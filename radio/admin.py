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
        #world_file = '<b style="padding-left:20px">World File:</b> <a href="{}" download>{}</a>'.format(obj.tx_analysis.world_file_4326.url,obj.tx_analysis.world_file_4326.name) if obj and obj.tx_analysis and obj.tx_analysis.world_file_4326 else ""
        #return mark_safe("{}{}".format(raster_file,world_file))
        return mark_safe(raster_file)

    tx_raster_4326.short_description = 'TX Raster(EPSG:4326)'

    def tx_shp_file(self,obj):
        shp_file = '<a href="{}" download>{}</a>'.format(obj.tx_analysis.shp_file.url,obj.tx_analysis.shp_file.name) if obj and obj.tx_analysis and obj.tx_analysis.shp_file else ""

        sld_file = '<b style="padding-left:20px">sld File:</b> <a href="/static/radio/rainbow_55.sld" download>rainbow.sld</a>' if obj and obj.tx_analysis and obj.tx_analysis.shp_file else ""
        return mark_safe("{}{}".format(shp_file,sld_file))
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
        shp_file = '<a href="{}" download>{}</a>'.format(obj.rx_analysis.shp_file.url,obj.rx_analysis.shp_file.name) if obj and obj.rx_analysis and obj.rx_analysis.shp_file else ""

        sld_file = '<b style="padding-left:20px">sld File:</b> <a href="/static/radio/rainbow_55.sld" download>rainbow.sld</a>' if obj and obj.rx_analysis and obj.rx_analysis.shp_file else ""
        return mark_safe("{}{}".format(shp_file,sld_file))

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

class StatusMixin(object):
    
    def tx_analysis_status(self,obj):
        if not obj or not obj.tx_analysis:
            return ""
        else:
            return obj.tx_analysis.status_name
    tx_analysis_status.short_description = 'TX Analysis Status'
        
    def tx_analyse_msg(self,obj):
        if not obj or not obj.tx_analysis:
            return ""
        else:
            return obj.tx_analysis.process_msg or ""
    tx_analyse_msg.short_description = 'TX Analyse Message'
        
    def rx_analysis_status(self,obj):
        if not obj or not obj.rx_analysis:
            return ""
        else:
            return obj.rx_analysis.status_name
    rx_analysis_status.short_description = 'RX Analysis Status'
        
    def rx_analyse_msg(self,obj):
        if not obj or not obj.rx_analysis:
            return ""
        else:
            return obj.rx_analysis.process_msg or ""
    rx_analyse_msg.short_description = 'RX Analyse Message'
        
    def tx_analysis_up2date(self,obj):
        if not obj:
            return True
        elif not obj.tx_analysis:
            return False
        elif not obj.tx_analysis.last_analysed:
            return False
        else:
            return obj.tx_analysis.last_analysed >= obj.tx_analysis.analyse_requested
    tx_analysis_up2date.short_description = 'TX Analysis Up to Date?'
    tx_analysis_up2date.boolean = True

    def rx_analysis_up2date(self,obj):
        if not obj:
            return True
        elif not obj.rx_analysis:
            return False
        elif not obj.rx_analysis.last_analysed:
            return False
        else:
            return obj.rx_analysis.last_analysed >= obj.rx_analysis.analyse_requested
    rx_analysis_up2date.short_description = 'RX Analysis Up to Date?'
    rx_analysis_up2date.boolean = True

@admin.register(Network)
class NetworkAdmin(StatusMixin,AnalysisFieldsMixin,admin.ModelAdmin):
    list_display = ('name', 'comments',"tx_analysis_status","rx_analysis_status")
    ordering = ('name',)
    form = NetworkEditForm
    inlines = (RepeaterInline,)
    readonly_fields = ("tx_analysis_status","tx_analyse_msg","rx_analysis_status","rx_analyse_msg","tx_last_analysed","tx_bbox","tx_raster_4326","rx_last_analysed","rx_bbox","rx_raster_4326")

    #actions = ('analyse_tx_coverage','analyse_rx_coverage','reanalyse_tx_coverage',reanalyse_rx_coverage)
    actions = ('analyse_tx_coverage','analyse_rx_coverage')

    def tx_analyse_result(self,obj):
        return mark_safe("<pre>{}</pre>".format((obj.tx_analysis.analyse_result or "") if obj else ""))
    tx_analyse_result.short_description = 'TX Analyse Result'

    def save_model(self, request, obj, form, change):
        """
        Given a model instance save it to the database.
        """
        if not obj.pk:
            obj.creater = request.user
        obj.modifier = request.user

        super().save_model(request,obj,form,change)
        form.save_repeaters()
        
    def _analyse_coverage(self, request, queryset,scope,force):
        counter = analysis.analyse_network_coverage(queryset=queryset,scope=scope,force=force)
        if counter:
            self.message_user(request, 'The network analysing task was submitted.')
        else:
            self.message_user(request, 'All chosen networks is up to date or under processing')

    def analyse_tx_coverage(self, request, queryset):
        self._analyse_coverage(request,queryset,analysis.TX,False)
    analyse_tx_coverage.short_description = 'Analyse TX Coverage'

    def analyse_rx_coverage(self, request, queryset):
        self._analyse_coverage(request,queryset,analysis.RX,False)
    analyse_rx_coverage.short_description = 'Analyse RX Coverage'

    def reanalyse_tx_coverage(self, request, queryset):
        self._analyse_coverage(request,queryset,analysis.TX,True)
    reanalyse_tx_coverage.short_description = 'Reanalyse TX Coverage'

    def reanalyse_rx_coverage(self, request, queryset):
        self._analyse_coverage(request,queryset,analysis.RX,True)
    reanalyse_rx_coverage.short_description = 'Reanalyse RX Coverage'


@admin.register(Repeater)
class RepeaterAdmin(StatusMixin,RepeaterFieldsMixin,AnalysisFieldsMixin,admin.ModelAdmin):
    list_display = ('site_name', 'network','district','channel_number',"_tx_frequency",'_ctcss_tx','_rx_frequency','_ctcss_rx',"tx_analysis_status","rx_analysis_status")
    ordering = ('site_name',)
    list_filter = ('district','network')
    readonly_fields = ("network","tx_last_analysed","tx_bbox","tx_raster_4326","tx_shp_file","rx_last_analysed","rx_bbox","rx_raster_4326","rx_shp_file","tx_analysis_status","tx_analyse_msg","rx_analysis_status","rx_analyse_msg")
    fields= ["site_name","network","district","channel_number","sss_display","sss_description","point","link_point","link_description",
            "tx_frequency","ctcss_tx","tx_antenna_height","nac_tx","tx_power","tx_antenna_gain",
            "rx_frequency","ctcss_rx","rx_antenna_height","nac_rx","rx_power","rx_antenna_gain",
            "output_color","output_radius","output_clutter","last_inspected",
            "tx_last_analysed","tx_bbox","tx_raster_4326","tx_shp_file","rx_last_analysed","rx_bbox","rx_raster_4326","rx_shp_file",
            "tx_analysis_status","tx_analyse_msg","rx_analysis_status","rx_analyse_msg"]
    form = RepeaterEditForm
    actions = ('analyse_tx_coverage','analyse_rx_coverage','reanalyse_tx_coverage','reanalyse_rx_coverage')
    #actions = ('analyse_tx_coverage','analyse_rx_coverage')

    def info_completed(self,obj):
        return obj.is_complete if obj else False
    info_completed.boolean = True
    info_completed.short_description = 'Info Completed?'


    def _analyse_coverage(self, request, queryset,scope,force):
        counter = analysis.analyse_repeater_coverage(queryset=queryset,scope=scope,force=force)
        if counter:
            self.message_user(request, 'The repeater analysing task was submitted.')
        else:
            self.message_user(request, 'All chosen repeaters is up to date or under processing')

    def analyse_tx_coverage(self, request, queryset):
        self._analyse_coverage(request,queryset,analysis.TX,False)
    analyse_tx_coverage.short_description = 'Analyse TX Coverage'

    def analyse_rx_coverage(self, request, queryset):
        self._analyse_coverage(request,queryset,analysis.RX,False)
    analyse_rx_coverage.short_description = 'Analyse RX Coverage'

    def reanalyse_tx_coverage(self, request, queryset):
        self._analyse_coverage(request,queryset,analysis.TX,True)
    reanalyse_tx_coverage.short_description = 'Reanalyse TX Coverage'

    def reanalyse_rx_coverage(self, request, queryset):
        self._analyse_coverage(request,queryset,analysis.RX,True)
    reanalyse_rx_coverage.short_description = 'Reanalyse RX Coverage'

@admin.register(Option)
class OptionAdmin(admin.ModelAdmin):
    list_display = ('name','value', '_comments')
    ordering = ('name',)
    form = OptionEditForm

    def _comments(self,obj):
        return mark_safe("<pre>{}</pre>".format((obj.comments or "") if obj else ""))
    _comments.short_description = 'Comments'

