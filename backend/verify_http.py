"""Live integration check through Next.js; removes only its UUID-namespaced fixtures."""
import http.cookiejar
import json
import os
import secrets
import urllib.error
import urllib.request
import uuid
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from care.models import Appointment, Clinic, Doctor, Region, TimeSlot


class Session:
    def __init__(self):
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        self.csrf = ''

    def request(self, path, body=None, expected=200):
        req = urllib.request.Request('http://127.0.0.1:3000/api/'+path, data=json.dumps(body).encode() if body is not None else None, headers={'Content-Type': 'application/json', 'Origin': 'http://127.0.0.1:3000', 'X-CSRFToken': self.csrf})
        try:
            response = self.opener.open(req, timeout=20)
        except urllib.error.HTTPError as error:
            response = error
        payload = json.loads(response.read())
        assert response.code == expected, (path, response.code, payload)
        return payload

    def login(self, username, password, portal):
        self.csrf = self.request('auth/session/')['csrfToken']
        self.csrf = self.request('auth/login/', {'username': username, 'password': password, 'portal': portal})['csrfToken']


def main():
    key = 'verify-'+uuid.uuid4().hex[:16]
    password = secrets.token_urlsafe(24)
    users = []
    sessions = []
    doctor = None
    try:
        User = get_user_model()
        for suffix in ['doctor', 'patient']:
            users.append(User.objects.create_user(username=key+'-'+suffix, password=password))
        region = Region.objects.get(city='Chennai', area='Velachery')
        doctor = Doctor.objects.create(id=key, user=users[0], name='HTTP Verification Doctor '+key, specialty='Verification', initials='VT', color='green', experience=1, rating='4.0', bio='Temporary verification fixture', is_accepting=True)
        clinic = Clinic.objects.create(doctor=doctor, region=region, name='HTTP Verification Clinic', address='Temporary verification address', fee=650)
        doc, patient = Session(), Session()
        doc.login(users[0].username, password, 'doctor')
        sessions.append(doc)
        patient.login(users[1].username, password, 'patient')
        sessions.append(patient)
        ids = []
        for time in ['09:00', '10:00']:
            ids.append(doc.request('doctor-portal/slots/', {'clinicId': clinic.pk, 'date': str(timezone.localdate()+timedelta(days=1)), 'time': time}, 201)['id'])
        result = patient.request(f'doctors/?region={region.pk}&q={key}')
        assert len(result) == 1 and result[0]['nextAvailable']['id'] == ids[0]
        booking = patient.request('appointments/', {'slotId': ids[0]}, 201)
        assert booking['clinic']['id'] == clinic.pk and booking['fee'] == 650
        patient.request('appointments/', {'slotId': ids[0]}, 409)
        moved = patient.request(f"appointments/{booking['id']}/reschedule/", {'slotId': ids[1]})
        assert moved['slotId'] == ids[1]
        slots = patient.request(f'doctors/{doctor.pk}/slots/?clinic={clinic.pk}')
        assert not next(s for s in slots if s['id'] == ids[0])['booked']
        assert next(s for s in slots if s['id'] == ids[1])['booked']
        assert len(doc.request('doctor-portal/appointments/')) == 1
        patient.request(f"appointments/{booking['id']}/cancel/", {})
        doc.request('doctor-portal/close-slot/', {'slotId': ids[0]})
        past_slot = TimeSlot.objects.create(doctor=doctor, clinic=clinic, date=timezone.localdate()-timedelta(days=1), time='08:00')
        past_visit = Appointment.objects.create(patient=users[1], slot=past_slot, consultation_fee=clinic.fee)
        completed = doc.request('doctor-portal/complete/', {'appointmentId': past_visit.pk})
        assert completed['status'] == 'completed'
        patient.request(f'appointments/{past_visit.pk}/cancel/', {}, 400)
        print('PASS: live doctor publish -> Chennai area search -> patient booking -> duplicate conflict -> reschedule releases original -> doctor sees visit -> cancellation -> block slot -> complete past visit.')
    finally:
        for session in sessions:
            try:
                session.request('auth/logout/', {})
            except Exception:
                pass
        with transaction.atomic():
            if doctor:
                Appointment.objects.filter(slot__doctor=doctor).delete()
                TimeSlot.objects.filter(doctor=doctor).delete()
                Clinic.objects.filter(doctor=doctor).delete()
                doctor.delete()
            get_user_model().objects.filter(pk__in=[user.pk for user in users]).delete()


if __name__ == '__main__':
    main()
