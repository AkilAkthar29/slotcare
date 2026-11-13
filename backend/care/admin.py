from django.contrib import admin
from .models import Appointment, Clinic, Doctor, Region, TimeSlot


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ['city', 'area']
    search_fields = ['city', 'area']


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ['name', 'specialty', 'user', 'is_accepting']
    list_filter = ['is_accepting']
    search_fields = ['name', 'specialty', 'clinics__name']
    exclude = ['clinic', 'fee', 'region']


@admin.register(TimeSlot)
class TimeSlotAdmin(admin.ModelAdmin):
    list_display = ['doctor', 'clinic', 'date', 'time', 'is_active']
    list_filter = ['date', 'doctor']


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ['id', 'patient', 'slot', 'status', 'created_at']
    list_filter = ['status']
    readonly_fields = ['created_at']


@admin.register(Clinic)
class ClinicAdmin(admin.ModelAdmin):
    list_display = ['name', 'doctor', 'region', 'fee', 'is_active']
    search_fields = ['name', 'address', 'doctor__name', 'region__area']
    list_filter = ['region', 'is_active']
