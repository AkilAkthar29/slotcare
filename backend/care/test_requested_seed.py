from datetime import time, timedelta
from io import StringIO
from zoneinfo import ZoneInfo
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from .models import Appointment, Clinic, Doctor, Region, TimeSlot


class RequestedProfileSeedTests(TestCase):
    def seed(self, **kwargs):
        call_command('seed_requested_doctors', experience=0, rating='N/A', stdout=StringIO(), **kwargs)

    def test_repeatable_area_search_slots_and_preservation(self):
        region_count = Region.objects.count()
        self.seed()
        self.assertEqual((Doctor.objects.count(), Clinic.objects.count(), TimeSlot.objects.count()), (8, 8, 16))
        self.assertEqual(Region.objects.count(), region_count)
        tomorrow = timezone.localdate(timezone=ZoneInfo('Asia/Kolkata'))+timedelta(days=1)
        result = APIClient().get('/api/doctors/?city=Chennai&area=Velachery&specialty=Dermatology').json()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['name'], 'Dr. Yazhini Thenmozhi')
        self.assertTrue(result[0]['bio'].startswith('DEMO DATA:'))
        self.assertEqual(result[0]['nextAvailable']['clinic']['fee'], 700)
        slots = APIClient().get(f"/api/doctors/{result[0]['id']}/slots/?date={tomorrow}").json()
        self.assertEqual([s['time'] for s in slots], ['10:30 AM', '11:00 AM'])
        self.assertTrue(all(not s['booked'] for s in slots))
        user = get_user_model().objects.create_user(username='existing-patient', password='PreservePassword123!')
        slot = TimeSlot.objects.get(doctor_id=result[0]['id'], date=tomorrow, time=time(10, 30))
        appointment = Appointment.objects.create(patient=user, slot=slot, consultation_fee=700)
        blocked = TimeSlot.objects.get(doctor_id=result[0]['id'], date=tomorrow, time=time(11))
        blocked.is_active = False
        blocked.save()
        self.seed()
        self.assertEqual((Doctor.objects.count(), Clinic.objects.count(), TimeSlot.objects.count()), (8, 8, 16))
        appointment.refresh_from_db()
        blocked.refresh_from_db()
        self.assertEqual(appointment.slot_id, slot.pk)
        self.assertEqual(appointment.status, 'confirmed')
        self.assertFalse(blocked.is_active)

    def test_missing_metadata_and_dry_run_do_not_write(self):
        with self.assertRaises(CommandError):
            call_command('seed_requested_doctors', stdout=StringIO())
        self.assertEqual(Doctor.objects.count(), 0)
        self.seed(dry_run=True)
        self.assertEqual(Doctor.objects.count(), 0)

    def test_named_metadata_update_persists_and_is_scoped(self):
        from .management.commands.update_requested_doctor_metadata import VALUES
        self.seed()
        other = Doctor.objects.create(id='unlisted', name='Unlisted Doctor', specialty='General Medicine', initials='UD', color='green', experience=22, rating='4.2', bio='Unrelated profile')
        slot_ids = list(TimeSlot.objects.values_list('id', flat=True))
        for _ in range(2):
            call_command('update_requested_doctor_metadata', stdout=StringIO())
            api_rows = {row['name']: row for row in APIClient().get('/api/doctors/?city=Chennai').json()}
            for name, experience, rating in VALUES:
                self.assertEqual(api_rows[name]['experience'], experience)
                self.assertEqual(api_rows[name]['rating'], rating)
                self.assertNotIn('Experience not provided', api_rows[name]['bio'])
        other.refresh_from_db()
        self.assertEqual((other.experience, other.rating), (22, '4.2'))
        self.assertEqual(list(TimeSlot.objects.values_list('id', flat=True)), slot_ids)
