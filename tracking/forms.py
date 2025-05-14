from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div, Fieldset, Layout, Submit
from django import forms

from tracking.models import Device


class DeviceForm(forms.ModelForm):
    save_button = Submit("save", "Save", css_class="btn-lg")
    cancel_button = Submit("cancel", "Cancel", css_class="btn-secondary")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # crispy_forms layout
        self.helper = FormHelper()
        self.helper.form_class = "form-horizontal"
        self.helper.label_class = "col-xs-12 col-sm-4 col-md-2"
        self.helper.field_class = "col-xs-12 col-sm-8 col-md-10"
        self.helper.help_text_inline = True
        self.fields["other_details"].widget = forms.Textarea(attrs={"cols": "40", "rows": "4"})
        self.helper.layout = Layout(
            Fieldset("Vehicle/device details", "district", "symbol", "callsign", "rin_number", "fire_use"),
            Fieldset("Crew details", "current_driver", "usual_driver", "usual_location"),
            Fieldset("Contractor details", "contractor_details"),
            Fieldset("Other details", "other_details", "internal_only", "hidden"),
            Div(self.save_button, self.cancel_button, css_class="col-sm-offset-4 col-md-offset-3 col-lg-offset-2"),
        )

    class Meta:
        model = Device
        fields = [
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
