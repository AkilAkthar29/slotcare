from datetime import timedelta
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from .models import Appointment, Clinic, Doctor, TimeSlot


class BookingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.jamie = get_user_model().objects.create_user(username='jamie', password='SlotCareDemo123!')
        cls.alex = get_user_model().objects.create_user(username='alex', password='SlotCareDemo123!')
        for doctor_id, specialty in [('ananya', 'General Physician'), ('arjun', 'Cardiologist')]:
            doctor = Doctor.objects.create(id=doctor_id, name='Test Doctor', specialty=specialty, clinic='Test Clinic', fee=100, initials='TD', color='green', experience=1, rating='4.0', bio='Test fixture', is_accepting=True)
            clinic = Clinic.objects.create(doctor=doctor, name=doctor.clinic, fee=doctor.fee)
            for day in range(1, 8):
                for hour in [9, 10, 11]:
                    TimeSlot.objects.create(doctor=doctor, clinic=clinic, date=timezone.localdate()+timedelta(days=day), time=f'{hour}:00')

    def setUp(self):
        self.client = APIClient(enforce_csrf_checks=True)
        self.csrf = self.client.get('/api/auth/session/').json()['csrfToken']

    def login(self, username='jamie'):
        response = self.client.post('/api/auth/login/', {'username': username, 'password': 'SlotCareDemo123!'}, format='json', HTTP_X_CSRFTOKEN=self.csrf)
        self.assertEqual(response.status_code, 200)
        self.csrf = response.json()['csrfToken']

    def post(self, path, data):
        return self.client.post(path, data, format='json', HTTP_X_CSRFTOKEN=self.csrf)

    def slots(self):
        return list(TimeSlot.objects.filter(doctor_id='ananya', date__gt=timezone.localdate())[:3])

    def test_public_directory(self):
        response = self.client.get('/api/doctors/?specialty=Cardiologist')
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(len(self.client.get('/api/doctors/ananya/slots/').json()), 21)
        self.assertEqual(self.client.get('/api/doctors/ananya/slots/?date=invalid').status_code, 400)

    def test_authentication_and_csrf(self):
        self.assertEqual(self.client.get('/api/appointments/').status_code, 403)
        self.assertEqual(self.client.post('/api/auth/login/', {'username': 'jamie', 'password': 'SlotCareDemo123!'}, format='json').status_code, 403)
        self.assertEqual(self.post('/api/auth/login/', {'username': 'jamie', 'password': 'wrong'}).status_code, 400)
        self.login()
        self.assertEqual(self.client.get('/api/auth/session/').json()['user']['username'], 'jamie')
        slot = self.slots()[0]
        self.assertEqual(self.client.post('/api/appointments/', {'slotId': slot.pk}, format='json').status_code, 403)
        self.assertEqual(self.post('/api/auth/logout/', {}).status_code, 200)
        self.assertEqual(self.client.get('/api/appointments/').status_code, 403)

    def test_book_persist_reschedule_cancel_and_rebook(self):
        self.login()
        first, second, _ = self.slots()
        response = self.post('/api/appointments/', {'slotId': first.pk})
        self.assertEqual(response.status_code, 201)
        booking = response.json()
        self.assertEqual(Appointment.objects.get(pk=booking['id']).patient, self.jamie)
        self.assertEqual(len(self.client.get('/api/appointments/').json()), 1)
        availability = self.client.get('/api/doctors/ananya/slots/').json()
        self.assertTrue(next(s for s in availability if s['id'] == first.pk)['booked'])
        self.assertEqual(self.post('/api/appointments/', {'slotId': first.pk}).status_code, 409)
        response = self.post(f"/api/appointments/{booking['id']}/reschedule/", {'slotId': second.pk})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['slotId'], second.pk)
        self.assertFalse(Appointment.objects.filter(slot=first, status='confirmed').exists())
        self.assertEqual(self.post(f"/api/appointments/{booking['id']}/cancel/", {}).status_code, 200)
        self.assertFalse(Appointment.objects.filter(slot=second, status='confirmed').exists())
        self.assertEqual(self.post('/api/appointments/', {'slotId': second.pk}).status_code, 201)
        self.assertEqual(self.post(f"/api/appointments/{booking['id']}/reschedule/", {'slotId': first.pk}).status_code, 400)

    def test_patient_isolation_and_conflict_rollback(self):
        first, second, _ = self.slots()
        original = Appointment.objects.create(patient=self.jamie, slot=first)
        other = Appointment.objects.create(patient=self.alex, slot=second)
        self.login()
        self.assertEqual([b['id'] for b in self.client.get('/api/appointments/').json()], [str(original.pk)])
        for suffix, payload in [('', None), ('cancel/', {}), ('reschedule/', {'slotId': first.pk})]:
            path = f'/api/appointments/{other.pk}/' + suffix
            response = self.client.get(path) if payload is None else self.post(path, payload)
            self.assertEqual(response.status_code, 404)
        response = self.post(f'/api/appointments/{original.pk}/reschedule/', {'slotId': second.pk})
        self.assertEqual(response.status_code, 409)
        original.refresh_from_db()
        self.assertEqual(original.slot_id, first.pk)
        self.assertEqual(original.status, 'confirmed')
        # The database protects against duplicates even outside the API.
        with self.assertRaises(IntegrityError), transaction.atomic():
            Appointment.objects.create(patient=self.alex, slot=first)

    def test_invalid_slots_and_patient_assignment(self):
        self.login()
        self.assertEqual(self.post('/api/appointments/', {}).status_code, 400)
        self.assertEqual(self.post('/api/appointments/', {'slotId': 999999}).status_code, 404)
        past = TimeSlot.objects.create(doctor_id='ananya', clinic=Clinic.objects.get(doctor_id='ananya'), date=timezone.localdate()-timedelta(days=1), time='09:00')
        self.assertEqual(self.post('/api/appointments/', {'slotId': past.pk}).status_code, 400)
        first = self.slots()[0]
        response = self.post('/api/appointments/', {'slotId': first.pk, 'patient': self.alex.pk, 'status': 'cancelled'})
        self.assertEqual(response.status_code, 201)
        booking = Appointment.objects.get(pk=response.json()['id'])
        self.assertEqual(booking.patient, self.jamie)
        self.assertEqual(booking.status, 'confirmed')
        different = TimeSlot.objects.filter(doctor_id='arjun').first()
        self.assertEqual(self.post(f'/api/appointments/{booking.pk}/reschedule/', {'slotId': different.pk}).status_code, 400)
