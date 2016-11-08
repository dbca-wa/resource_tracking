from django.contrib.admin import ModelAdmin, register
from .models import Incident, Employee, EmployeeShift

@register(Incident)
class IncidentAdmin(ModelAdmin):
    list_display = ("financial_year", "fire_number", "name", "incident_location")
    list_filter = ("financial_year", "fire_number", "name")
    search_fields = ("financial_year", "fire_number", "name", "incident_location")

@register(Employee)
class EmployeeAdmin(ModelAdmin):
    list_display = ("employee_id", "first_name", "surname", 
        "mobile_num", "agency", "cost_centre", "cost_centre_desc")
    list_filter = ("agency", "cost_centre", "cost_centre_desc")
    search_fields = ("employee_id", "first_name", "surname", "mobile_num")

@register(EmployeeShift)
class EmployeeShiftAdmin(ModelAdmin):
    list_display = ("incident", "employee", "shift_number", "shift_type", 
        "role_crew", "shift_start", "shift_end", "accommodation_req",
        "accommodation_details", "accommodation_time_to_travel")
    list_filter = ("incident", "shift_number", "accommodation_req")
    search_fields = ("incident", "employee", "role_crew", "accommodation_details")
