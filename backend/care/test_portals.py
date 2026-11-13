from datetime import timedelta
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from .models import Appointment, Clinic, Doctor, Region, TimeSlot


class PortalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.patient = User.objects.create_user(username='patient-test', password='TestPassword123!')
        cls.doctor_user = User.objects.create_user(username='doctor-test', password='TestPassword123!')
        cls.other_user = User.objects.create_user(username='other-doctor-test', password='TestPassword123!')
        cls.velachery, _ = Region.objects.get_or_create(city='Chennai', area='Velachery')
        cls.mogappair, _ = Region.objects.get_or_create(city='Chennai', area='Mogappair')
        fields = dict(specialty='General Physician', clinic='Test Clinic', fee=500, initials='TD', color='green', experience=5, rating='4.5', bio='Test fixture')
        cls.doctor = Doctor.objects.create(id='portal-doctor', name='Test Physician', user=cls.doctor_user, region=cls.velachery, is_accepting=True, **fields)
        cls.other = Doctor.objects.create(id='other-doctor', name='Other Physician', user=cls.other_user, region=cls.mogappair, is_accepting=False, **fields)
        cls.clinic = Clinic.objects.create(doctor=cls.doctor, name='Test Clinic', region=cls.velachery, fee=500)
        cls.other_clinic = Clinic.objects.create(doctor=cls.other, name='Other Clinic', region=cls.mogappair, fee=700)
        cls.date = timezone.localdate()+timedelta(days=1)
        cls.slot = TimeSlot.objects.create(doctor=cls.doctor, clinic=cls.clinic, date=cls.date, time='09:00')
        cls.other_slot = TimeSlot.objects.create(doctor=cls.other, clinic=cls.other_clinic, date=cls.date, time='10:00')

    def setUp(self):
        self.client = APIClient(enforce_csrf_checks=True)
        self.csrf = self.client.get('/api/auth/session/').json()['csrfToken']

    def post(self, path, data):
        return self.client.post(path, data, format='json', HTTP_X_CSRFTOKEN=self.csrf)

    def login(self, username, portal):
        response = self.post('/api/auth/login/', {'username': username, 'password': 'TestPassword123!', 'portal': portal})
        if response.status_code == 200:
            self.csrf = response.json()['csrfToken']
        return response

    def test_distinct_logins_and_permissions(self):
        self.assertEqual(self.login('patient-test', 'doctor').status_code, 400)
        self.assertEqual(self.login('doctor-test', 'patient').status_code, 400)
        response = self.login('patient-test', 'patient')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['user']['role'], 'patient')
        self.assertEqual(self.client.get('/api/doctor-portal/profile/').status_code, 403)
        self.assertEqual(self.post('/api/doctor-portal/slots/', {'date': str(self.date), 'time': '11:00'}).status_code, 403)
        self.assertEqual(self.post('/api/auth/logout/', {}).status_code, 200)
        self.csrf = self.client.get('/api/auth/session/').json()['csrfToken']
        self.assertEqual(self.login('doctor-test', 'doctor').json()['user']['role'], 'doctor')
        self.assertEqual(self.client.get('/api/appointments/').status_code, 403)
        self.assertEqual(self.post('/api/appointments/', {'slotId': self.slot.pk}).status_code, 403)

    def test_region_filter_and_accurate_availability(self):
        regions = self.client.get('/api/regions/').json()
        self.assertTrue(any(r['area'] == 'Velachery' for r in regions))
        response = self.client.get('/api/doctors/?city=Chennai&area=Velachery').json()
        self.assertEqual([d['id'] for d in response], [self.doctor.pk])
        self.assertTrue(response[0]['available'])
        self.assertEqual(response[0]['region']['area'], 'Velachery')
        self.assertNotIn('user', response[0])
        response = self.client.get('/api/doctors/?area=Mogappair').json()
        self.assertFalse(response[0]['available'])
        self.assertEqual(self.client.get('/api/doctors/other-doctor/slots/').json(), [])
        self.assertEqual(len(self.client.get('/api/doctors/?available=true').json()), 1)
        self.assertEqual(self.client.get('/api/doctors/?city=Unknown').json(), [])
        self.assertEqual(self.client.get('/api/doctors/?region=invalid').status_code, 400)
        Appointment.objects.create(patient=self.patient, slot=self.slot)
        self.assertFalse(self.client.get('/api/doctors/portal-doctor/').json()['available'])
        Appointment.objects.update(status='cancelled')
        self.assertTrue(self.client.get('/api/doctors/portal-doctor/').json()['available'])
        TimeSlot.objects.filter(pk=self.slot.pk).update(is_active=False)
        self.assertFalse(self.client.get('/api/doctors/portal-doctor/').json()['available'])

    def test_doctor_manages_own_area_slots_and_patients(self):
        own = Appointment.objects.create(patient=self.patient, slot=self.slot)
        Appointment.objects.create(patient=self.patient, slot=self.other_slot)
        self.assertEqual(self.login('doctor-test', 'doctor').status_code, 200)
        response = self.client.get('/api/doctor-portal/appointments/').json()
        self.assertEqual([a['id'] for a in response], [str(own.pk)])
        self.assertEqual(response[0]['patientName'], 'patient-test')
        self.assertEqual([s['id'] for s in self.client.get('/api/doctor-portal/slots/').json()], [self.slot.pk])
        self.assertEqual(self.post('/api/doctor-portal/close-slot/', {'slotId': self.other_slot.pk}).status_code, 404)
        self.assertEqual(self.post('/api/doctor-portal/close-slot/', {'slotId': self.slot.pk}).status_code, 400)
        self.slot.refresh_from_db()
        self.assertTrue(self.slot.is_active)
        response = self.post('/api/doctor-portal/clinics/', {'clinicId': self.clinic.pk, 'regionId': self.mogappair.pk})
        self.post('/api/doctor-portal/profile/', {'acceptingAppointments': False, 'user': self.other_user.pk})
        self.assertEqual(response.status_code, 200)
        self.doctor.refresh_from_db()
        self.clinic.refresh_from_db()
        self.assertEqual(self.clinic.region_id, self.mogappair.pk)
        self.assertEqual(self.doctor.user_id, self.doctor_user.pk)
        self.assertFalse(self.doctor.is_accepting)
        own.refresh_from_db()
        self.assertEqual(own.status, 'confirmed')
        self.assertFalse(self.client.get('/api/doctors/portal-doctor/').json()['available'])

    def test_slot_creation_validation_close_and_reopen(self):
        self.login('doctor-test', 'doctor')
        body = {'date': str(self.date), 'time': '11:30', 'clinicId': self.clinic.pk}
        response = self.post('/api/doctor-portal/slots/', body)
        self.assertEqual(response.status_code, 201)
        slot_id = response.json()['id']
        self.assertEqual(self.post('/api/doctor-portal/slots/', body).status_code, 409)
        self.assertEqual(self.post('/api/doctor-portal/slots/', {**body, 'time': '11:15'}).status_code, 400)
        self.assertEqual(self.post('/api/doctor-portal/slots/', {**body, 'date': str(timezone.localdate()-timedelta(days=1))}).status_code, 400)
        self.assertEqual(self.post('/api/doctor-portal/close-slot/', {'slotId': slot_id}).status_code, 200)
        self.assertFalse(TimeSlot.objects.get(pk=slot_id).is_active)
        self.assertEqual(self.post('/api/doctor-portal/slots/', body).status_code, 201)
        self.assertTrue(TimeSlot.objects.get(pk=slot_id).is_active)

    def test_unavailable_doctor_blocks_new_bookings_and_rescheduling(self):
        appointment = Appointment.objects.create(patient=self.patient, slot=self.slot)
        target = TimeSlot.objects.create(doctor=self.doctor, clinic=self.clinic, date=self.date, time='12:00')
        Doctor.objects.filter(pk=self.doctor.pk).update(is_accepting=False)
        self.login('patient-test', 'patient')
        self.assertEqual(self.post('/api/appointments/', {'slotId': target.pk}).status_code, 400)
        self.assertEqual(self.post(f'/api/appointments/{appointment.pk}/reschedule/', {'slotId': target.pk}).status_code, 400)
        appointment.refresh_from_db()
        self.assertEqual(appointment.slot_id, self.slot.pk)
        self.assertEqual(appointment.status, 'confirmed')
        self.assertEqual(self.post(f'/api/appointments/{appointment.pk}/cancel/', {}).status_code, 200)
