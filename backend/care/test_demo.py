from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from .models import Appointment, Clinic, Doctor, Region, TimeSlot


class DemoSeedTests(TestCase):
    def test_optional_seed_is_repeatable_and_preserves_edits_and_bookings(self):
        real_user = get_user_model().objects.create_user(username='real-patient', password='ExistingPassword123!')
        call_command('seed_demo', include_past_visit=True, verbosity=0)
        counts = [model.objects.count() for model in [Doctor, Clinic, TimeSlot, Appointment]]
        slot = TimeSlot.objects.filter(date__gt='2000-01-01', is_active=True).last()
        slot.is_active = False
        slot.save()
        clinic = Clinic.objects.first()
        clinic.fee = 777
        clinic.save()
        call_command('seed_demo', include_past_visit=True, verbosity=0)
        self.assertEqual(counts, [model.objects.count() for model in [Doctor, Clinic, TimeSlot, Appointment]])
        slot.refresh_from_db()
        clinic.refresh_from_db()
        real_user.refresh_from_db()
        self.assertFalse(slot.is_active)
        self.assertEqual(clinic.fee, 777)
        self.assertTrue(real_user.check_password('ExistingPassword123!'))
        self.assertEqual(Region.objects.filter(city='Chennai').count(), 207)
