from django.db import migrations


def add_regions(apps, schema_editor):
    Region = apps.get_model('care', 'Region')
    for area in ['Velachery', 'Mogappair']:
        Region.objects.get_or_create(city='Chennai', area=area)


class Migration(migrations.Migration):
    dependencies = [('care', '0002_doctor_is_accepting_doctor_user_timeslot_is_active_and_more')]
    operations = [migrations.RunPython(add_regions, migrations.RunPython.noop)]
