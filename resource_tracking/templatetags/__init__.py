import os
import hashlib
import logging

from django.conf import settings

logger = logging.getLogger(__name__)

_resource_files = {}
_css_files = {}
_other_files = {}
_js_minify = not settings.DEBUG and settings.JS_MINIFY


def _get_resource_type(resource_file):
    return os.path.splitext(resource_file)[1].lower()


def _get_resource_dict(resource_type):
    if resource_type == ".css":
        return _css_files
    elif resource_type == ".js":
        return _resource_files
    else:
        return _other_files


def _process_resource_file(resource_file):
    resource_type = _get_resource_type(resource_file)
    resource_dict = _get_resource_dict(resource_type)
    resource_content = None
    if not os.path.exists(resource_file) or os.path.isdir(resource_file):
        # file does not exist or it is a folder
        return

    resource_file_name = os.path.basename(resource_file)
    resource_file_modify_time = os.path.getmtime(resource_file)
    # read the js file
    with open(resource_file) as f:
        resource_content = f.read()

    # minify the file if required
    hashed_file_name = None

    if resource_type == ".js" and _js_minify:
        # is a javascript file, minify is required
        from slimit import minify
        resource_content = minify(resource_content, mangle=True, mangle_toplevel=True)

    # get the hashed file
    hashed_file_name = hashlib.md5(resource_content).hexdigest() + (".min" if _js_minify else "") + resource_type
    hashed_file_path = os.path.join(os.path.dirname(resource_file), "version")
    if not os.path.exists(hashed_file_path):
        #folder not exist, create it
        os.mkdir(hashed_file_path)

    hashed_file = os.path.join(hashed_file_path, hashed_file_name)

    if os.path.exists(hashed_file):
        if os.path.isdir(hashed_file):
            raise "'{0}' is not a file.".fomat(hashed_file)
        else:
            # file is already exist and js file is not changed since previous generating.
            logger.info("Resource file '{0}' is not modified since last processing".format(resource_file_name))
            pass
    else:
        # file is modified since previous generating
        with open(hashed_file, 'w') as f:
            f.write(resource_content)

    resource_dict[resource_file_name] = ("version/" + hashed_file_name, resource_file, resource_file_modify_time)
    logger.info("Resource file '{0}' is processed and the exposed file is '{1}'. {2}".format(resource_file_name,hashed_file_name, os.getpid()))


def _initialize():
    if hasattr(settings, "RESOURCE_FILES_WITH_AUTO_VERSION") and settings.RESOURCE_FILES_WITH_AUTO_VERSION:
        for f in settings.RESOURCE_FILES_WITH_AUTO_VERSION:
            _process_resource_file(f)


def _get_resource_file(resource_file):
    resource_type = _get_resource_type(resource_file)
    resource_dict = _get_resource_dict(resource_type)
    try:
        return resource_dict[resource_file][0]
    except:
        # resource file does not support autoversion.
        return resource_file


def _get_resource_file_debug(resource_file):
    resource_type = _get_resource_type(resource_file)
    resource_dict = _get_resource_dict(resource_type)
    try:
        if resource_file in resource_dict:
            # resource file is already processed, check whether it is modifyed or not.
            resource_modify_time = os.path.getmtime(resource_dict[resource_file][1])
            if resource_modify_time != resource_dict[resource_file][2]:
                # it is changed, process it again
                _process_resource_file(resource_dict[resource_file][1])
        else:
            # resource file does not support autoversion.
            return resource_file

        return resource_dict[resource_file][0]
    except:
        # resource file does not support autoversion.
        return resource_file


_initialize()

get_resource_file = None
if settings.DEBUG:
    get_resource_file = _get_resource_file_debug
else:
    get_resource_file = _get_resource_file
