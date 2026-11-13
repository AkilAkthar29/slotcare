from django.conf import settings
from django.db import models


class Region(models.Model):
    city = models.CharField(max_length=80)
    area = models.CharField(max_length=80)
    aliases = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ['city', 'area']
        constraints = [models.UniqueConstraint(fields=['city', 'area'], name='unique_city_area')]

    def __str__(self):
        return f'{self.area}, {self.city}'

    def clean(self):
        from django.core.exceptions import ValidationError
        if not isinstance(self.aliases, list) or any(not isinstance(alias, str) for alias in self.aliases):
            raise ValidationError({'aliases': 'Use a JSON list of alternate neighbourhood names.'})


class Doctor(models.Model):
    id = models.SlugField(primary_key=True)
    name = models.CharField(max_length=120)
    specialty = models.CharField(max_length=80)
    clinic = models.CharField(max_length=160, blank=True, default='')
    fee = models.PositiveIntegerField(default=0)
    initials = models.CharField(max_length=4)
    color = models.CharField(max_length=20)
    experience = models.PositiveIntegerField()
    rating = models.CharField(max_length=4)
    bio = models.TextField()
    user = models.OneToOneField(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='doctor_profile')
    region = models.ForeignKey(Region, null=True, blank=True, on_delete=models.PROTECT, related_name='doctors')
    is_accepting = models.BooleanField(default=False, help_text='Accept new appointments when open slots exist.')

    def __str__(self):
        return self.name


class Clinic(models.Model):
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='clinics')
    name = models.CharField(max_length=160)
    address = models.TextField(blank=True, help_text='Full street address. Legacy records may need this filled in.')
    region = models.ForeignKey(Region, null=True, blank=True, on_delete=models.PROTECT, related_name='clinics')
    fee = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['id']
        constraints = [models.UniqueConstraint(fields=['doctor', 'name', 'region'], name='unique_doctor_clinic_region')]

    def __str__(self):
        return f'{self.name} ({self.doctor.name})'


class TimeSlot(models.Model):
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='slots')
    date = models.DateField()
    time = models.TimeField()
    is_active = models.BooleanField(default=True)
    clinic = models.ForeignKey(Clinic, on_delete=models.PROTECT, related_name='slots')

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.clinic_id and self.clinic.doctor_id != self.doctor_id:
            raise ValidationError({'clinic': 'The slot must belong to a clinic of this doctor.'})

    class Meta:
        ordering = ['date', 'time']
        constraints = [models.UniqueConstraint(fields=['doctor', 'date', 'time'], name='unique_doctor_date_time')]


class Appointment(models.Model):
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='appointments')
    slot = models.ForeignKey(TimeSlot, on_delete=models.PROTECT, related_name='appointments')
    status = models.CharField(max_length=12, choices=[('confirmed', 'Confirmed'), ('cancelled', 'Cancelled'), ('completed', 'Completed')], default='confirmed')
    created_at = models.DateTimeField(auto_now_add=True)
    consultation_fee = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ['slot__date', 'slot__time', 'id']
        constraints = [
            models.UniqueConstraint(fields=['slot'], condition=models.Q(status='confirmed'), name='one_active_appointment_per_slot'),
            models.CheckConstraint(condition=models.Q(status__in=['confirmed', 'cancelled', 'completed']), name='valid_appointment_status'),
        ]
