import os

from django import forms
from django.utils.safestring import mark_safe
from django.contrib.gis.geos import Point
from django.contrib.admin.widgets import FilteredSelectMultiple

from . import models

class ReadonlyWidget(forms.HiddenInput):

    def __init__(self,f_display=None,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self._f_display = f_display if f_display else lambda value:str(value) if value is not None else ""

    @property
    def is_hidden(self):
        return False

    def render(self, name, value, attrs=None, renderer=None):
        return "{}{}".format(super().render(name,value,attrs=attrs,renderer=renderer),self._f_display(value))

text_readonly_widget = ReadonlyWidget()
boolean_readonly_widget = ReadonlyWidget(lambda value: '<img src="/static/admin/img/icon-yes.svg" alt="True">' if value else '<img src="/static/admin/img/icon-no.svg" alt="True">')


class LabeledMixin(object):
    _template_name = None
    def __init__(self,label, *args,**kwargs):
        self.label = mark_safe(label)
        super().__init__(*args,**kwargs)

    @property
    def template_name(self):
        if not self._template_name:
            self._template_name = os.path.splitext(os.path.split(super().template_name)[1])
            self._template_name = "{}_labeled{}".format(*self._template_name)

        return self._template_name

    def get_context(self, name, value, attrs):
        context = super().get_context(name,value,attrs)
        context['widget']['label'] = self.label
        return context

class LabeledNumberInput(LabeledMixin,forms.NumberInput):
    pass

class PointWidget(forms.MultiWidget):

    def __init__(self, attrs=None):
        widgets = [
            LabeledNumberInput("<b style='padding-right:10px'>Longitude</b>",attrs={"step":0.001}),
            LabeledNumberInput("<b style='padding-left:20px;padding-right:10px'>Latitude</b>",attrs={"step":0.001})
        ]
        super().__init__(widgets, attrs)

    def decompress(self,value):
        if value:
            return value.x,value.y
        return [None,None]

    def value_from_datadict(self,data,files,name):
        x,y = super().value_from_datadict(data,files,name)
        if x and y:
            return Point(float(x),float(y))
        else:
            return None
class NetworkEditForm(forms.ModelForm):
    repeaters = forms.ModelMultipleChoiceField(queryset=models.Repeater.objects.all().order_by("district__name","site_name"),widget=FilteredSelectMultiple(verbose_name='Repeater',is_stacked=False),required=False)

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        if self.instance and self.instance.pk:
            self.initial["repeaters"] = models.Repeater.objects.filter(network=self.instance)


    def save(self,*args,**kwargs):
        obj = super().save(*args,**kwargs)
        if kwargs["commit"]:
            self.save_repeaters()

        return obj

        

    def save_repeaters(self):
        repeaters = self.cleaned_data["repeaters"]
        repeater_ids = [obj.id for obj in repeaters] if repeaters else []
        for repeater in models.Repeater.objects.filter(network=self.instance).exclude(id__in=repeater_ids):
            repeater.network = None
            repeater.save(update_fields=["network"])
        for repeater in models.Repeater.objects.filter(id__in=repeater_ids).exclude(network=self.instance):
            repeater.network = self.instance
            repeater.save(update_fields=["network"])

    class Meta:
        model = models.Network
        fields = "__all__"
        widgets = {
        }


class RepeaterEditForm(forms.ModelForm):
    class Meta:
        model = models.Repeater
        fields = "__all__"
        widgets = {
            "point":PointWidget(),
            "link_point":PointWidget(),
            "tx_frequency":forms.NumberInput(attrs={"step":0.001}),
            "rx_frequency":forms.NumberInput(attrs={"step":0.001}),
            "ctcss_tx":forms.NumberInput(attrs={"step":0.001}),
            "ctcss_rx":forms.NumberInput(attrs={"step":0.001}),
            "sss_description":forms.TextInput(attrs={"style":"width:80%"}),
            "link_description":forms.TextInput(attrs={"style":"width:80%"}),
        }

class OptionEditForm(forms.ModelForm):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        if self.instance :
            if self.instance.pk:
                if "name" in self.fields :
                    self.fields["name"].widget = text_readonly_widget
            
    class Meta:
        model = models.Option
        fields = "__all__"
        widgets = {
            "comments":forms.Textarea(attrs={"style":"width:80%"}),
        }

