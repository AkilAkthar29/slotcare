from datetime import timedelta
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from .models import Appointment, Clinic, Doctor, Region, TimeSlot


class ChennaiDirectoryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.patient = get_user_model().objects.create_user(username='directory-patient', password='TestPassword123!')
        cls.velachery = Region.objects.get(city='Chennai', area='Velachery')
        cls.mogappair = Region.objects.get(city='Chennai', area='Mogappair')
        cls.doctor = Doctor.objects.create(id='directory-doctor', name='Test Physician', specialty='Cardiology', clinic='Legacy', fee=100, initials='TP', color='green', experience=5, rating='4.5', bio='', is_accepting=True)
        cls.clinic_a = Clinic.objects.create(doctor=cls.doctor, name='South Clinic', address='12 Test Street, Velachery', region=cls.velachery, fee=800)
        cls.clinic_b = Clinic.objects.create(doctor=cls.doctor, name='West Clinic', address='34 Test Road, Mogappair', region=cls.mogappair, fee=1200)
        cls.date = timezone.localdate()+timedelta(days=1)
        cls.first = TimeSlot.objects.create(doctor=cls.doctor, clinic=cls.clinic_a, date=cls.date, time='10:00')
        cls.second = TimeSlot.objects.create(doctor=cls.doctor, clinic=cls.clinic_b, date=cls.date, time='09:00')

    def setUp(self):
        self.client = APIClient()

    def test_neighbourhoods_include_empty_areas_and_aliases(self):
        response = self.client.get('/api/regions/?city=Chennai').json()
        self.assertGreaterEqual(len(response), 200)
        for area in ['Nungambakkam', 'Kilpauk', 'Royapettah', 'Anna Nagar', 'Velachery', 'Mogappair', 'Uthandi']:
            self.assertTrue(any(r['area'] == area for r in response), area)
        self.assertEqual(self.client.get('/api/regions/?search=Thyagaraya').json()[0]['area'], 'T. Nagar')
        self.assertEqual(self.client.get('/api/doctors/?area=Nungambakkam').json(), [])

    def test_next_slot_and_fee_use_the_selected_clinic_area(self):
        all_result = self.client.get('/api/doctors/?city=Chennai').json()[0]
        self.assertEqual(all_result['nextAvailable']['clinic']['id'], self.clinic_b.pk)
        result = self.client.get(f'/api/doctors/?region={self.velachery.pk}&specialty=Cardiology&q=South').json()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['nextAvailable']['id'], self.first.pk)
        self.assertEqual(result[0]['nextAvailable']['clinic']['fee'], 800)
        self.assertEqual([c['id'] for c in result[0]['clinics']], [self.clinic_a.pk])
        slots = self.client.get(f'/api/doctors/{self.doctor.pk}/slots/?clinic={self.clinic_a.pk}').json()
        self.assertEqual([s['id'] for s in slots], [self.first.pk])
        self.assertEqual(self.client.get('/api/doctors/?specialty=Dermatology').json(), [])

    def test_area_booking_reschedule_conflict_release_and_snapshot(self):
        self.client.force_authenticate(self.patient)
        response = self.client.post('/api/appointments/', {'slotId': self.first.pk})
        self.assertEqual(response.status_code, 201)
        booking = response.json()
        self.assertEqual(booking['clinic']['address'], self.clinic_a.address)
        self.assertEqual(booking['fee'], 800)
        Clinic.objects.filter(pk=self.clinic_a.pk).update(fee=950)
        self.assertEqual(self.client.get(f"/api/appointments/{booking['id']}/").json()['fee'], 800)
        blocker = Appointment.objects.create(patient=self.patient, slot=self.second)
        self.assertEqual(self.client.post(f"/api/appointments/{booking['id']}/reschedule/", {'slotId': self.second.pk}).status_code, 409)
        self.assertEqual(Appointment.objects.get(pk=booking['id']).slot_id, self.first.pk)
        self.assertEqual(Appointment.objects.get(pk=booking['id']).consultation_fee, 800)
        self.client.post(f'/api/appointments/{blocker.pk}/cancel/', {})
        moved = self.client.post(f"/api/appointments/{booking['id']}/reschedule/", {'slotId': self.second.pk})
        self.assertEqual(moved.status_code, 200)
        self.assertEqual(moved.json()['clinic']['id'], self.clinic_b.pk)
        self.assertEqual(moved.json()['fee'], 1200)
        self.assertTrue(self.client.get(f'/api/doctors/?region={self.velachery.pk}').json()[0]['available'])
        self.assertFalse(self.client.get(f'/api/doctors/?region={self.mogappair.pk}').json()[0]['available'])
        with self.assertRaises(IntegrityError), transaction.atomic():
            Appointment.objects.create(patient=self.patient, slot=self.second)
        # A doctor cannot publish the same time at a second clinic.
        with self.assertRaises(IntegrityError), transaction.atomic():
            TimeSlot.objects.create(doctor=self.doctor, clinic=self.clinic_a, date=self.date, time='09:00')
