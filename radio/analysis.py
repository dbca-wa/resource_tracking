import logging
import os
import requests
import json
import subprocess
import threading
import shutil
import traceback
import tempfile
from PIL import Image


from django.contrib.gis.geos import Polygon,MultiPolygon
from django.contrib.gis import gdal
from django.conf import settings
from django.db.models import Q,F
from django.db.models.query import QuerySet
from django.utils import timezone

from .models import (Repeater,RepeaterTXAnalysis,RepeaterRXAnalysis,repeater_4326_file_path,repeater_mercator_file_path,repeater_shp_file_path,
        Network,NetworkTXAnalysis,NetworkRXAnalysis,network_4326_file_path,network_mercator_file_path,
        Option)
logger = logging.getLogger(__name__)

TX = 1
RX = 2

credential_options = ["uid","key"]

# options for area coverage
fixed_options = [
    ("file","shp"),
]
global_options = [
    "uid","key","dis","pm","pe","out","azi","bwi","ber","cli","cll","ked","mod","out","pol","ter","tlt","rel","engine","nl",
    "res",("clh",("res","90")),
    "ant",("fbr",("ant","0")),("vbw",("ant","0")),("hbw",("ant",0)),
    "col",("blu",("col","7")),("grn",("col","7")),("red",("col","7")),
    "txw","txg",
    "rxh","rxg","rxs",
    "rad"
]

network_options = [
]

repeater_name = lambda scope,repeater:"{}_{}".format(repeater.site_name.lower().replace(" ","_"),"tx" if scope == TX else "rx")
network_name = lambda scope,net:("{}_{}".format(net.name.lower().replace(" ","_"),"tx" if scope == TX else "rx")) if net else None

repeater_options = [
    ("nam",lambda options,scope,obj: repeater_name(scope,obj)),
    ("net",lambda options,scope,obj:network_name(scope,obj.network)),
    ("frq",lambda options,scope,obj: str(obj.tx_frequency.normalize()) if scope == TX else str(obj.rx_frequency.normalize())),
    ("txh",lambda options,scope,obj: obj.tx_antenna_height if scope == TX else obj.rx_antenna_height),
    ("lat",lambda options,scope,obj: obj.point.y),
    ("lon",lambda options,scope,obj:obj.point.x),
    #("rad",lambda options,scope,obj: _get_radius(options,scope,obj)),

]

# options for mesh site analysis
mesh_site_fixed_options  = [
]
mesh_site_global_options  = [
    "uid"
]
mesh_site_network_options  = [
    #("calcs",lambda options,scope,net:",".join([str((repeater.tx_analysis if scope == TX else repeater.rx_analysis).analyse_result["id"])  for repeater in Repeater.objects.filter(network=net)]))
    ("network",lambda options,scope,net:network_name(scope,net))
]

#options for deleting calculation
del_cal_fixed_options = [
    ("del",1)
]
del_cal_global_options = [
    "uid"
]

COMPRESS_FILE_SETTINGS = [
    (".7z",lambda f,output:["7za","-y","x",f,"-o{}".format(output)]),
    (".zip",lambda f,output:["unzip","-o","-q",f,"-d",output]),
    (".tar",lambda f,output:["tar","--overwrite","-x","-f",f,"-C",output]),
    (".tar.gz",lambda f,output:["tar","--overwrite","-x","-z","-f",f,"-C",output]),
    (".tgz",lambda f,output:["tar","--overwrite","-x","-z","-f",f,"-C",output]),
    (".tar.xz",lambda f,output:["tar","--overwrite","-x","-J","-f",f,"-C",output]),
    (".tar.bz2",lambda f,output:["tar","--overwrite","-x","-j","-f",f,"-C",output]),
    (".tar.bz",lambda f,output:["tar","--overwrite","-x","-j","-f",f,"-C",output])
]
#mapping between Repeater analysis column and json field and other related settings 
repeater_file_column_mapping = {
    "raster_4326":('PNG_WGS84',repeater_4326_file_path,"world_file_4326"),
    "raster_mercator":('PNG_Mercator',repeater_mercator_file_path,"world_file_mercator"),
    "shp_file":('shp',repeater_shp_file_path,"geom"),
}

#mapping between network analysis column and json field and other related settings
network_file_column_mapping = {
    "raster_4326":('png_wgs84',network_4326_file_path,"world_file_4326"),
    "raster_mercator":('png_mercator',network_mercator_file_path,"world_file_mercator"),
}

def get_img_size(img_file):
    """
    Return a tuple(width,height)
    """
    img = Image.open(img_file)
    return (img.width,img.height)

#mapping between rast file extension and world file extension
world_file_ext_mapping = {
    ".gif":".gfw",
    ".jpg":".jgw",
    ".jp2":".j2w",
    ".png":".pgw",
    ".tif":".tfw"
}
def transform_bbox(bbox,projection="epsg:4326"):
    """
    Transform bbox from epsg_4326 to dest projection
    """
    if projection == "epsg:4326":
        return bbox

    src_proj = gdal.SpatialReference("epsg:4326")
    dest_proj = gdal.SpatialReference(projection)
    p1 = gdal.geometries.OGRGeometry("POINT({} {})".format(bbox[0],bbox[1]))
    p2 = gdal.geometries.OGRGeometry("POINT({} {})".format(bbox[2],bbox[3]))
    ct = gdal.CoordTransform(src_proj,dest_proj)
    p1.transform(ct)
    p2.transform(ct)
    return [p1.x,p1.y,p2.x,p2.y]

def generate_world_file(img_file,img_bbox):
    """
    Generate a world file for raster file, and return the file path
    """
    path,img_file_name = os.path.split(img_file)
    img_file_basename,img_file_ext = os.path.splitext(img_file_name)
    world_file_ext = world_file_ext_mapping.get(img_file_ext)
    if not world_file_ext:
        raise Exception("Image file({}) Not Support,only support .gif,.jpg,.jp2,.png,.tif".format(img_file))

    world_file = os.path.join(path,"{}{}".format(img_file_basename,world_file_ext))

    img_size = get_img_size(img_file)
    with open(world_file,'w') as f:
        f.write(str(round((img_bbox[2] - img_bbox[0]) / (img_size[0] * 1.0),6)))
        f.write(os.linesep)

        f.write("0")
        f.write(os.linesep)

        f.write("0")
        f.write(os.linesep)

        f.write(str(round((img_bbox[3] - img_bbox[1]) / (img_size[1] * 1.0),6)))
        f.write(os.linesep)

        f.write(str(img_bbox[0]))
        f.write(os.linesep)

        f.write(str(img_bbox[1]))

    return world_file

def normalize_bbox(bbox):
    """
    return a tupe(upper left x|lon,upper left y|lat,bottom right x|lat, bottom right y|lon) )From a bounds 
    bbox is a free style lat/lon bounding box.
    WGS84 bounds: 112.85 -43.7    153.69 -9.86
    """
    lons = [d for d in bbox if d > 100 and d < 160]
    lats = [d for d in bbox if d > -46 and d < -7]
    if len(lons) != 2 or len(lats) != 2:
        raise Exception("The bounding box({}) is not belonging to australia".format(bbox))

    lats.sort(reverse=True)
    lons.sort()

    return [lons[0],lats[0],lons[1],lats[1]]

def get_verify_ssl():
    try:
        return Option.objects.get(name = "verify_ssl").tvalue
    except:
        return True

def _get_radius(options,scope,obj):
    if options["dis"] == 'm':
        return obj.output_radius * 1000
    else:
        raise Exception("Distance unit({}) Not Support".format(options["dis"]))

def _set_global_option(scope,options,option,remove=False,force=False):
    """
    Set global option
    Option are retrieved from model 'Option'
    """
    _set_option(scope,options,option,lambda option:Option.objects.get(name=option).tvalue,remove=remove,force=force)

def _set_object_option(scope,options,option,obj,remove=False,force=False):
    """
    Set option from the properties for object such as repeater, network
    """
    _set_option(scope,options,option,lambda option:getattr(obj,option),remove=remove,obj=obj,force=force)

def _set_option(scope,options,option,get_option,remove=False,obj=None,force=False):
    """
    Set option for web service.
    scope: TX or RX
    options: the options dict object
    option: option name
    get_option: the function to retrieve the option's value
    remove: remove the option from options
    force: always fetch the option's value even if it already exists in options if force is True
    """
    if isinstance(option,str):
        #option key
        if remove:
            if option in options:
                del options[option]
        else:
            if force or option not in options:
                try:
                    value = get_option(option)
                except :
                    value = None
                if value is not None:
                    options[option] = value
                elif option in options:
                    del options[option]
            else:
                #already set.
                pass
    elif isinstance(option,(list,tuple)):
        if isinstance(option[1],(list,tuple)):
            #this option is dependent on another option
            if options.get(option[1][0]) == option[1][1]:
                #filter condition is met,include this option
                _set_option(scope,options,option[0],get_option,obj=obj,force=force)
            else:
                #filter condition is not met,should not include this option
                _set_option(scope,options,option[0],get_option,remove=True,obj=obj,force=force)
        elif callable(option[1]):
            #this option is a computable option
            if remove:
                if option[0] in options:
                    del options[option[0]]
            else:
                if force or option[0] not in options:
                    if obj is None:
                        value = option[1](options,scope)
                    else:
                        value = option[1](options,scope,obj)

                    if value is not None:
                        options[option[0]] = value
                    elif option[0] in options:
                        del options[option[0]]
        else:
            raise Exception("Option config({}) Not Support".format(option))
    else:
        raise Exception("Option config({}) Not Support".format(option))

def _download_file(analysis,file_column_mapping,force=False,verify_ssl=True):
    """
    Download files for repeater or network
    """
    #download all files
    if not force and analysis.last_downloaded and analysis.last_downloaded > analysis.last_analysed:
        return

    update_fields = []
    for column,column_settings in file_column_mapping.items():
        key,get_file_path,rel_column = column_settings
        url = analysis.analyse_result.get(key)
        if not url:
            raise Exception("Key({}) missing in analyse result({})".format(key,analysis.analyse_result))
        if column == "shp_file":
            file_name = "download.shp"
        else:
            file_name = os.path.split(url)[1]
        rel_file_path = get_file_path(analysis,file_name)
        file_path = os.path.join(settings.MEDIA_ROOT,rel_file_path)
        #create folder if does not exist
        file_folder,file_name = os.path.split(file_path)
        if not os.path.exists(file_folder):
            os.makedirs(os.path.split(file_path)[0])
        
        #download files
        cmd = "wget{}  \"{}\" -O {}".format("" if verify_ssl else " --no-check-certificate",url,file_path)
        logger.debug("download file. cmd='{}'".format(cmd))
        subprocess.check_call(cmd,shell=True)

        setattr(analysis,column,rel_file_path)
        update_fields.append(column)
        
        if rel_column:
            setattr(analysis,rel_column,None)
            update_fields.append(rel_column)


    bounds = analysis.analyse_result.get("bounds")
    if not bounds:
        raise Exception("Key({}) missing in analyse result({})".format("bounds",analysis.analyse_result))

    analysis.bbox = None
    update_fields.append("bbox")
    analysis.last_downloaded = timezone.now()
    update_fields.append("last_downloaded")
    
    analysis.save(update_fields=update_fields)

def _download_repeater_file(analysis,force=False,verify_ssl=True):
    """
    Download files for repeater
    """
    _download_file(analysis,repeater_file_column_mapping,force=force,verify_ssl=verify_ssl)

def _download_network_file(analysis,force=False,verify_ssl=True):
    """
    Download files for network
    """
    _download_file(analysis,network_file_column_mapping,force=force,verify_ssl=verify_ssl)

def _process_spatial_data(analysis,force=False):
    """
    Generate the world file for raster 
    Extract the spatial data from shape file for vector data
    """
    #extract the spatial data from shape file 
    if not force and  analysis.bbox:
        return

    update_fields = []
    #populate the bbox
    bounds = analysis.analyse_result.get("bounds")
    if not bounds:
        raise Exception("Key({}) missing in analyse result({})".format("bounds",analysis.analyse_result))

    analysis.bbox = normalize_bbox(bounds)
    update_fields.append("bbox")
    
    #generate world file
    for f,projection,column in ((analysis.raster_4326.name,"epsg:4326","world_file_4326"),(analysis.raster_mercator.name,"epsg:3857","world_file_mercator")):
        world_file = generate_world_file(os.path.join(settings.MEDIA_ROOT,f),transform_bbox(analysis.bbox,projection))
        setattr(analysis,column,world_file[len(settings.MEDIA_ROOT) + 1:])
        update_fields.append(column)
    
    if hasattr(analysis,"shp_file"):
        #decompress file
        file_name = analysis.shp_file.name.lower()
        file_path = os.path.join(settings.MEDIA_ROOT,analysis.shp_file.name)
        shp_file_folder = None
        try:
            shp_file_folder = tempfile.mkdtemp(prefix="radio",suffix=".shp")

            for fileext,cmd in COMPRESS_FILE_SETTINGS:
                if file_name.endswith(fileext):
                    subprocess.check_call(cmd(file_path,shp_file_folder))
                    break
            shp_file_path = None
            for f in os.listdir(shp_file_folder):
                if f.endswith(".shp"):
                    shp_file_path = os.path.join(shp_file_folder,f)
                    break
            if not shp_file_path:
                raise Exception("Can't find shape file in folder ''".format(shp_file_folder))
    
            ds = gdal.DataSource(shp_file_path)
            layer = ds[0]
            polygons = []
            for feat in layer:
                if isinstance(feat.geom,gdal.geometries.Polygon):
                    polygons.append(feat.geom.geos)
                elif isinstance(feat.geom,gdal.geometries.MultiPolygon):
                    for g in feat.geom.geos.geom:
                        polygons.append(g)
                else:
                    raise Exception("Geometry({}) Not Support, only support Polygon and MultiPolygon".format(feat.geom.__class__))
            analysis.geom = MultiPolygon(polygons)
            update_fields.append("geom")
        finally:
            if shp_file_folder:
                #remove the temporary folder
                try:
                    shutil.rmtree(shp_file_folder)
                except :
                    logger.error(traceback.format_exc())



    analysis.save(update_fields = update_fields)

def _del_calculation(cid,options={},endpoint=None,verify_ssl=True):
    """
    Delete a calculation
    """
    if verify_ssl is None:
        verify_ssl = get_verify_ssl()

    #set the fixed options
    for k,v in del_cal_fixed_options:
        options[k] = v

    #set the global options
    for option in del_cal_global_options:
        _set_global_option(None,options,option,force=False)

    #set the analysis options
    options["cid"] = cid

    if not endpoint:
        endpoint = Option.objects.get(name="del_calculation_endpoint").value
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("Delete calculation,options = {}".format(["{}={}".format(k,'******' if k in credential_options else v) for k,v in options.items()]))
    url = "{}?{}".format(endpoint,"&".join(["{}={}".format(k,v) for k,v in options.items()]))
    res = requests.get(url,verify=verify_ssl)
    res.raise_for_status()
    if "error" in res:
        raise Exception(res["error"])

def _del_analysis_calculation(analysis,options={},endpoint=None,verify_ssl=True):
    """
    Delete a analysis related calculation
    """
    if not analysis or not analysis.analyse_result or not analysis.analyse_result.get("id") or analysis.analyse_result.get("deleted"):
        return
    try:
        _del_calculation(analysis.analyse_result["id"],options=options,endpoint=endpoint,verify_ssl=verify_ssl)
        analysis.analyse_result["deleted"] = True
        if "delete_msg" in analysis.analyse_result:
            del analysis.analyse_result["delete_msg"]
    except :
        logger.error("delete calculation({}) failed,options={}.{}".format(analysis.analyse_result["id"],["{}={}".format(k,'******' if k in credential_options else v) for k,v in options.items()],traceback.format_exc()))
        analysis.analyse_result["delete_msg"] = traceback.format_exc()

    analysis.save(update_fields = ["analyse_result"])

def del_outdated_repeater_calculation(network):
    """
    Delete a outdated repeater analysis based on network
    """
    if not network:
        return

    verify_ssl = get_verify_ssl()

    endpoint = Option.objects.get(name="del_calculation_endpoint").value
    options = {}

    for scope,analysis in [(TX,network.tx_analysis),(RX,network.rx_analysis)]:
        if not analysis or not analysis.analyse_result:
            continue
        calculations = analysis.analyse_result.get("calculations")
        if not calculations:
            continue
        for rep_analysis in (RepeaterTXAnalysis if scope == TX else RepeaterTXAnalysis).objects.filter(repeater__network=network):
            if not rep_analysis.analyse_result:
                continue
            try:
                index = calculations.index(rep_analysis.analyse_result["id"])
                del calculations[index]
            except:
                continue

        if not calculations:
            # no calculations are outdated
            continue

        for cid in calculations:
            _del_calculation(cid,options=options,endpoint=endpoint,verify_ssl=verify_ssl)

class _Thread(threading.Thread):
    """
    Capture the excetpion thrown in run method, and rethrow in join method
    """
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self._ex = None

    def run(self):
        try:
            self._run()
        except Exception as ex:
            self._ex = ex
        except:
            self._ex = Exception(traceback.format_exc())

    def _run(self):
        pass

    def join(self,*args,**kwargs):
        super().join(*args,**kwargs)
        if self._ex:
            raise self._ex

class RepeaterAnalysisThread(_Thread):
    def __init__(self,options,del_options,scope,rep,analysis,endpoint,del_endpoint,verify_ssl):
        super().__init__()
        self.options = options
        self.del_options = del_options
        self.scope = scope
        self.rep = rep
        self.analysis = analysis
        self.endpoint = endpoint
        self.del_endpoint = del_endpoint
        self.verify_ssl = verify_ssl

    def _run(self):
        #delete the previous calculation
        _del_analysis_calculation(self.analysis,self.del_options,endpoint=self.del_endpoint,verify_ssl=self.verify_ssl)

        #set the repeater option
        for option in repeater_options:
            _set_object_option(self.scope,self.options,option,self.rep,force=True)

        #print the option
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("The area coverage analysis options({}) for repeater({})".format(["{}={}".format(k,'******' if k in credential_options else v) for k,v in self.options.items()],self.rep))

        #analysis the area coverage
        res = requests.post(self.endpoint, data=self.options,verify=self.verify_ssl)
        res.raise_for_status()
        try:
            res = res.json()
        except:
            raise Exception(res.text)
        if "error" in res:
            raise Exception(res["error"])
        logger.debug("The area coverage analysis result({}) for repeater({})".format(res,self.rep))
        self.analysis.network = self.rep.network.name if self.rep.network else None
        self.analysis.analyse_result = res
        self.analysis.last_analysed = timezone.now()
        self.analysis.save(update_fields=["analyse_result","last_analysed","network"])

class RepeaterPostAnalysisThread(_Thread):
    def __init__(self,analysis,force,verify_ssl):
        super().__init__()
        self.analysis = analysis
        self.force = force
        self.verify_ssl = verify_ssl
        self._ex = None

    def _run(self):
        _download_repeater_file(self.analysis,force=self.force,verify_ssl=self.verify_ssl)
        try:
            _process_spatial_data(self.analysis,force=self.force)
        except:
            self.analysis.analyse_requested = timezone.now()
            self.analysis.save(update_fields=["analyse_requested"])
            raise

class NetworkAnalysisThread(_Thread):
    def __init__(self,options,del_options,scope,network,analysis,endpoint,del_endpoint,verify_ssl):
        super().__init__()
        self.options = options
        self.del_options = del_options
        self.scope = scope
        self.network = network
        self.analysis = analysis
        self.endpoint = endpoint
        self.del_endpoint = del_endpoint
        self.verify_ssl = verify_ssl

    def _run(self):
        #delete the previous network calculation
        _del_analysis_calculation(self.analysis,self.del_options,endpoint=self.del_endpoint,verify_ssl=self.verify_ssl)

        #set the network option
        for option in mesh_site_network_options:
            _set_object_option(self.scope,self.options,option,self.network,force=True)

        #print the option
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("The mesh site analysis options({}) for network({})".format(["{}={}".format(k,'******' if k in credential_options else v) for k,v in self.options.items()],self.network))
        #analysis the area coverage
        url = "{}?{}".format(self.endpoint,"&".join(["{}={}".format(k,v) for k,v in self.options.items()]))
        res = requests.get(url,verify=self.verify_ssl)
        res.raise_for_status()
        try:
            res = res.json()
        except:
            raise Exception(res.text)
        if "error" in res:
            raise Exception(res["error"])
        logger.debug("The mesh site analysis result({}) for network({})".format(res,self.network))
        self.analysis.analyse_result = res
        self.analysis.last_analysed = timezone.now()
        self.analysis.save(update_fields=["analyse_result","last_analysed"])


class NetworkPostAnalysisThread(_Thread):
    def __init__(self,analysis,force,verify_ssl):
        super().__init__()
        self.analysis = analysis
        self.force = force
        self.verify_ssl = verify_ssl

    def _run(self):
        _download_network_file(self.analysis,force=self.force,verify_ssl=self.verify_ssl)
        try:
            _process_spatial_data(self.analysis,force=self.force)
        except:
            self.analysis.analyse_requested = timezone.now()
            self.analysis.save(update_fields=["analyse_requested"])
            raise


def area_coverage(queryset=None,network=None,repeater=None,force=False,scope=TX | RX,options={},del_options={},verify_ssl=None):
    """
    Perform the area coverage for selected repeaters
    use multi thread to improve the performance(not allowed in current account)
    """
    if verify_ssl is None:
        verify_ssl = get_verify_ssl()

    if scope & (TX|RX) == 0:
        #Both tx and rx are not required to calculate the are coverage.
        return

    del_endpoint = Option.objects.get(name="del_calculation_endpoint").value

    if queryset:
        if isinstance(qs,QuerySet):
            base_qs = queryset.order_by("network")
        else:
            base_qs = Repeater.objects.filter(id__in = [r.id for r in queryset]).order_by("network")
    else:
        if repeater:
            base_qs = Repeater.objects.filter(id = repeater.id)
        elif network:
            base_qs = Repeater.objects.filter(network = network).order_by("network")
        else:
            base_qs = Repeater.objects.all().order_by("network")

    #analyse the repeater
    endpoint = Option.objects.get(name="area_coverage_endpoint").value

    if scope & TX == TX:
        if not force:
            tx_qs = base_qs.filter(Q(tx_analysis__last_analysed__isnull=True)|Q(tx_analysis__last_analysed__lt=F("tx_analysis__analyse_requested")))
        else:
            tx_qs = base_qs.all()
    else:
        tx_qs = None


    if scope & RX == RX:
        if not force:
            rx_qs = base_qs.filter(Q(rx_analysis__last_analysed__isnull=True)|Q(rx_analysis__last_analysed__lt=F("rx_analysis__analyse_requested")))
        else:
            rx_qs = base_qs.all()
    else:
        rx_qs = None

    #set the fixed options
    for k,v in fixed_options:
        options[k] = v

    threads = []
    previous_network = None
    for s,qs,get_analysis in [o for o in [
        (TX,tx_qs,lambda r:RepeaterTXAnalysis.objects.get_or_create(repeater=r,defaults={"analyse_requested":timezone.now()})[0]),
        (RX,rx_qs,lambda r:RepeaterRXAnalysis.objects.get_or_create(repeater=r,defaults={"analyse_requested":timezone.now()})[0])] if o[1]]:
        #get the global option first.
        for option in global_options:
            if isinstance(option,str) or isinstance(option[0],str):
                #same for all scope
                reset_option = False
            else:
                reset_option = True
            _set_global_option(s,options,option,force=reset_option)

        for rep in qs:
            #set the network option
            if network_options and not rep.network:
                raise Exception("Can't perform area coverage analysis, the repeater({}) is not belonging to any network.".format(rep))

            for option in network_options:
                _set_object_option(s,options,option,rep.network,force=(previous_network ==  rep.network))

            analysis = get_analysis(rep)
            #thread = RepeaterAnalysisThread(dict(options),dict(del_options),s,rep,analysis,endpoint,del_endpoint,verify_ssl)
            thread = RepeaterAnalysisThread(options,del_options,s,rep,analysis,endpoint,del_endpoint,verify_ssl)
            #threads.append(thread)
            thread.start()
            #current account plan doesn't support call webservice multipe times at the same time.
            thread.join()

            previous_network = rep.network

    for t in threads:
        t.join()

    #post analyse
    #extract geom
    if scope & TX == TX:
        tx_qs = base_qs.all()
    else:
        tx_qs = None


    if scope & RX == RX:
        rx_qs = base_qs.all()
    else:
        rx_qs = None

    threads.clear()
    for s,qs,get_analysis in [o for o in [(TX,tx_qs,lambda r:r.tx_analysis),(RX,rx_qs,lambda r:r.rx_analysis)] if o[1]]:
        for repeater in qs:
            analysis = get_analysis(repeater)
            thread = RepeaterPostAnalysisThread(analysis,force,verify_ssl)
            threads.append(thread)
            thread.start()

    for t in threads:
        t.join()

def mesh_site(queryset=None,network=None,force=False,scope=TX | RX,options={},del_options={},verify_ssl=None):
    """
    Perform mesh site analysis for selected repeaters
    use multi thread to improve the performance(not allowed in current account)
    """
    if verify_ssl is None:
        verify_ssl = get_verify_ssl()

    if scope & (TX|RX) == 0:
        #Both tx and rx are not required to calculate the are coverage.
        return
    if queryset:
        if isinstance(qs,QuerySet):
            base_qs = queryset
        else:
            base_qs = Network.objects.filter(id__in = [r.id for r in queryset])
    else:
        if network:
            base_qs = Network.objects.filter(id = network.id)
        else:
            base_qs = Network.objects.all()

    #analyse the network
    endpoint = Option.objects.get(name="mesh_site_endpoint").value
    del_endpoint = Option.objects.get(name="del_calculation_endpoint").value

    if scope & TX == TX:
        if not force:
            tx_qs = base_qs.filter(Q(tx_analysis__last_analysed__isnull=True)|Q(tx_analysis__last_analysed__lt=F("tx_analysis__analyse_requested")))
        else:
            tx_qs = base_qs.all()
    else:
        tx_qs = None


    if scope & RX == RX:
        if not force:
            rx_qs = base_qs.filter(Q(rx_analysis__last_analysed__isnull=True)|Q(rx_analysis__last_analysed__lt=F("rx_analysis__analyse_requested")))
        else:
            rx_qs = base_qs.all()
    else:
        rx_qs = None

    #set the fixed options
    for k,v in mesh_site_fixed_options:
        options[k] = v

    threads = []
    for s,qs,get_analysis in [o for o in [
        (TX,tx_qs,lambda net:NetworkTXAnalysis.objects.get_or_create(network=net,defaults={"analyse_requested":timezone.now()})[0]),
        (RX,rx_qs,lambda net:NetworkRXAnalysis.objects.get_or_create(network=net,defaults={"analyse_requested":timezone.now()})[0])] if o[1]]:
        #get the global option first.
        for option in mesh_site_global_options:
            if isinstance(option,str) or isinstance(option[0],str):
                #same for all scope
                reset_option = False
            else:
                reset_option = True

            _set_global_option(s,options,option,force=reset_option)

        for net in qs:
            analysis = get_analysis(net)

            #thread = NetworkAnalysisThread(dict(options),dict(del_options),s,net,analysis,endpoint,del_endpoint,verify_ssl)
            thread = NetworkAnalysisThread(options,del_options,s,net,analysis,endpoint,del_endpoint,verify_ssl)
            #threads.append(thread)
            thread.start()
            #current account plan doesn't support call webservice multipe times at the same time.
            thread.join()

    for t in threads:
        t.join()

    #post analyse
    if scope & TX == TX:
        tx_qs = base_qs.all()
    else:
        tx_qs = None


    if scope & RX == RX:
        rx_qs = base_qs.all()
    else:
        rx_qs = None

    threads.clear()
    for s,qs,get_analysis in [o for o in [(TX,tx_qs,lambda r:r.tx_analysis),(RX,rx_qs,lambda r:r.rx_analysis)] if o[1]]:
        for net in qs:
            analysis = get_analysis(net)
            thread = NetworkPostAnalysisThread(analysis,force,verify_ssl)
            threads.append(thread)
            thread.start()

    for t in threads:
        t.join()


def analyse_network_coverage(queryset=None,network=None,force=False,scope=TX | RX,options={},verify_ssl=None):
    if verify_ssl is None:
        verify_ssl = get_verify_ssl()
    if options is None:
        options = {}
    if "area_coverage" not in options:
        options["area_coverage"] = {}
    if "mesh_site" not in options:
        options["mesh_site"] = {}
    if "del_calculation" not in options:
        options["del_calculation"] = {}

    del_endpoint = Option.objects.get(name="del_calculation_endpoint").value

    for net in ([network ]if network else queryset):
        #delete the calculation of the repeaters which are removed from the network
        for rep_analysis_qs in [m.objects.filter(network=net.name).exclude(repeater__network=net) for s,m in [(scope & TX,RepeaterTXAnalysis),(scope & RX,RepeaterRXAnalysis)] if s ]:
            for rep_analysis in rep_analysis_qs:
                _del_analysis_calculation(rep_analysis,options["del_calculation"],endpoint=del_endpoint,verify_ssl=verify_ssl)
                rep_analysis.network=None
                rep_analysis.save(update_fields=["network"])

        area_coverage(network=net,force=force,scope=scope,options=options["area_coverage"],del_options=options["del_calculation"],verify_ssl=verify_ssl)
        mesh_site(network=net,force=force,scope=scope,options=options["mesh_site"],del_options=options["del_calculation"],verify_ssl=verify_ssl)


        

        
