import json
from pathlib import Path
from django.db import migrations


def merge_aliases(apps, schema_editor):
    Region = apps.get_model('care', 'Region')
    dataset = json.loads((Path(__file__).resolve().parents[1] / 'data' / 'chennai_neighbourhoods_v1.json').read_text(encoding='utf-8'))
    for row in dataset['regions']:
        region = Region.objects.filter(city='Chennai', area=row['area']).first()
        if region:
            aliases = list(dict.fromkeys([*region.aliases, *row['aliases']]))
            if aliases != region.aliases:
                Region.objects.filter(pk=region.pk).update(aliases=aliases)


class Migration(migrations.Migration):
    dependencies = [('care', '0005_alter_doctor_clinic_alter_doctor_fee')]
    operations = [migrations.RunPython(merge_aliases, migrations.RunPython.noop)]
