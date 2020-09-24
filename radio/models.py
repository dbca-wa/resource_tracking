import traceback
import os
import logging
import requests
import itertools
import json
from datetime import timedelta

from django.utils import timezone
from django.conf import settings
from django.contrib.gis.db import models
from django.contrib.auth.models import User
from django.core import validators
from django.db import connection
from django.core.exceptions import ObjectDoesNotExist
from django.dispatch import receiver
from django.db.models.signals import post_save,pre_save,post_delete
from django.contrib.postgres.fields import ArrayField,JSONField
from django.core.files.storage import FileSystemStorage


logger = logging.getLogger(__name__)

_programmatic_user = None
def get_user_program():
    """

    """
    global _programmatic_user
    if not _programmatic_user:
        try:
            _programmatic_user = User.objects.get(username='Programmatic')
        except ObjectDoesNotExist as ex:
            with connection.cursor() as cursor:
                try:
                    cursor.execute("""
                    INSERT INTO auth_user 
                        (username,first_name,last_name,email,is_staff,is_active,is_superuser,password,date_joined) 
                    VALUES 
                        ('Programmatic','Programmatic','System','programmatic.system@dbca.wa.gov.au',false,true,false,'','{}')
                    """.format(timezone.now().strftime('%Y-%m-%d %H:%M:%S %Z')))
                except:
                    pass
                _programmatic_user = User.objects.get(username='Programmatic')

    return _programmatic_user

# Create your models here.
class Option(models.Model):
    _tvalue = None

    name = models.CharField(max_length=32,unique=True)
    comments = models.TextField(max_length=512,null=True,blank=True)
    value = models.CharField(max_length=64,null=True,blank=True)

    @property
    def tvalue(self):
        """
        typed value
        """
        if self.value is None or self.value == "":
            return None

        if self._tvalue is None:
            try:
                self._tvalue =  json.loads(self.value)
            except:
                self._tvalue = self.value

        return self._tvalue

    @classmethod
    def get_option(cls,key,default=None):
        try:
            return Option.objects.get(name=key).tvalue
        except:
            return default

    

    def __str__(self):
        return "Option({})".format(self.name)

    class Meta:
        ordering = ["name"]


class District(models.Model):
    name = models.CharField(max_length=64,unique=True,null=False,editable=False)

    def clean(self):
        if self.value:
            self.value = self.value.strip()

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]

class Network(models.Model):
    name = models.CharField(max_length=64,unique=True,null=False)
    comments = models.CharField(max_length=512,null=True,blank=True)

    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, blank=True, null=True, on_delete=models.PROTECT,
        related_name='+', editable=False)
    modifier = models.ForeignKey(
        settings.AUTH_USER_MODEL, blank=True, null=True, on_delete=models.PROTECT,
        related_name='+', editable=False)
    created = models.DateTimeField(default=timezone.now, editable=False)
    modified = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]

class Repeater(models.Model):
    site_name = models.CharField(max_length=128,unique=True)
    network = models.ForeignKey(Network,on_delete=models.SET_NULL,null=True,blank=True,editable=False)
    last_inspected = models.DateField(default=timezone.now, null=True,blank=True)
    sss_display = models.BooleanField(default=True,verbose_name="SSS Display Enabled")
    sss_description = models.CharField(max_length=512,null=True,blank=True)
    district = models.ForeignKey(District,on_delete=models.PROTECT,null=True,blank=True)
    channel_number = models.SmallIntegerField(null=True,blank=True)
    point = models.PointField(null=True,blank=True)
    link_description = models.CharField(max_length=512,null=True,blank=True)
    link_point = models.PointField(null=True,blank=True)
    tx_frequency = models.DecimalField(max_digits=16,decimal_places=8,null=True,blank=True,verbose_name="TX Frequency (mHz)")
    rx_frequency = models.DecimalField(max_digits=16,decimal_places=8,null=True,blank=True,verbose_name="RX Frequency (mHz)")
    ctcss_tx = models.DecimalField(max_digits=16,decimal_places=8,null=True,blank=True,verbose_name="CTCSS TX (Hz)")
    ctcss_rx = models.DecimalField(max_digits=16,decimal_places=8,null=True,blank=True,verbose_name="CTCSS RX (Hz)")
    nac_tx = models.CharField(max_length=32,null=True,blank=True,verbose_name="NAC TX (P25)")
    nac_rx = models.CharField(max_length=32,null=True,blank=True,verbose_name="NAC RX (P25)")
    tx_antenna_height = models.FloatField(null=True,blank=True,verbose_name="TX Antenna Height (M)")
    rx_antenna_height = models.FloatField(null=True,blank=True,verbose_name="RX Antenna Height (M)")
    tx_power = models.FloatField(null=True,blank=True,verbose_name="TX Transmitter RF power in Watts,20dBm=0.1w")
    rx_power = models.FloatField(null=True,blank=True,verbose_name="RX Transmitter RF power in Watts,20dBm=0.1w")
    tx_antenna_gain = models.FloatField(null=True,blank=True,verbose_name="TX Transmitter antenna  gain in dBi")
    rx_antenna_gain = models.FloatField(null=True,blank=True,verbose_name="RX Transmitter antenna  gain in dBi")
    output_color = models.CharField(max_length=32,null=True,blank=True)
    output_radius = models.FloatField(null=True,blank=True,verbose_name="Output Radius (Km)")
    output_clutter = models.FloatField(null=True,blank=True,verbose_name="Output Clutter (M)")

    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, blank=True, null=True, on_delete=models.PROTECT,
        related_name='+', editable=False)
    modifier = models.ForeignKey(
        settings.AUTH_USER_MODEL, blank=True, null=True, on_delete=models.PROTECT,
        related_name='+', editable=False)
    created = models.DateTimeField(default=timezone.now, editable=False)
    modified = models.DateTimeField(auto_now=True, editable=False)

    @property
    def longitude(self):
        return self.point.x if self.point else None

    @property
    def latitude(self):
        return self.point.y if self.point else None

    @property
    def link_longitude(self):
        return self.link_point.x if self.link_point else None

    @property
    def link_latitude(self):
        return self.link_point.x if self.link_point else None

    @property
    def is_complete(self):
        return True if (self.point and self.channel_number and self.tx_frequency and self.rx_frequency and self.tx_antenna_height and self.rx_antenna_height) else False

    def __str__(self):
        return "{} - {}".format(self.district,self.site_name)

    class Meta:
        ordering = ["district__name","site_name"]

class OverwriteStorage(FileSystemStorage):

    def get_available_name(self, name):
        """Returns a filename that's free on the target storage system, and
        available for new content to be written to.

        Found at http://djangosnippets.org/snippets/976/

        This file storage solves overwrite on upload problem. Another
        proposed solution was to override the save method on the model
        like so (from https://code.djangoproject.com/ticket/11663):

        def save(self, *args, **kwargs):
            try:
                this = MyModelName.objects.get(id=self.id)
                if this.MyImageFieldName != self.MyImageFieldName:
                    this.MyImageFieldName.delete()
            except: pass
            super(MyModelName, self).save(*args, **kwargs)
        """
        # If the filename already exists, remove it as if it was a true file system
        if self.exists(name):
            os.remove(os.path.join(settings.MEDIA_ROOT, name))
        return name

def network_file_path(instance,filename,suffix=None):
    if isinstance(instance,NetworkTXAnalysis):
        folder = "tx"
    else:
        folder = "rx"

    ext = os.path.splitext(filename)[1]
   
    name = instance.network.name.lower().replace(" ","_")
    if suffix :
        return os.path.join("radio","networks",name,folder,"{}_{}_{}{}".format(name,folder,suffix,ext))
    else:
        return os.path.join("radio","networks",name,folder,"{}_{}{}".format(name,folder,ext))

def network_4326_file_path(instance,filename):
    return network_file_path(instance,filename,suffix="4326")

def network_mercator_file_path(instance,filename):
    return network_file_path(instance,filename,suffix="mercator")

class CoverageAnalysis(models.Model):
    IDLE = 0

    WAITING = 110
    
    WAITING_TO_DELETE = 120
    DELETING = 121
    DELETE_FAILED = -122
    DELETED = 129

    WAITING_TO_ANALYSE = 130
    ANALYSING = 131
    ANALYSE_FAILED = -132
    ANALYSED = 139

    WAITING_TO_DOWNLOAD = 140
    DOWNLOADING = 141
    DOWNLOAD_FAILED = -142
    DOWNLOADED = 149

    WAITING_TO_EXTRACT = 150
    EXTRACTING = 151
    EXTRACT_FAILED = -152
    EXTRACT_REQUIRED = -153
    EXTRACTED = 159

    #Failed statuses
    TIMEOUT = -9998
    FAILED = -9999

    PROCESS_STATUS_CHOICES = (
        (IDLE,"Idle"),
        (WAITING,"Waiting to process"),

        (DELETE_FAILED ,"Delete Failed"),
        (WAITING_TO_DELETE ,"Waiting to delete"),
        (DELETING,"Deleting Calculation"),
        (DELETED,"Deleted Calculation"),

        (ANALYSE_FAILED,"Analyse Failed"),
        (WAITING_TO_ANALYSE ,"Waiting to analyse"),
        (ANALYSING,"Analysing"),
        (ANALYSED,"Analysed"),

        (DOWNLOAD_FAILED,"Download Failed"),
        (WAITING_TO_DOWNLOAD ,"Waiting to download"),
        (DOWNLOADING,"Downloading"),
        (DOWNLOADED,"Downloaded"),

        (EXTRACT_FAILED,"Extracting Failed"),
        (EXTRACT_REQUIRED,"Extract Required"),
        (WAITING_TO_EXTRACT ,"Waiting to extract"),
        (EXTRACTING,"Extrating Spatial Data"),

        (TIMEOUT,"Timeout"),
        (FAILED,"Failed"),
    )
    PROCESS_STATUS_MAPPING = dict(PROCESS_STATUS_CHOICES)

    WAITING_STATUS_MAPPING = {
        IDLE:WAITING,
        WAITING:WAITING,

        WAITING_TO_DELETE:WAITING_TO_DELETE,
        DELETING:WAITING_TO_DELETE,
        DELETE_FAILED:WAITING_TO_DELETE,
        DELETED:WAITING_TO_ANALYSE,

        WAITING_TO_ANALYSE:WAITING_TO_ANALYSE,
        ANALYSING:WAITING_TO_ANALYSE,
        ANALYSE_FAILED:WAITING_TO_ANALYSE,
        ANALYSED:WAITING_TO_DOWNLOAD,

        WAITING_TO_DOWNLOAD:WAITING_TO_DOWNLOAD,
        DOWNLOADING:WAITING_TO_DOWNLOAD,
        DOWNLOAD_FAILED:WAITING_TO_DOWNLOAD,
        DOWNLOADED:WAITING_TO_EXTRACT,

        WAITING_TO_EXTRACT:WAITING_TO_EXTRACT,
        EXTRACTING:WAITING_TO_EXTRACT,
        #EXTRACT_FAILED:WAITING_TO_DOWNLOAD,
        EXTRACT_FAILED:WAITING_TO_EXTRACT,
        EXTRACT_REQUIRED:WAITING_TO_EXTRACT,

        TIMEOUT:WAITING,
        FAILED:WAITING
    }

    PROCESS_TIMEOUT = timedelta(hours=6)

    process_status = models.SmallIntegerField(default=IDLE,choices=PROCESS_STATUS_CHOICES,editable=False)
    process_msg = models.TextField(editable=False,null=True)
    process_start = models.DateTimeField(editable=False,null=True)
    process_end = models.DateTimeField(editable=False,null=True)

    @property
    def process_status_name(self):
        if self.process_status > self.IDLE and timezone.now() - self.process_start > self.PROCESS_TIMEOUT:
            return "Timeout"
        else:
            return self.PROCESS_STATUS_CHOICES[self.process_status]

    @property
    def status_name(self):
        status = self.process_status
        if self.process_status > self.IDLE and timezone.now() - self.process_start > self.PROCESS_TIMEOUT:
            status = self.IDLE

        if status == self.IDLE:
            if not self.last_analysed:
                return "Outdated"
            elif self.last_analysed < self.analyse_requested:
                return "Outdated"
            else:
                return "Latest"
        else:
            return self.PROCESS_STATUS_MAPPING[status]

    @property
    def is_outdated(self):
        if not self.last_analysed:
            return True
        elif self.last_analysed < self.analyse_requested:
            return True
        else:
            return False



    class Meta:
        abstract = True

class NetworkAnalysis(CoverageAnalysis):
    analyse_requested = models.DateTimeField(editable=False)
    last_analysed = models.DateTimeField(editable=False,null=True)

    analyse_result = JSONField(null=True,editable=False)
    raster_4326 = models.FileField(max_length=512,null=True,editable=False,upload_to=network_4326_file_path, storage=OverwriteStorage())
    world_file_4326 = models.FileField(max_length=512,null=True,editable=False,upload_to=network_4326_file_path, storage=OverwriteStorage())
    #raster_mercator = models.FileField(max_length=512,null=True,editable=False,upload_to=network_mercator_file_path, storage=OverwriteStorage())
    #world_file_mercator = models.FileField(max_length=512,null=True,editable=False,upload_to=network_mercator_file_path, storage=OverwriteStorage())
    bbox = ArrayField(base_field=models.FloatField(),size=4,null=True,editable=False) #left bottom lon,left bottom lon,upper right lon,upper right lat 

    class Meta:
        abstract = True

class NetworkTXAnalysis(NetworkAnalysis):
    network = models.OneToOneField(Network,on_delete=models.CASCADE,primary_key=True,editable=False,related_name="tx_analysis")

class NetworkRXAnalysis(NetworkAnalysis):
    network = models.OneToOneField(Network,on_delete=models.CASCADE,primary_key=True,editable=False,related_name="rx_analysis")

def repeater_file_path(instance,filename,suffix=None,ext=None):
    if isinstance(instance,RepeaterTXAnalysis):
        folder = "tx"
    else:
        folder = "rx"

    if not ext:
        ext = os.path.splitext(filename)[1]
   
    site_name = instance.repeater.site_name.lower().replace(" ","_")
    if suffix :
        return os.path.join("radio","repeaters",site_name,folder,"{}_{}_{}{}".format(site_name,folder,suffix,ext))
    else:
        return os.path.join("radio","repeaters",site_name,folder,"{}_{}{}".format(site_name,folder,ext))

def repeater_4326_file_path(instance,filename):
    return repeater_file_path(instance,filename,suffix="4326",ext=".tiff")

def repeater_mercator_file_path(instance,filename):
    return repeater_file_path(instance,filename,suffix="mercator")

def repeater_shp_file_path(instance,filename):
    return repeater_file_path(instance,filename,ext=".shp.zip")

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

class RepeaterAnalysis(CoverageAnalysis):
    network = models.CharField(max_length=64,null=True,editable=False)
    analyse_requested = models.DateTimeField(editable=False)
    last_analysed = models.DateTimeField(editable=False,null=True)
    last_merged = models.DateTimeField(editable=False,null=True)
    last_resolved = models.DateTimeField(editable=False,null=True)
    last_simplified = models.DateTimeField(editable=False,null=True)

    analyse_result = JSONField(null=True,editable=False)
    raster_4326 = models.FileField(max_length=512,null=True,editable=False,upload_to=repeater_4326_file_path, storage=OverwriteStorage())
    world_file_4326 = models.FileField(max_length=512,null=True,editable=False,upload_to=repeater_4326_file_path, storage=OverwriteStorage())
    #raster_mercator = models.FileField(max_length=512,null=True,editable=False,upload_to=repeater_mercator_file_path, storage=OverwriteStorage())
    #world_file_mercator = models.FileField(max_length=512,null=True,editable=False,upload_to=repeater_mercator_file_path, storage=OverwriteStorage())
    shp_file = models.FileField(max_length=512,null=True,editable=False,upload_to=repeater_shp_file_path, storage=OverwriteStorage())
    bbox = ArrayField(base_field=models.FloatField(),size=4,null=True,editable=False) #left bottom lon,left bottom lon,upper right lon,upper right lat 


    @property
    def raster_4326_path(self):
        return os.path.join(settings.MEDIA_ROOT,self.raster_4326.name) if self.raster_4326 else None

    @property
    def raster_4326_filename(self):
        return os.path.split(self.raster_4326.name)[1] if self.raster_4326 else None

    @property
    def raster_4326_basename(self):
        return os.path.splitext(os.path.split(self.raster_4326.name)[1])[0] if self.raster_4326 else None


    class Meta:
        abstract = True

class RepeaterTXAnalysis(RepeaterAnalysis):
    repeater = models.OneToOneField(Repeater,on_delete=models.CASCADE,primary_key=True,editable=False,related_name="tx_analysis")

class RepeaterRXAnalysis(RepeaterAnalysis):
    repeater = models.OneToOneField(Repeater,on_delete=models.CASCADE,primary_key=True,editable=False,related_name="rx_analysis")


class RepeaterCoverage(models.Model):
    repeater = models.ForeignKey(Repeater,on_delete=models.CASCADE,editable=False,related_name="+")
    site_name = models.CharField(max_length=128)
    district = models.CharField(max_length=64,null=False,editable=False)
    dn= models.IntegerField(null=True,editable=False)
    geom = models.MultiPolygonField(null=True,editable=False)

    class Meta:
        abstract = True

class RepeaterTXCoverage(RepeaterCoverage):
    pass

class RepeaterRXCoverage(RepeaterCoverage):
    pass

class RepeaterTXCoverageSimplified(RepeaterCoverage):
    color = models.CharField(max_length=16,null=True,editable=False)
    pass

class RepeaterRXCoverageSimplified(RepeaterCoverage):
    color = models.CharField(max_length=16,null=True,editable=False)
    pass

class AnalysisListener(object):
    @staticmethod
    @receiver(pre_save, sender=Repeater)
    def update_analysis_4_existing_repeater(sender,instance,**kwargs):
        if instance.pk is None:
            #new repeater,process in post_save
            return

        existing_repeater = Repeater.objects.get(pk=instance.pk)

        AnalysisListener._update_analysis(existing_repeater,instance)

    @staticmethod
    @receiver(post_save, sender=Repeater)
    def update_analysis_4_new_repeater(sender,instance,created,**kwargs):
        if created:
            #new repeater
            AnalysisListener._update_analysis(None,instance)

    @staticmethod
    @receiver(post_delete, sender=Repeater)
    def update_analysis_4_deleted_repeater(sender,instance,**kwargs):
        AnalysisListener._update_analysis(instance,None)

    @staticmethod
    @receiver(post_save, sender=Network)
    def create_network_analysis(sender,instance,created,**kwargs):
        if created:
            #new network,create related network analysis object
            now = timezone.now()
            NetworkTXAnalysis(network=instance,analyse_requested=now).save()
            NetworkRXAnalysis(network=instance,analyse_requested=now).save()

    @staticmethod
    @receiver(pre_save, sender=Network)
    def create_network_analysis(sender,instance,**kwargs):
        if not instance.pk:
            #new network
            return
        existing_network = Network.objects.get(pk=instance.pk)
        if instance.name != existing_network.name:
            #network name changed.
            now = timezone.now()
            for rep in Repeater.objects.filter(network=instance):
                RepeaterTXAnalysis.objects.update_or_create(repeater=r,defaults={"analyse_requested":now})
                RepeaterRXAnalysis.objects.update_or_create(repeater=r,defaults={"analyse_requested":now})

    @staticmethod
    def _update_analysis(existing_repeater,repeater):
        #update repeater analysis data
        tx_changed = False
        rx_changed = False
        now = timezone.now()
        if repeater:
            #update or create repeater
            if existing_repeater:
                try:
                    tx_analysis = RepeaterTXAnalysis.objects.get(repeater=existing_repeater)
                except ObjectDoesNotExist as ex:
                    tx_analysis = None
                try:
                    rx_analysis = RepeaterRXAnalysis.objects.get(repeater=existing_repeater)
                except ObjectDoesNotExist as ex:
                    rx_analysis = None
            else:
                tx_analysis = None
                rx_analysis = None
    
            if tx_analysis is None:
                RepeaterTXAnalysis(repeater=repeater,analyse_requested=now).save()
                tx_changed = True
            else:
                for key in ["network","point","output_radius","output_clutter","tx_frequency","tx_antenna_height"]:
                    if getattr(existing_repeater,key) != getattr(repeater,key):
                        tx_analysis.analyse_requested = now
                        tx_analysis.save(update_fields=["analyse_requested"])
                        tx_changed = True
                        break
    
            if rx_analysis is None:
                RepeaterRXAnalysis(repeater=repeater,analyse_requested=now).save()
                rx_cahnged = True
            else:
                for key in ["network","point","output_radius","output_clutter","rx_frequency","rx_antenna_height"]:
                    if getattr(existing_repeater,key) != getattr(repeater,key):
                        rx_analysis.analyse_requested = now
                        rx_analysis.save(update_fields=["analyse_requested"])
                        rx_changed = True
                        break

        #update network analysis data
        previous_network_tx_changed = False
        previous_network_rx_changed = False
        network_tx_changed = False
        network_rx_changed = False

        if existing_repeater:
            previous_network = existing_repeater.network
        else:
            previous_network = None

        if repeater:
            network = repeater.network
        else:
            network = None

        if previous_network != network:
            if previous_network:
                previous_network_tx_changed = True
                previous_network_rx_changed = True
            if network:
                network_tx_changed = True
                network_rx_changed = True
        elif network:
            network_tx_changed = tx_changed
            network_rx_changed = rx_changed

        if previous_network_tx_changed:
            NetworkTXAnalysis.objects.update_or_create(network=previous_network,defaults={"analyse_requested":now})

        if previous_network_rx_changed:
            NetworkRXAnalysis.objects.update_or_create(network=previous_network,defaults={"analyse_requested":now})

        if network_tx_changed:
            NetworkTXAnalysis.objects.update_or_create(network=repeater.network,defaults={"analyse_requested":now})

        if network_rx_changed:
            NetworkRXAnalysis.objects.update_or_create(network=repeater.network,defaults={"analyse_requested":now})


class OptionListener(object):
    @staticmethod
    @receiver(pre_save, sender=Option)
    def update_analysis_4_existing_option(sender,instance,**kwargs):
        try:
            existing_option = Option.objects.get(pk=instance.pk)
        except ObjectDoesNotExist as ex:
            #new option
            return

        OptionListener._update_analysis(existing_option,instance)

    @staticmethod
    @receiver(post_save, sender=Option)
    def update_analysis_4_new_option(sender,instance,created,**kwargs):
        if created:
            #new repeater
            OptionListener._update_analysis(None,instance)

    @staticmethod
    @receiver(post_delete, sender=Option)
    def update_analysis_4_deleted_option(sender,instance,**kwargs):
        OptionListener._update_analysis(instance,None)

    def _update_analysis(existing_option,option):
        from .analysis import global_options,extract_options
        if not option:
            #delete
            if not existing_option.value:
                #deleted option'value is null
                return
        elif existing_option:
            if existing_option.value == option.value:
                #not changed
                return
        elif not option.value:
            #empty value
            return

        name = option.name if option else existing_option.name

        changed = False
        for key in global_options:
            if isinstance(key,str):
                if key == name:
                    changed = True
                    break
            elif isinstance(key,(list,tuple)):
                if isinstance(key[1],(list,tuple)):
                    #depenedent option
                    if isinstance(key[0],str):
                        #normal dependent option
                        if key[0] == name:
                            changed = True
                            break
                    elif isinstance(key[0],(list,tuple)) and callable(key[0][1]):
                        #computable dependent option,all computable option's name should start with '[webservice option name]_'
                        if key[0][0] == name or name.startswith("{}_".format(key[0][0])):
                            changed = True
                            break
                elif callable(key[1]):
                    #computable option,computable option name must be the option name or be prefixed with option name used in rest api and a underscore 
                    if key[0] == name or name.startswith("{}_".format(key[0])):
                        changed = True
                        break


        if changed:
            #option's value was changed, all repeaters and networks should be reanalyszed.
            now = timezone.now()
            RepeaterTXAnalysis.objects.all().update(analyse_requested=now)
            RepeaterRXAnalysis.objects.all().update(analyse_requested=now)

            NetworkTXAnalysis.objects.all().update(analyse_requested=now)
            NetworkRXAnalysis.objects.all().update(analyse_requested=now)

        if option.name in extract_options:
            now = timezone.now()
            status  = None
            for analysis in itertools.chain(RepeaterTXAnalysis.objects.all(),RepeaterRXAnalysis.objects.all()):
                if analysis.process_status > analysis.IDLE and now - analysis.process_start > analysis.PROCESS_TIMEOUT:
                    status = analsis.IDLE
                else:
                    status = analysis.process_status
                
                if status == analysis.IDLE:
                    if analysis.is_outdated:
                        #outdated
                        continue
                    else:
                        analysis.process_status = analysis.EXTRACT_REQUIRED
                elif abs(status) < analysis.WAITING_TO_EXTRACT:
                    #running the stages before extracting
                    continue
                else:
                    analysis.process_status = analysis.EXTRACT_REQUIRED
                analysis.save(update_fields=["process_status"])

