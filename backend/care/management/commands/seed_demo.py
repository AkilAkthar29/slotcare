from datetime import time, timedelta
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from care.models import Appointment, Clinic, Doctor, Region, TimeSlot


class Command(BaseCommand):
    help = 'Optionally add namespaced fictional sample accounts, clinics and future slots. Never overwrite existing records.'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=7)
        parser.add_argument('--include-past-visit', action='store_true', help='Add one fictional past visit for demonstrating completion.')

    @transaction.atomic
    def handle(self, *args, **options):
        if not 1 <= options['days'] <= 30:
            raise CommandError('--days must be between 1 and 30.')
        User = get_user_model()
        password = 'SlotCareDemo123!'
        patient, created = User.objects.get_or_create(username='slotcare_demo_patient', defaults={'first_name': '', 'last_name': 'Patient'})
        if created:
            patient.set_password(password)
            patient.save()
        elif hasattr(patient, 'doctor_profile'):
            raise CommandError('The sample patient username is already a doctor account. No changes were made.')
        specs = [('ananya', 'Dr. Ananya Rao', 'General Physician'), ('rohan', 'Dr. Rohan Sen', 'Cardiology'), ('meera', 'Dr. Meera Das', 'Dermatology')]
        doctors = []
        for index, (key, name, specialty) in enumerate(specs, 1):
            username = f'slotcare_demo_doctor_{index}'
            user, created = User.objects.get_or_create(username=username)
            doctor = Doctor.objects.filter(pk=f'demo-{key}').first()
            if not created and (not doctor or doctor.user_id != user.pk):
                raise CommandError(f'{username} is already in use by another account. No changes were made.')
            if created:
                user.set_password(password)
                user.save()
            if doctor and doctor.user_id != user.pk:
                raise CommandError('A sample doctor ID is already in use. No changes were made.')
            if not doctor:
                doctor = Doctor.objects.create(id=f'demo-{key}', user=user, name=name, specialty=specialty, clinic='Clinic', fee=600, initials='DR', color=['green', 'blue', 'peach'][index-1], experience=8, rating='4.8', bio='Fictional doctor for the SlotCare interview sample.', is_accepting=True)
            doctors.append(doctor)
        places = [(0, 'Velachery', 'South Care', 600, 9), (0, 'Mogappair', 'West Care', 850, 14), (1, 'Nungambakkam', 'Heart Care', 1100, 10), (2, 'Adyar', 'Skin Care', 900, 11)]
        clinics = []
        created_slots = 0
        for doctor_index, area, name, fee, hour in places:
            region = Region.objects.get(city='Chennai', area=area)
            clinic, _ = Clinic.objects.get_or_create(doctor=doctors[doctor_index], name=name, region=region, defaults={'address': f'Fictional address, 10 Sample Street, {area}, Chennai. Not a real clinic.', 'fee': fee})
            clinics.append(clinic)
            for day in range(1, options['days']+1):
                for minute in [0, 30]:
                    _, added = TimeSlot.objects.get_or_create(doctor=doctors[doctor_index], date=timezone.localdate()+timedelta(days=day), time=time(hour, minute), defaults={'clinic': clinic})
                    created_slots += int(added)
        if options['include_past_visit']:
            slot, _ = TimeSlot.objects.get_or_create(doctor=doctors[0], date=timezone.localdate()-timedelta(days=1), time=time(11), defaults={'clinic': clinics[0]})
            Appointment.objects.get_or_create(slot=slot, patient=patient, defaults={'consultation_fee': clinics[0].fee})
        self.stdout.write(self.style.SUCCESS(f'Sample data ready: added {created_slots} future slots. Existing accounts, passwords, clinic edits, blocked slots and bookings preserved.'))
        self.stdout.write('Patient: slotcare_demo_patient | Doctors: slotcare_demo_doctor_1 / _2 / _3 | Initial password: SlotCareDemo123!')
