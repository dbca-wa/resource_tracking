import logging
import os
import requests
import json
import subprocess
import threading
import shutil
import traceback
import tempfile
import queue
from PIL import Image

from django.contrib.gis.geos import Polygon,MultiPolygon
from django.contrib.gis import gdal
from django.conf import settings
from django.db.models import Q,F
from django.db.models.query import QuerySet
from django.utils import timezone

from .models import (Repeater,RepeaterTXAnalysis,RepeaterRXAnalysis,repeater_4326_file_path,repeater_mercator_file_path,repeater_shp_file_path,
        Network,NetworkTXAnalysis,NetworkRXAnalysis,network_4326_file_path,network_mercator_file_path,
        RepeaterTXCoverage,RepeaterRXCoverage,
        Option)
logger = logging.getLogger(__name__)

TX = 1
RX = 2

_tasks = queue.Queue()

credential_options = ["uid","key"]

# options for area coverage
fixed_options = [
    ("file","shp"),
]
global_options = [
    "uid","key","dis","pm","pe","out","azi","bwi","ber","cli","cll","ked","mod","out","pol","ter","tlt","rel","engine","clm","nf",
    "res",("clh",("res","90")),
    "ant",("fbr",("ant","0")),("vbw",("ant","0")),("hbw",("ant",0)),
    "col",("blu",("col","7")),("grn",("col","7")),("red",("col","7")),
    ("txw",lambda options,scope:Option.get_option("txw_{}".format("tx" if scope == TX else "rx"))),("txg",lambda options,scope:Option.get_option("txg_{}".format("tx" if scope == TX else "rx"))),
    "rxh","rxg","rxs",
    "rad",
    "fmt","txl","min","max","gry","opy"
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
    #("lat",lambda options,scope,obj:-29.268431),
    #("lon",lambda options,scope,obj:124.555023),
    ("txw",lambda options,scope,obj: obj.tx_power if obj.tx_power  else options.get('txw')),
    ("txg",lambda options,scope,obj: obj.tx_antenna_gain if obj.tx_antenna_gain  else options.get('txg')),
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
    "raster_4326":(lambda result:result["shp"].replace('fmt=shp','fmt=tiff'),repeater_4326_file_path,"world_file_4326"),
    "raster_mercator":('PNG_Mercator',repeater_mercator_file_path,"world_file_mercator"),
    "shp_file":('shp',repeater_shp_file_path,None),
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

class AnalyseWorker(threading.Thread):
    instance = None
    def __init__(self):
        super().__init__()

    def run(self):
        try:
            while True:
                try:
                    task = _tasks.get(timeout=10)
                    task.run()
                except queue.Empty:
                    break
        finally:
            AnalyseWorker.instance = None

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

def _download_file(analysis,file_column_mapping,verify_ssl=None):
    """
    Download files for repeater or network
    """
    #download all files
    if abs(analysis.process_status) >= analysis.DOWNLOADED:
        return

    if analysis.process_status < 0 and abs(analysis.process_status) < analysis.DOWNLOADING:
        #previous processing is failed
        return

    if verify_ssl is None:
        verify_ssl = get_verify_ssl()

    try:
        start_processing(analysis,analysis.DOWNLOADING)

        update_fields = []
        for column,column_settings in file_column_mapping.items():
            if analysis.analyse_result.get("{}_downloaded".format(column)):
                #already downloaded
                continue
            key,get_file_path,rel_column = column_settings
            if callable(key):
                url = key(analysis.analyse_result)
            else:
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
            analysis.analyse_result["{}_downloaded".format(column)]=str(timezone.now())
            update_fields.append("analyse_result")
            
            if rel_column:
                setattr(analysis,rel_column,None)
                update_fields.append(rel_column)
    
            analysis.save(update_fields=update_fields)
            update_fields.clear()
    
    
        bounds = analysis.analyse_result.get("bounds")
        if not bounds:
            raise Exception("Key({}) missing in analyse result({})".format("bounds",analysis.analyse_result))
    
        analysis.bbox = None
        update_fields.append("bbox")
        
        end_processing(analysis,analysis.DOWNLOADED,update_fields=update_fields)
    except:
        end_processing(analysis,analysis.DOWNLOAD_FAILED,msg=traceback.format_exc())

def _download_repeater_file(analysis,verify_ssl=None):
    """
    Download files for repeater
    """
    _download_file(analysis,repeater_file_column_mapping,verify_ssl=verify_ssl)

def _download_network_file(analysis,verify_ssl=None):
    """
    Download files for network
    """
    _download_file(analysis,network_file_column_mapping,verify_ssl=verify_ssl)

def _process_spatial_data(analysis,coverage_model):
    """
    Generate the world file for raster 
    Extract the spatial data from shape file for vector data
    """
    #extract the spatial data from shape file 
    if abs(analysis.process_status) >= analysis.EXTRACTED:
        #already processed
        return

    if analysis.process_status < 0 and abs(analysis.process_status) < analysis.EXTRACTING:
        #previous processing is failed
        return

    try:
        start_processing(analysis,analysis.EXTRACTING)

        update_fields = []
        #populate the bbox
        bounds = analysis.analyse_result.get("bounds")
        if not bounds:
            raise Exception("Key({}) missing in analyse result({})".format("bounds",analysis.analyse_result))
    
        analysis.bbox = normalize_bbox(bounds)
        update_fields.append("bbox")
        
        #generate world file
        #for f,projection,column in ((analysis.raster_4326.name,"epsg:4326","world_file_4326"),(analysis.raster_mercator.name,"epsg:3857","world_file_mercator")):
        for f,projection,column in ((analysis.raster_mercator.name,"epsg:3857","world_file_mercator"),):
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
                rep = analysis.repeater
                coverage_model.objects.filter(repeater=rep).delete()
                for feat in layer:
                    if isinstance(feat.geom,gdal.geometries.Polygon):
                        coverage_model(repeater=rep,site_name=rep.site_name,district=rep.district.name,dn=feat.get('DN'),geom=MultiPolygon([feat.geom.geos])).save()
                    elif isinstance(feat.geom,gdal.geometries.MultiPolygon):
                        coverage_model(repeater=rep,site_name=rep.site_name,district=rep.district.name,dn=feat.get('DN'),geom=feat.geom.geos).save()
                    else:
                        raise Exception("Geometry({}) Not Support, only support Polygon and MultiPolygon".format(feat.geom.__class__))
            finally:
                if shp_file_folder:
                    #remove the temporary folder
                    try:
                        shutil.rmtree(shp_file_folder)
                    except :
                        logger.error(traceback.format_exc())
    
        analysis.last_analysed = timezone.now()
        update_fields.append("last_analysed")
        end_processing(analysis,analysis.IDLE,update_fields=update_fields)
    except:
        end_processing(analysis,analysis.EXTRACTE_FAILED,msg=traceback.format_exc())

def _del_calculation(cid,options={},endpoint=None,verify_ssl=None):
    """
    Delete a calculation
    """
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

    if verify_ssl is None:
        verify_ssl = get_verify_ssl()

    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("Delete calculation,options = {}".format(["{}={}".format(k,'******' if k in credential_options else v) for k,v in options.items()]))
    url = "{}?{}".format(endpoint,"&".join(["{}={}".format(k,v) for k,v in options.items()]))
    res = requests.get(url,verify=verify_ssl)
    res.raise_for_status()
    if "error" in res:
        raise Exception(res["error"])

def start_processing(analysis,status):
    analysis.process_status = status
    analysis.process_msg = None
    analysis.process_start = timezone.now()
    analysis.process_end = None
    analysis.save(update_fields=["process_status","process_msg","process_start","process_end"])

def end_processing(analysis,status,msg=None,update_fields=None):
    analysis.process_status = status
    analysis.process_msg = msg
    analysis.process_end = timezone.now()
    if update_fields:
        update_fields.append("process_status")
        update_fields.append("process_msg")
        update_fields.append("process_end")
        analysis.save(update_fields=update_fields)
    else:
        analysis.save(update_fields=["process_status","process_msg","process_end"])

def _del_analysis_calculation(analysis,options={},endpoint=None,verify_ssl=None,target_status=RepeaterTXAnalysis.DELETED):
    """
    Delete a analysis related calculation
    return True if delete succeed otherwise return False
    """
    if abs(analysis.process_status) >= analysis.DELETED:
        #already processed
        return

    if analysis.process_status < 0 and abs(analysis.process_status) < analysis.DELETING:
        #previous processing is failed
        return

    update_fields = []
    try:
        start_processing(analysis,analysis.DELETING)
        if not analysis or not analysis.analyse_result or not analysis.analyse_result.get("id") :
            #data incorrect
            raise Exception("Can't find calculation id in analyse result")
        if not analysis.analyse_result.get("deleted"):
            _del_calculation(analysis.analyse_result["id"],options=options,endpoint=endpoint,verify_ssl=verify_ssl)
            if hasattr(analysis,"network"):
                #analysis has network field, reset it
                analysis.network=None
                update_fields.append("network")
            analysis.analyse_result["deleted"] = True
            update_fields.append("analyse_result")
        end_processing(analysis,target_status,update_fields=update_fields)
    except :
        logger.error("delete calculation({}) failed,options={}.{}".format(analysis.analyse_result["id"],["{}={}".format(k,'******' if k in credential_options else v) for k,v in options.items()],traceback.format_exc()))
        end_processing(analysis,analysis.DELETE_FAILED,msg=traceback.format_exc(),update_fields=update_fields)

    return False if analysis.process_status == analysis.FAILED else True

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

def _wait_threads(threads):
    for t in threads:
        t.join()

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
        if abs(self.analysis.process_status) >= self.analysis.ANALYSED:
            return

        if self.analysis.process_status < 0 and abs(self.analysis.process_status) < self.analysis.ANALYSING:
            #previous processing is failed
            return

        #delete the previous calculation
        _del_analysis_calculation(self.analysis,self.del_options,endpoint=self.del_endpoint,verify_ssl=self.verify_ssl)
        try:
            start_processing(self.analysis,self.analysis.ANALYSING)
    
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
            end_processing(self.analysis,self.analysis.ANALYSED,update_fields=["analyse_result","network"])
        except :
            end_processing(self.analysis,self.analysis.ANALYSE_FAILED,msg=traceback.format_exc())

class RepeaterPostAnalysisThread(_Thread):
    def __init__(self,analysis,coverage_model,verify_ssl):
        super().__init__()
        self.analysis = analysis
        self.coverage_model = coverage_model
        self.verify_ssl = verify_ssl
        self._ex = None

    def _run(self):
        _download_repeater_file(self.analysis,verify_ssl=self.verify_ssl)

        _process_spatial_data(self.analysis,self.coverage_model)

class NetworkAnalysisThread(_Thread):
    def __init__(self,options,del_options,scope,network,analysis,repeater_analysis_model,endpoint,del_endpoint,verify_ssl):
        super().__init__()
        self.options = options
        self.del_options = del_options
        self.scope = scope
        self.network = network
        self.analysis = analysis
        self.endpoint = endpoint
        self.del_endpoint = del_endpoint
        self.verify_ssl = verify_ssl
        self.repeater_analysis_model = repeater_analysis_model

    def _run(self):
        if abs(self.analysis.process_status) >= self.analysis.ANALYSED:
            return

        if self.analysis.process_status < 0 and abs(self.analysis.process_status) < self.analysis.ANALYSING:
            #previous processing is failed
            return

        #delete the previous network calculation
        _del_analysis_calculation(self.analysis,self.del_options,endpoint=self.del_endpoint,verify_ssl=self.verify_ssl)
    
        try:
            start_processing(self.analysis,self.analysis.ANALYSING)

            times = 0
            while self.repeater_analysis_model.objects.filter(repeater__network = self.network).exclude(process_status__gt=self.repeater_analysis_model.IDLE).exists():
                time.sleep(60)
                times += 60
                if times > 1800:
                    #half an hour,timeout
                    raise Exception("Some repeaters are still under processing.")

            if self.repeater_analysis_model.objects.filter(repeater__network = self.network).exclude(process_status__lt=sekf.repeater_analysis_model.IDLE).exists():
                raise Exception("Some repeaters are processed failed")

            if self.repeater_analysis_model.objects.filter(repeater__network = self.network).filter(Q(last_analysed__isnull=True) | Q(last_analysed__lt=F("analyse_requested"))).exists():
                raise Exception("Some repeaters are outdated, please analyse the network again.")

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
            end_processing(self.analysis,self.analysis.ANALYSED,update_fields=["analyse_result"])
        except :
            end_processing(self.analysis,self.analysis.ANALYSE_FAILED,msg=traceback.format_exc())


class NetworkPostAnalysisThread(_Thread):
    def __init__(self,analysis,verify_ssl):
        super().__init__()
        self.analysis = analysis
        self.verify_ssl = verify_ssl

    def _run(self):
        _download_network_file(self.analysis,verify_ssl=self.verify_ssl)

        _process_spatial_data(self.analysis)

def get_repeater_list(queryset=None,network=None,repeater=None,force=False,scope=TX | RX):
    """
    Get the list of repeaters for analysing
    """
    if scope & (TX|RX) == 0:
        #Both tx and rx are not required to calculate the are coverage.
        return (None,None)

    if queryset:
        if isinstance(queryset,QuerySet):
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

    if scope & TX == TX:
        if not force:
            tx_qs = base_qs.filter(
                Q(tx_analysis__last_analysed__isnull=True)|
                Q(tx_analysis__last_analysed__lt=F("tx_analysis__analyse_requested"))
            ).filter(
                Q(tx_analysis__process_status=RepeaterTXAnalysis.IDLE)|
                Q(tx_analysis__process_status__lt=0)|
                (Q(tx_analysis__process_status__gt=RepeaterTXAnalysis.IDLE) & Q(tx_analysis__process_start__lt=timezone.now() - RepeaterTXAnalysis.PROCESS_TIMEOUT))
            )
        else:
            tx_qs = base_qs.all()
    else:
        tx_qs = None


    if scope & RX == RX:
        if not force:
            rx_qs = base_qs.filter(
                Q(rx_analysis__last_analysed__isnull=True)|
                Q(rx_analysis__last_analysed__lt=F("rx_analysis__analyse_requested"))
            ).filter(
                Q(rx_analysis__process_status=RepeaterRXAnalysis.IDLE)|
                Q(rx_analysis__process_status__lt=0)|
                (Q(rx_analysis__process_status__gt=RepeaterRXAnalysis.IDLE) & Q(rx_analysis__process_start__lt=timezone.now() - RepeaterRXAnalysis.PROCESS_TIMEOUT))
            )
        else:
            rx_qs = base_qs.all()
    else:
        rx_qs = None

    return (list(tx_qs) if tx_qs else None,list(rx_qs) if rx_qs else None)

class _AreaCoverage(object):
    """
    Perform the area coverage for selected repeaters
    use multi thread to improve the performance(not allowed in current account)
    repeaters shoule be order by network
    """
    def __init__(self,tx_repeaters=None,rx_repeaters=None):
        self.tx_repeaters = tx_repeaters
        self.rx_repeaters = rx_repeaters

    def run(self):
        del_endpoint = Option.get_option("del_calculation_endpoint")
    
        endpoint = Option.get_option("area_coverage_endpoint")

        verify_ssl = get_verify_ssl()

        max_analyse_tasks = Option.get_option("max_analyse_tasks",1)
        max_download_tasks = Option.get_option("max_download_tasks",5)

        options = {}
        del_options = {}

        #set the fixed options
        for k,v in fixed_options:
            options[k] = v

        threads = []
        previous_network = None
        for s,qs,get_analysis in [(TX,self.tx_repeaters,lambda r:r.tx_analysis),(RX,self.rx_repeaters,lambda r:r.rx_analysis)]:
            if not qs:
                continue
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
                thread = RepeaterAnalysisThread(dict(options),dict(del_options),s,rep,analysis,endpoint,del_endpoint,verify_ssl)
                threads.append(thread)
                thread.start()
                if len(threads) >= max_analyse_tasks:
                    _wait_threads(threads)
                    threads.clear()

                previous_network = rep.network

        if threads:
            _wait_threads(threads)
            threads.clear()

        #post analyse
        threads.clear()
        for s,repeaters,get_analysis,coverage_model in [(TX,self.tx_repeaters,lambda r:r.tx_analysis,RepeaterTXCoverage),(RX,self.rx_repeaters,lambda r:r.rx_analysis,RepeaterRXCoverage)]:
            if not repeaters:
                continue
            for repeater in repeaters:
                analysis = get_analysis(repeater)
                thread = RepeaterPostAnalysisThread(analysis,coverage_model,verify_ssl)
                threads.append(thread)
                thread.start()
                if len(threads) >= max_download_tasks:
                    _wait_threads(threads)
                    threads.clear()

        if threads:
            _wait_threads(threads)
            threads.clear()

def get_network_list(queryset=None,network=None,force=False,scope=TX | RX):
    if scope & (TX|RX) == 0:
        #Both tx and rx are not required to calculate the are coverage.
        return (None,None)
    if queryset:
        if isinstance(queryset,QuerySet):
            base_qs = queryset
        else:
            base_qs = Network.objects.filter(id__in = [r.id for r in queryset])
    else:
        if network:
            base_qs = Network.objects.filter(id = network.id)
        else:
            base_qs = Network.objects.all()

    if scope & TX == TX:
        if not force:
            tx_qs = base_qs.filter(
                Q(tx_analysis__last_analysed__isnull=True)|
                Q(tx_analysis__last_analysed__lt=F("tx_analysis__analyse_requested"))
            ).filter(
                Q(tx_analysis__process_status=NetworkTXAnalysis.IDLE)|
                Q(tx_analysis__process_status__lt=0)|
                (Q(tx_analysis__process_status__gt=NetworkTXAnalysis.IDLE) & Q(tx_analysis__process_start__lt=timezone.now() - NetworkTXAnalysis.PROCESS_TIMEOUT))
            )
        else:
            tx_qs = base_qs.all()
    else:
        tx_qs = None


    if scope & RX == RX:
        if not force:
            rx_qs = base_qs.filter(
                Q(rx_analysis__last_analysed__isnull=True)|
                Q(rx_analysis__last_analysed__lt=F("rx_analysis__analyse_requested"))
            ).filter(
                Q(rx_analysis__process_status=NetworkRXAnalysis.IDLE)|
                Q(rx_analysis__process_status__lt=0)|
                (Q(rx_analysis__process_status__gt=NetworkRXAnalysis.IDLE) & Q(rx_analysis__process_start__lt=timezone.now() - NetworkRXAnalysis.PROCESS_TIMEOUT))
            )
        else:
            rx_qs = base_qs.all()
    else:
        rx_qs = None

    return (list(tx_qs) if tx_qs else None,list(rx_qs) if rx_qs else None)


class _MeshSite(object):
    """
    Perform mesh site analysis for selected networks
    use multi thread to improve the performance(not allowed in current account)
    """
    def __init__(self,tx_networks=None,rx_networks=None):
        self.tx_networks = None
        self.rx_networks = None

    def run(self):
        #analyse the network
        endpoint = Option.get_option("mesh_site_endpoint")
    
        del_endpoint = Option.get_option("del_calculation_endpoint")
    
        verify_ssl = get_verify_ssl()

        del_options = {}

        max_analyse_tasks = Option.get_option("max_analyse_tasks",1)
        max_download_tasks = Option.get_option("max_download_tasks",5)

        #remove the calculation of the repeaters which are removed from the network
        for s,networks,get_analysis,repeater_analysis_model in [
            (TX,self.tx_networks,lambda net:net.tx_analysis,RepeaterTXAnalysis),
            (RX,self.rx_networks,lambda net:net.rx_analysis,RepeaterRXAnalysis)
        ] :
            if not networks:
                continue
            for net in networks:
                for rep_analysis in repeater_analysis_model.objects.filter(network=net.name).exclude(repeater__network=net):
                    _del_analysis_calculation(rep_analysis,del_options,endpoint=del_endpoint,target_status=RepeaterTXAnalysis.IDLE,verify_ssl=verify_ssl)
                    if rep_analysis.process_status < 0:
                        end_processing(get_analysis(net),NetworkTXAnalysis.FAILED,msg=rep_analysis.process_msg)
                        break
        options = {}
    
        #set the fixed options
        for k,v in mesh_site_fixed_options:
            options[k] = v
    
        threads = []
        for s,networks,get_analysis,repeater_analysis_model in [o for o in [
            (TX,self.tx_networks,lambda net:net.tx_analysis,RepeaterTXAnalysis),
            (RX,self.rx_networks,lambda net:net.rx_analysis,RepeaterRXAnalysis)] if o[1]]:
            #get the global option first.
            for option in mesh_site_global_options:
                if isinstance(option,str) or isinstance(option[0],str):
                    #same for all scope
                    reset_option = False
                else:
                    reset_option = True
    
                _set_global_option(s,options,option,force=reset_option)
    
            for net in networks:
                analysis = get_analysis(net)
                try:
                    thread = NetworkAnalysisThread(dict(options),dict(del_options),s,net,analysis,repeater_analysis_model,endpoint,del_endpoint,verify_ssl)
                    threads.append(thread)
                    thread.start()
                    if len(threads) >= max_analyse_tasks:
                        _wait_threads(threads)
                        threads.clear()
                    #current account plan doesn't support call webservice multipe times at the same time.
                except:
                    end_processing(analysis,analysis.ANALYSE_FAILED,msg = traceback.format_exc())
    
        if threads:
            _wait_threads(threads)
            threads.clear()
    
        #post analyse
        for s,networks,get_analysis in [o for o in [(TX,self.tx_networks,lambda r:r.tx_analysis),(RX,self.rx_networks,lambda r:r.rx_analysis)] if o[1]]:
            for net in networks:
                analysis = get_analysis(net)
                thread = NetworkPostAnalysisThread(analysis,verify_ssl)
                threads.append(thread)
                thread.start()
                if len(threads) >= max_download_tasks:
                    _wait_threads(threads)
                    threads.clear()
    
        if threads:
            _wait_threads(threads)
            threads.clear()


def analyse_repeater_coverage(queryset=None,network=None,repeater=None,force=False,scope=TX | RX):
    #get the repeater list which are required to be analysed
    tx_repeaters,rx_repeaters = get_repeater_list(queryset=queryset,network=network,repeater=repeater,force=force,scope=scope)
    #set process status to related waiting status for repeaters
    counter = 0
    for s,repeaters,get_analysis in [o for o in [
        (TX,tx_repeaters,lambda rep:RepeaterTXAnalysis.objects.get_or_create(repeater=rep,defaults={"analyse_requested":timezone.now()})[0]),
        (RX,rx_repeaters,lambda rep:RepeaterRXAnalysis.objects.get_or_create(repeater=rep,defaults={"analyse_requested":timezone.now()})[0])] if o[1]]:

        for rep in repeaters:
            analysis = get_analysis(rep)
            counter += 1
            if force:
                start_processing(analysis,analysis.WAITING)
            else:
                start_processing(analysis,analysis.WAITING_STATUS_MAPPING[analysis.process_status])

    if counter :
       #submit the task to analyse repoeaters
        _tasks.put(_AreaCoverage(tx_repeaters=tx_repeaters,rx_repeaters=rx_repeaters))
        #start the analyse worker if it is not started yeat.
        if not AnalyseWorker.instance:
            AnalyseWorker.instance = AnalyseWorker()
            AnalyseWorker.instance.start()

    return counter


def analyse_network_coverage(queryset=None,network=None,force=False,scope=TX | RX,options={}):
    #get the network list which are required to be analysed
    tx_networks,rx_networks = get_network_list(queryset=queryset,network=network,force=force,scope=scope)
    #get the repeater list which are required to be analysed
    tx_repeaters,rx_repeaters = get_repeater_list(queryset=Repeater.objects.filter(network=network) if network else Repeater.objects.filter(network__in=[o.id for o in queryset]),force=force,scope=scope)

    net_counter = 0
    rep_counter = 0
    #set process status to related waiting status for network
    for s,networks,get_analysis in [o for o in [
        (TX,tx_networks,lambda net:NetworkTXAnalysis.objects.get_or_create(network=net,defaults={"analyse_requested":timezone.now()})[0]),
        (RX,rx_networks,lambda net:NetworkRXAnalysis.objects.get_or_create(network=net,defaults={"analyse_requested":timezone.now()})[0])] if o[1]]:

        for net in networks:
            analysis = get_analysis(net)
            net_counter += 1
            if force:
                start_processing(analysis,analysis.WAITING)
            else:
                start_processing(analysis,analysis.WAITING_STATUS_MAPPING[analysis.process_status])

    #set process status to related waiting status for repeaters
    for s,repeaters,get_analysis in [o for o in [
        (TX,tx_repeaters,lambda rep:RepeaterTXAnalysis.objects.get_or_create(repeater=rep,defaults={"analyse_requested":timezone.now()})[0]),
        (RX,rx_repeaters,lambda rep:RepeaterRXAnalysis.objects.get_or_create(repeater=rep,defaults={"analyse_requested":timezone.now()})[0])] if o[1]]:

        for rep in repeaters:
            analysis = get_analysis(rep)
            rep_counter += 1
            if force:
                start_processing(analysis,analysis.WAITING)
            else:
                start_processing(analysis,analysis.WAITING_STATUS_MAPPING[analysis.process_status])

    #submit the task to analyse repoeaters
    if rep_counter:
        _tasks.put(_AreaCoverage(tx_repeaters=tx_repeaters,rx_repeaters=rx_repeaters))
    #submit the task to analyse networks
    if net_counter:
        _tasks.put(_MeshSite(network=net,force=force,scope=scope,options=options["mesh_site"],del_options=options["del_calculation"]))

    #start the analyse worker if it is not started yeat.
    if rep_counter or net_counter:
        if not AnalyseWorker.instance:
            AnalyseWorker.instance = AnalyseWorker()
            AnalyseWorker.instance.start()

    return rep_counter + net_counter

        

        
