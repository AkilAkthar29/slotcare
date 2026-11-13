from datetime import timedelta
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from .models import Appointment, Clinic, Doctor, Region, TimeSlot


class ClinicPortalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username='publishing-doctor', password='TestPassword123!')
        cls.patient = get_user_model().objects.create_user(username='booking-patient', password='TestPassword123!')
        cls.other_user = get_user_model().objects.create_user(username='other-portal-doctor', password='TestPassword123!')
        cls.area = Region.objects.get(city='Chennai', area='Velachery')
        common = dict(specialty='General Physician', clinic='Legacy Clinic', fee=500, initials='TD', color='blue', experience=5, rating='4.5', bio='', is_accepting=True)
        cls.doctor = Doctor.objects.create(id='publishing-doctor', user=cls.user, name='Test Doctor', **common)
        cls.other = Doctor.objects.create(id='second-doctor', user=cls.other_user, name='Other Doctor', **common)
        cls.clinic = Clinic.objects.create(doctor=cls.doctor, name='Test Area Clinic', address='Test street address', region=cls.area, fee=700)
        cls.other_clinic = Clinic.objects.create(doctor=cls.other, name='Other Clinic', address='Other address', region=cls.area, fee=900)

    def authenticated(self, user):
        client = APIClient(enforce_csrf_checks=True)
        csrf = client.get('/api/auth/session/').json()['csrfToken']
        response = client.post('/api/auth/login/', {'username': user.username, 'password': 'TestPassword123!', 'portal': 'doctor' if hasattr(user, 'doctor_profile') else 'patient'}, format='json', HTTP_X_CSRFTOKEN=csrf)
        self.assertEqual(response.status_code, 200)
        client.credentials(HTTP_X_CSRFTOKEN=response.json()['csrfToken'])
        return client

    def test_publish_find_book_and_reschedule_in_area(self):
        doctor = self.authenticated(self.user)
        patient = self.authenticated(self.patient)
        date = str(timezone.localdate()+timedelta(days=2))
        ids = []
        for time in ['09:00', '10:00']:
            response = doctor.post('/api/doctor-portal/slots/', {'date': date, 'time': time, 'clinicId': self.clinic.pk}, format='json')
            self.assertEqual(response.status_code, 201)
            ids.append(response.json()['id'])
        directory = patient.get(f'/api/doctors/?region={self.area.pk}&q=Test&specialty=General%20Physician').json()
        result = next(d for d in directory if d['id'] == self.doctor.pk)
        self.assertEqual(result['nextAvailable']['id'], ids[0])
        response = patient.post('/api/appointments/', {'slotId': ids[0]}, format='json')
        self.assertEqual(response.status_code, 201)
        booking_id = response.json()['id']
        response = patient.post(f'/api/appointments/{booking_id}/reschedule/', {'slotId': ids[1]}, format='json')
        self.assertEqual(response.status_code, 200)
        availability = patient.get(f'/api/doctors/{self.doctor.pk}/slots/?clinic={self.clinic.pk}').json()
        self.assertFalse(next(s for s in availability if s['id'] == ids[0])['booked'])
        self.assertTrue(next(s for s in availability if s['id'] == ids[1])['booked'])
        appointments = doctor.get('/api/doctor-portal/appointments/').json()
        self.assertEqual(appointments[0]['patientName'], self.patient.username)

    def test_only_own_clinics_and_future_schedule(self):
        client = self.authenticated(self.user)
        body = {'date': str(timezone.localdate()+timedelta(days=60)), 'time': '10:00', 'clinicId': self.clinic.pk}
        self.assertEqual(client.post('/api/doctor-portal/slots/', body, format='json').status_code, 201)
        self.assertEqual(client.post('/api/doctor-portal/slots/', {**body, 'clinicId': self.other_clinic.pk}, format='json').status_code, 400)
        self.assertEqual(client.post('/api/doctor-portal/clinics/', {'clinicId': self.other_clinic.pk, 'fee': 1}, format='json').status_code, 404)
        self.assertEqual(client.get('/api/doctor-portal/clinics/').json()[0]['id'], self.clinic.pk)
        response = client.post('/api/doctor-portal/clinics/', {'name': 'Second Test Clinic', 'address': 'Second street address', 'regionId': self.area.pk, 'fee': 1100}, format='json')
        self.assertEqual(response.status_code, 201)
        # Same doctor/time cannot be published at a second site.
        self.assertEqual(client.post('/api/doctor-portal/slots/', {**body, 'clinicId': response.json()['id']}, format='json').status_code, 409)

    def test_complete_past_visits_with_ownership_and_state_checks(self):
        client = self.authenticated(self.user)
        patient = self.authenticated(self.patient)
        yesterday = timezone.localdate()-timedelta(days=1)
        slot = TimeSlot.objects.create(doctor=self.doctor, clinic=self.clinic, date=yesterday, time='09:00')
        booking = Appointment.objects.create(patient=self.patient, slot=slot, consultation_fee=700)
        other_slot = TimeSlot.objects.create(doctor=self.other, clinic=self.other_clinic, date=yesterday, time='09:00')
        other_booking = Appointment.objects.create(patient=self.patient, slot=other_slot)
        self.assertEqual(client.post('/api/doctor-portal/complete/', {'appointmentId': other_booking.pk}, format='json').status_code, 404)
        self.assertEqual(patient.post('/api/doctor-portal/complete/', {'appointmentId': booking.pk}, format='json').status_code, 403)
        result = client.post('/api/doctor-portal/complete/', {'appointmentId': booking.pk}, format='json')
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()['status'], 'completed')
        self.assertEqual(client.post('/api/doctor-portal/complete/', {'appointmentId': booking.pk}, format='json').status_code, 400)
        self.assertEqual(patient.post(f'/api/appointments/{booking.pk}/cancel/', {}, format='json').status_code, 400)
        future = TimeSlot.objects.create(doctor=self.doctor, clinic=self.clinic, date=timezone.localdate()+timedelta(days=1), time='09:00')
        future_booking = Appointment.objects.create(patient=self.patient, slot=future)
        self.assertEqual(client.post('/api/doctor-portal/complete/', {'appointmentId': future_booking.pk}, format='json').status_code, 400)
