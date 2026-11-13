import re
from django.db import migrations


def remove_labels(apps, schema_editor):
    Doctor = apps.get_model('care', 'Doctor')
    Clinic = apps.get_model('care', 'Clinic')
    User = apps.get_model('auth', 'User')

    def clean(value):
        return re.sub(r' {2,}', ' ', re.sub(r'\bdemo\b\s*', '', value, flags=re.IGNORECASE)).strip()

    # Edit display fields only. IDs, credentials, appointments and clinic links stay intact.
    doctors = Doctor.objects.filter(pk__in=['demo-ananya', 'demo-rohan', 'demo-meera'])
    for doctor in doctors:
        Doctor.objects.filter(pk=doctor.pk).update(name=clean(doctor.name), clinic=clean(doctor.clinic), bio=clean(doctor.bio))
        for clinic in Clinic.objects.filter(doctor_id=doctor.pk):
            Clinic.objects.filter(pk=clinic.pk).update(name=clean(clinic.name), address=clean(clinic.address))
    User.objects.filter(username='slotcare_demo_patient', first_name='Demo').update(first_name='')


class Migration(migrations.Migration):
    dependencies = [('care', '0006_merge_neighbourhood_aliases')]
    operations = [migrations.RunPython(remove_labels, migrations.RunPython.noop)]
