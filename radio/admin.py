import traceback

from django.contrib import admin
from django.utils.safestring import mark_safe
from django.utils import timezone
from django.contrib import admin,messages

from .models import District,Network,Repeater,Option
from . import analysis

from .forms import RepeaterEditForm,NetworkEditForm,OptionEditForm

class RepeaterFieldsMixin(object):
    def _tx_frequency(self,obj):
        return obj.tx_frequency.normalize() if obj.tx_frequency else ""
    _tx_frequency.short_description = 'TX Frequency (mHz)'

    def _rx_frequency(self,obj):
        return obj.rx_frequency.normalize() if obj.rx_frequency else ""
    _rx_frequency.short_description = 'RX Frequency (mHz)'

    def _ctcss_tx(self,obj):
        return obj.ctcss_tx.normalize() if obj.ctcss_tx else ""
    _ctcss_tx.short_description = 'CTCSS TX (Hz)'

    def _ctcss_rx(self,obj):
        return obj.ctcss_rx.normalize() if obj.ctcss_rx else ""
    _ctcss_rx.short_description = 'CTCSS RX (Hz)'


class AnalysisFieldsMixin(object):
    def tx_analyse_result(self,obj):
        return mark_safe("<pre>{}</pre>".format((obj.tx_analysis.analyse_result or "") if obj else ""))
    tx_analyse_result.short_description = 'TX Analyse Result'

    def tx_last_analysed(self,obj):
        return obj.tx_analysis.last_analysed if obj else ""
    tx_last_analysed.short_description = 'TX Last Analysed'

    def tx_bbox(self,obj):
        return obj.tx_analysis.bbox if obj else ""
    tx_bbox.short_description = 'TX Bounding Box'

    def tx_raster_4326(self,obj):
        raster_file = '<a href="{}" target="repeater_raster">{}</a>'.format(obj.tx_analysis.raster_4326.url,obj.tx_analysis.raster_4326.name) if obj and obj.tx_analysis and obj.tx_analysis.raster_4326 else ""
        world_file = '<b style="padding-left:20px">World File:</b> <a href="{}" download>{}</a>'.format(obj.tx_analysis.world_file_4326.url,obj.tx_analysis.world_file_4326.name) if obj and obj.tx_analysis and obj.tx_analysis.world_file_4326 else ""
        return mark_safe("{}{}".format(raster_file,world_file))

    tx_raster_4326.short_description = 'TX Raster(EPSG:4326)'

    def tx_shp_file(self,obj):
        return mark_safe('<a href="{}" download>{}</a>'.format(obj.tx_analysis.shp_file.url,obj.tx_analysis.shp_file.name)) if obj and obj.tx_analysis and obj.tx_analysis.shp_file else ""
    tx_shp_file.short_description = 'TX Shape File'

    def rx_analyse_result(self,obj):
        return mark_safe("<pre>{}</pre>".format((obj.rx_analysis.analyse_result or "") if obj else ""))
    rx_analyse_result.short_description = 'RX Analyse Result'

    def rx_last_analysed(self,obj):
        return obj.rx_analysis.last_analysed if obj else ""
    rx_last_analysed.short_description = 'RX Last Analysed'

    def rx_bbox(self,obj):
        return obj.rx_analysis.bbox if obj else ""
    rx_bbox.short_description = 'RX Bounding Box'

    def rx_raster_4326(self,obj):
        raster_file = '<a href="{}" target="repeater_raster">{}</a>'.format(obj.rx_analysis.raster_4326.url,obj.rx_analysis.raster_4326.name) if obj and obj.rx_analysis and obj.rx_analysis.raster_4326 else ""
        world_file = '<b style="padding-left:20px">World File:</b> <a href="{}" download>{}</a>'.format(obj.rx_analysis.world_file_4326.url,obj.rx_analysis.world_file_4326.name) if obj and obj.rx_analysis and obj.rx_analysis.world_file_4326 else ""
        return mark_safe("{}{}".format(raster_file,world_file))

    rx_raster_4326.short_description = 'RX Raster(EPSG:4326)'

    def rx_shp_file(self,obj):
        return mark_safe('<a href="{}" download>{}</a>'.format(obj.rx_analysis.shp_file.url,obj.rx_analysis.shp_file.name)) if obj and obj.rx_analysis and obj.rx_analysis.shp_file else ""
    rx_shp_file.short_description = 'RX Shape File'


# Register your models here.
class RepeaterInline(RepeaterFieldsMixin,admin.TabularInline):
    model = Repeater
    fields = ["site_name","district","channel_number","sss_display","_tx_frequency",'_ctcss_tx','_rx_frequency','_ctcss_rx','last_inspected']
    readonly_fields = ('_tx_frequency','_ctcss_tx','_rx_frequency','_ctcss_rx')
    extra = 0

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def _tx_frequency(self,obj):
        return obj.tx_frequency.normalize()
    _tx_frequency.short_description = 'TX Frequency (mHz)'


    def save_model(self, request, obj, form, change):
        """
        Given a model instance save it to the database.
        """
        if not obj.pk:
            obj.creater = request.user
        obj.modifier = request.user

        super().save_model(request,obj,form,change)
        

@admin.register(Network)
class NetworkAdmin(AnalysisFieldsMixin,admin.ModelAdmin):
    list_display = ('name', 'comments',"tx_analyse_up2date","rx_analyse_up2date")
    ordering = ('name',)
    form = NetworkEditForm
    inlines = (RepeaterInline,)
    readonly_fields = ("tx_last_analysed","tx_bbox","tx_raster_4326","rx_last_analysed","rx_bbox","rx_raster_4326")

    #actions = ('analyse_coverage','reanalyse_coverage')
    actions = ('analyse_coverage',)

    def tx_analyse_result(self,obj):
        return mark_safe("<pre>{}</pre>".format((obj.tx_analysis.analyse_result or "") if obj else ""))
    tx_analyse_result.short_description = 'TX Analyse Result'

    def tx_analyse_up2date(self,obj):
        if not obj:
            return True
        elif not obj.tx_analysis:
            return False
        elif not obj.tx_analysis.last_analysed:
            return False
        else:
            return obj.tx_analysis.last_analysed >= obj.tx_analysis.analyse_requested
    tx_analyse_up2date.short_description = 'TX Analyse Up to Date?'
    tx_analyse_up2date.boolean = True

    def rx_analyse_up2date(self,obj):
        if not obj:
            return True
        elif not obj.rx_analysis:
            return False
        elif not obj.rx_analysis.last_analysed:
            return False
        else:
            return obj.rx_analysis.last_analysed >= obj.rx_analysis.analyse_requested
    rx_analyse_up2date.short_description = 'RX Analyse Up to Date?'
    rx_analyse_up2date.boolean = True



    def save_model(self, request, obj, form, change):
        """
        Given a model instance save it to the database.
        """
        if not obj.pk:
            obj.creater = request.user
        obj.modifier = request.user

        super().save_model(request,obj,form,change)
        form.save_repeaters()
        
    def analyse_coverage(self, request, queryset):
        options = {}
        for network in queryset:
            try:
                analysis.analyse_network_coverage(network=network,options=options)
                self.message_user(request, 'Network({}) have been analysed.'.format(network))
            except Exception as ex:
                traceback.print_exc()
                self.message_user(request, 'Failed to analyse the network({}).{}'.format(network,str(ex)),level=messages.ERROR)

    analyse_coverage.short_description = 'Analyse Coverage'

    def reanalyse_coverage(self, request, queryset):
        options = {}
        for network in queryset:
            try:
                analysis.analyse_network_coverage(network=network,options=options,force=True)
                self.message_user(request, 'Network({}) have been analysed.'.format(network))
            except Exception as ex:
                traceback.print_exc()
                self.message_user(request, 'Failed to analyse the network({}).{}'.format(network,str(ex)),level=messages.ERROR)

    reanalyse_coverage.short_description = 'Reanalyse Coverage'

@admin.register(Repeater)
class RepeaterAdmin(RepeaterFieldsMixin,AnalysisFieldsMixin,admin.ModelAdmin):
    list_display = ('site_name', 'network','district','channel_number',"_tx_frequency",'_ctcss_tx','_rx_frequency','_ctcss_rx',"tx_analyse_up2date","rx_analyse_up2date")
    ordering = ('site_name',)
    list_filter = ('district','network')
    readonly_fields = ("network","tx_last_analysed","tx_bbox","tx_raster_4326","tx_shp_file","rx_last_analysed","rx_bbox","rx_raster_4326","rx_shp_file")
    fields= ["site_name","network","district","channel_number","sss_display","sss_description","point","link_point","link_description",
            "tx_frequency","ctcss_tx","tx_antenna_height","nac_tx",
            "rx_frequency","ctcss_rx","rx_antenna_height","nac_rx",
            "output_color","output_radius","output_clutter","last_inspected",
            "tx_last_analysed","tx_bbox","tx_raster_4326","tx_shp_file","rx_last_analysed","rx_bbox","rx_raster_4326","rx_shp_file"]
    form = RepeaterEditForm
    actions = ('analyse_coverage','reanalyse_coverage')

    def info_completed(self,obj):
        return obj.is_complete if obj else False
    info_completed.boolean = True
    info_completed.short_description = 'Info Completed?'

    def tx_analyse_up2date(self,obj):
        if not obj:
            return True
        elif not obj.tx_analysis:
            return False
        elif not obj.tx_analysis.last_analysed:
            return False
        else:
            return obj.tx_analysis.last_analysed >= obj.tx_analysis.analyse_requested
    tx_analyse_up2date.short_description = 'TX Analyse Up to Date?'
    tx_analyse_up2date.boolean = True

    def rx_analyse_up2date(self,obj):
        if not obj:
            return True
        elif not obj.rx_analysis:
            return False
        elif not obj.rx_analysis.last_analysed:
            return False
        else:
            return obj.rx_analysis.last_analysed >= obj.rx_analysis.analyse_requested
    rx_analyse_up2date.short_description = 'RX Analyse Up to Date?'
    rx_analyse_up2date.boolean = True


    def analyse_coverage(self, request, queryset):
        del_endpoint = Option.objects.get(name="del_calculation_endpoint").value
        options = {}
        del_options = {}
        verify_ssl = analysis.get_verify_ssl()
        for rep in queryset:
            try:
                analysis.area_coverage(repeater=rep,force=False,scope=analysis.TX | analysis.RX,options=options,del_options=del_options,verify_ssl=verify_ssl)
                self.message_user(request, 'Repeater({}) have been analysed.'.format(rep))
            except Exception as ex:
                traceback.print_exc()
                self.message_user(request, 'Failed to analyse the repeater({}).{}'.format(rep,str(ex)),level=messages.ERROR)

    analyse_coverage.short_description = 'Analyse Coverage'

    def reanalyse_coverage(self, request, queryset):
        del_endpoint = Option.objects.get(name="del_calculation_endpoint").value
        options = {}
        del_options = {}
        verify_ssl = analysis.get_verify_ssl()
        for rep in queryset:
            try:
                analysis.area_coverage(repeater=rep,force=True,scope=analysis.TX | analysis.RX,options=options,del_options=del_options,verify_ssl=verify_ssl)
                self.message_user(request, 'Repeater({}) have been analysed.'.format(rep))
            except Exception as ex:
                traceback.print_exc()
                self.message_user(request, 'Failed to analyse the repeater({}).{}'.format(rep,str(ex)),level=messages.ERROR)

    reanalyse_coverage.short_description = 'Reanalyse Coverage'

@admin.register(Option)
class OptionAdmin(admin.ModelAdmin):
    list_display = ('name','value', '_comments')
    ordering = ('name',)
    form = OptionEditForm

    def _comments(self,obj):
        return mark_safe("<pre>{}</pre>".format((obj.comments or "") if obj else ""))
    _comments.short_description = 'Comments'

