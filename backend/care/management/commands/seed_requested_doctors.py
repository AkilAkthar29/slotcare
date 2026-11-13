from datetime import time, timedelta
from zoneinfo import ZoneInfo
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from care.models import Appointment, Clinic, Doctor, Region, TimeSlot


PROFILES = [
    ('nila-vetrivel', 'Dr. Nila Vetrivel', 'General Medicine', 'Blue Tamarind Clinic', 'Anna Nagar', 500),
    ('adhavan-ilanchezhian', 'Dr. Adhavan Ilanchezhian', 'Cardiology', 'Fernbank Heart Clinic', 'Adyar', 900),
    ('yazhini-thenmozhi', 'Dr. Yazhini Thenmozhi', 'Dermatology', 'Copperleaf Skin Clinic', 'Velachery', 700),
    ('iniyan-arulnathan', 'Dr. Iniyan Arulnathan', 'Pediatrics', 'Little Banyan Clinic', 'Mogappair', 600),
    ('mithra-pazhanivel', 'Dr. Mithra Pazhanivel', 'Orthopedics', 'Pebble Grove Ortho Clinic', 'T. Nagar', 800),
    ('kavin-mutharasan', 'Dr. Kavin Mutharasan', 'Neurology', 'Blue Kite Neuro Clinic', 'Tondiarpet', 900),
    ('oviya-senthamaran', 'Dr. Oviya Senthamaran', 'ENT', 'Silver Finch ENT Clinic', 'Perungudi', 650),
    ('viyan-nallamuthu', 'Dr. Viyan Nallamuthu', 'Ophthalmology', 'Clear Fern Eye Clinic', 'Mylapore', 750),
]
DEMO_LABEL = 'DEMO DATA: Fictional profile supplied for local SlotCare testing.'


class Command(BaseCommand):
    help = 'Seed the eight explicitly requested fictional profiles and tomorrow at 10:30/11:00 IST without overwriting existing records.'

    def add_arguments(self, parser):
        parser.add_argument('--experience', type=int, help='Required years of experience; use 0 only as an explicitly chosen placeholder.')
        parser.add_argument('--rating', help='Required rating (0-5 or N/A).')
        parser.add_argument('--dry-run', action='store_true', help='Validate everything and report changes, then roll back.')

    @transaction.atomic
    def handle(self, *args, **options):
        if options['experience'] is None or options['rating'] is None:
            raise CommandError('Missing required Doctor fields: experience and rating. Pass --experience YEARS --rating VALUE. No records were changed.')
        if not 0 <= options['experience'] <= 100:
            raise CommandError('Experience must be between 0 and 100.')
        rating = options['rating'].strip()
        try:
            valid_rating = rating == 'N/A' or 0 <= float(rating) <= 5
        except ValueError:
            valid_rating = False
        if not valid_rating or len(rating) > 4:
            raise CommandError('Rating must be 0-5 (up to four characters) or N/A.')
        tomorrow = timezone.localdate(timezone=ZoneInfo('Asia/Kolkata')) + timedelta(days=1)
        counts = {'doctors': 0, 'clinics': 0, 'slots': 0}
        for index, (key, name, specialty, clinic_name, area, fee) in enumerate(PROFILES):
            try:
                region = Region.objects.get(city__iexact='Chennai', area__iexact=area)
            except (Region.DoesNotExist, Region.MultipleObjectsReturned):
                raise CommandError(f'Expected exactly one existing Chennai neighbourhood: {area}. No changes were made.')
            doctor_id = f'requested-{key}'
            doctor = Doctor.objects.filter(pk=doctor_id).first()
            if doctor and (doctor.name != name or not doctor.bio.startswith(DEMO_LABEL)):
                raise CommandError(f'Doctor ID {doctor_id} is already in use by a different record. No changes were made.')
            if not doctor:
                if Doctor.objects.filter(name__iexact=name).exists():
                    raise CommandError(f'{name} already exists under another ID. Resolve the existing record instead of creating a duplicate.')
                words = name.removeprefix('Dr. ').split()
                doctor = Doctor(id=doctor_id, name=name, specialty=specialty, clinic=clinic_name, fee=fee, region=region,
                                initials=words[0][0]+words[-1][0], color=['green', 'blue', 'pink', 'purple', 'sand', 'peach'][index % 6],
                                experience=options['experience'], rating=rating, bio=DEMO_LABEL + (' Experience not provided (stored as 0).' if options['experience'] == 0 else ''), is_accepting=True)
                doctor.full_clean()
                doctor.save()
                counts['doctors'] += 1
            clinic, created = Clinic.objects.get_or_create(doctor=doctor, name=clinic_name, region=region, defaults={'fee': fee, 'address': ''})
            counts['clinics'] += int(created)
            for start in [time(10, 30), time(11)]:
                slot, created = TimeSlot.objects.get_or_create(doctor=doctor, date=tomorrow, time=start, defaults={'clinic': clinic, 'is_active': True})
                if slot.clinic_id != clinic.pk:
                    raise CommandError(f'{name} already has a slot at {start} at a different clinic. No changes were made.')
                counts['slots'] += int(created)
                if not slot.is_active or Appointment.objects.filter(slot=slot, status='confirmed').exists():
                    self.stdout.write(self.style.WARNING(f'{name} {start:%H:%M}: existing blocked/booked slot preserved.'))
        if options['dry_run']:
            transaction.set_rollback(True)
        prefix = 'DRY RUN (rolled back)' if options['dry_run'] else 'Created'
        self.stdout.write(self.style.SUCCESS(f'{prefix}: {counts}. Test date: {tomorrow} Asia/Kolkata; times: 10:30 AM and 11:00 AM.'))
        self.stdout.write('Listings are labelled DEMO DATA. Existing records/bookings remain unchanged. No login accounts or street addresses are invented.')
