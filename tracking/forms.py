from crispy_forms.bootstrap import Alert
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div, Field, Fieldset, Layout, Submit
from django import forms

from tracking.models import Device


class DeviceForm(forms.ModelForm):
    last_seen = forms.CharField(required=False)
    save_button = Submit("save", "Save", css_class="btn-lg")
    cancel_button = Submit("cancel", "Cancel", css_class="btn-secondary")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # crispy_forms layout
        self.helper = FormHelper()
        self.helper.form_class = "form-horizontal pb-1"
        self.helper.label_class = "col-xs-12 col-sm-4 col-md-2"
        self.helper.field_class = "col-xs-12 col-sm-8 col-md-10"
        self.helper.help_text_inline = True
        self.helper.field_classes = " btn btn-default"
        self.fields["last_seen"].required = False
        self.fields["last_seen"].disabled = False
        self.fields["last_seen"].widget = forms.TextInput(attrs={"readonly": ""})
        self.fields["registration"].required = False
        self.fields["registration"].disabled = False
        self.fields["registration"].widget = forms.TextInput(attrs={"readonly": ""})
        self.fields["other_details"].widget = forms.Textarea(attrs={"cols": "40", "rows": "4"})
        self.helper.layout = Layout(
            Alert(
                "Changes made to these fields will apply to resource tracking output in the Spatial Support System",
                dismiss=False,
                css_class="alert-warning",
            ),
            Fieldset(
                "Vehicle/device details",
                Field("last_seen", css_class="form-control-plaintext"),
                Field("registration", css_class="form-control-plaintext"),
                "district",
                "symbol",
                "callsign",
                "rin_number",
                "fire_use",
            ),
            Fieldset("Crew details", "current_driver", "usual_driver", "usual_location"),
            Fieldset("Contractor details", "contractor_details"),
            Fieldset("Other details", "other_details", "internal_only", "hidden"),
            Div(self.save_button, self.cancel_button, css_class="col-sm-offset-4 col-md-offset-3 col-lg-offset-2"),
        )

    class Meta:
        model = Device
        fields = [
            "registration",
            "district",
            "symbol",
            "callsign",
            "rin_number",
            "fire_use",
            "current_driver",
            "usual_driver",
            "usual_location",
            "contractor_details",
            "other_details",
            "internal_only",
            "hidden",
        ]
        exclude = ["id"]
