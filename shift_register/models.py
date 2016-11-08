from __future__ import unicode_literals

from django.db import models

class Incident(models.Model):
    financial_year = models.CharField(max_length=10, verbose_name="Financial Year")
    fire_number = models.CharField(max_length=10, null=True, blank=True,  verbose_name="P&W Fire Number")
    name = models.CharField(max_length=64, verbose_name="Incident Name")
    incident_location = models.CharField(max_length=64, verbose_name="Location",
        help_text="e.g. '10 km NE of Bridgetown' or 'Within the locality of Mitchell Plateau'")
    icc_location = models.TextField(null=True, blank=True, verbose_name="ICC Location",
        help_text="Address or location of Incident Control Centre")

    def __str__(self):
        if self.fire_number:
            return '{} - {} - {}'.format(self.financial_year, self.fire_number, self.name)
        else:
            return '{} - {}'.format(self.financial_year, self.name)

class Employee(models.Model):
    employee_id = models.CharField(max_length=10)
    first_name = models.CharField(max_length=64)
    surname = models.CharField(max_length=64)
    gender = models.CharField(max_length=1)
    date_of_birth = models.DateField()
    agency = models.CharField(max_length=4)
    occupational_position = models.CharField(max_length=128,
        verbose_name="Primary Occupational Position")
    location_desc = models.CharField(max_length=128,
        verbose_name="Primary Occupational Location")
    cost_centre = models.CharField(max_length=10, null=True, blank=True)
    cost_centre_desc = models.CharField(max_length=128, null=True, blank=True)
    mobile_num = models.CharField(max_length=10, null=True, blank=True,
        verbose_name="Mobile Phone No.")

    @property
    def full_name(self):
        return self.first_name + ' ' + self.surname

    def __str__(self):
        return '{}, {} ({})'.format(self.surname, self.first_name, self.employee_id)

class EmployeeShift(models.Model):
    incident = models.ForeignKey(Incident)
    employee = models.ForeignKey(Employee)
    shift_number = models.IntegerField()
    shift_type = models.CharField(max_length=1)
    accommodation_req = models.CharField(max_length=1,
        verbose_name="Accommodation Required?")
    role_crew = models.CharField(max_length=128,
        verbose_name="Role at Incident or Crew Name")
    shift_start = models.DateTimeField()
    shift_end = models.DateTimeField(null=True, blank=True)
    accommodation_details = models.TextField(null=True, blank=True)
    accommodation_time_to_travel = models.IntegerField(null=True, blank=True)
    comments = models.TextField(null=True, blank=True)

    def __str__(self):
        return '{} - Shift {} ({}) at {}'.format(
            self.employee, self.shift_number, self.shift_type, self.incident)
