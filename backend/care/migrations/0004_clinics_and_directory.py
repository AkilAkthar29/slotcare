import json
from pathlib import Path
import django.db.models.deletion
from django.db import migrations, models


def preserve_clinics_and_bookings(apps, schema_editor):
    Doctor = apps.get_model('care', 'Doctor')
    Clinic = apps.get_model('care', 'Clinic')
    TimeSlot = apps.get_model('care', 'TimeSlot')
    Appointment = apps.get_model('care', 'Appointment')
    Region = apps.get_model('care', 'Region')
    for doctor in Doctor.objects.all().iterator():
        clinic = Clinic.objects.create(doctor_id=doctor.pk, name=doctor.clinic or 'Primary clinic', region_id=doctor.region_id, fee=doctor.fee, address='')
        TimeSlot.objects.filter(doctor_id=doctor.pk).update(clinic_id=clinic.pk)
        Appointment.objects.filter(slot__doctor_id=doctor.pk).update(consultation_fee=doctor.fee)
    dataset = json.loads((Path(__file__).resolve().parents[1] / 'data' / 'chennai_neighbourhoods_v1.json').read_text(encoding='utf-8'))
    for row in dataset['regions']:
        Region.objects.get_or_create(city='Chennai', area=row['area'], defaults={'aliases': row['aliases']})


class Migration(migrations.Migration):
    dependencies = [('care', '0003_chennai_regions')]
    operations = [
        migrations.AddField(model_name='region', name='aliases', field=models.JSONField(blank=True, default=list)),
        migrations.CreateModel(name='Clinic', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('name', models.CharField(max_length=160)),
            ('address', models.TextField(blank=True, help_text='Full street address. Legacy records may need this filled in.')),
            ('fee', models.PositiveIntegerField()),
            ('is_active', models.BooleanField(default=True)),
            ('doctor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='clinics', to='care.doctor')),
            ('region', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='clinics', to='care.region')),
        ], options={'ordering': ['id'], 'constraints': [models.UniqueConstraint(fields=('doctor', 'name', 'region'), name='unique_doctor_clinic_region')]}),
        migrations.AddField(model_name='timeslot', name='clinic', field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='slots', to='care.clinic')),
        migrations.AddField(model_name='appointment', name='consultation_fee', field=models.PositiveIntegerField(blank=True, null=True)),
        migrations.RunPython(preserve_clinics_and_bookings, migrations.RunPython.noop),
        migrations.AlterField(model_name='timeslot', name='clinic', field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='slots', to='care.clinic')),
        migrations.RemoveConstraint(model_name='appointment', name='valid_appointment_status'),
        migrations.AlterField(model_name='appointment', name='status', field=models.CharField(choices=[('confirmed', 'Confirmed'), ('cancelled', 'Cancelled'), ('completed', 'Completed')], default='confirmed', max_length=12)),
        migrations.AddConstraint(model_name='appointment', constraint=models.CheckConstraint(condition=models.Q(status__in=['confirmed', 'cancelled', 'completed']), name='valid_appointment_status')),
    ]
