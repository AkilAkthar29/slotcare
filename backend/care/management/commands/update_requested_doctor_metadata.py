from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from care.models import Doctor


VALUES = [
    ('Dr. Nila Vetrivel', 12, '4.7'),
    ('Dr. Adhavan Ilanchezhian', 18, '4.9'),
    ('Dr. Yazhini Thenmozhi', 8, '4.8'),
    ('Dr. Iniyan Arulnathan', 10, '4.6'),
    ('Dr. Mithra Pazhanivel', 15, '4.7'),
    ('Dr. Kavin Mutharasan', 16, '4.8'),
    ('Dr. Oviya Senthamaran', 7, '4.5'),
    ('Dr. Viyan Nallamuthu', 11, '4.6'),
]


class Command(BaseCommand):
    help = 'Update only the eight named fictional profiles using their existing experience and rating fields.'

    @transaction.atomic
    def handle(self, *args, **options):
        for name, experience, rating in VALUES:
            matches = Doctor.objects.select_for_update().filter(name=name)
            if matches.count() != 1:
                raise CommandError(f'Expected exactly one existing profile named {name}. No changes were made.')
            doctor = matches.get()
            if not doctor.bio.startswith('DEMO DATA:'):
                raise CommandError(f'{name} is not marked as a fictional profile. No changes were made.')
            doctor.experience = experience
            doctor.rating = rating
            doctor.bio = doctor.bio.replace(' Experience not provided (stored as 0).', '')
            doctor.full_clean()
            doctor.save(update_fields=['experience', 'rating', 'bio'])
            self.stdout.write(f'{name}: {experience} years, {rating}/5')
        self.stdout.write(self.style.SUCCESS('Updated eight existing profiles. Other records, accounts and bookings were not changed.'))
