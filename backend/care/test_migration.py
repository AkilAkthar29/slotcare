from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class ClinicMigrationTests(TransactionTestCase):
    def test_existing_account_booking_and_clinic_are_preserved(self):
        old = [('care', '0003_chennai_regions')]
        new = [('care', '0007_remove_visible_demo_labels')]
        executor = MigrationExecutor(connection)
        executor.migrate(old)
        apps = executor.loader.project_state(old).apps
        User = apps.get_model('auth', 'User')
        Doctor = apps.get_model('care', 'Doctor')
        TimeSlot = apps.get_model('care', 'TimeSlot')
        Appointment = apps.get_model('care', 'Appointment')
        Region = apps.get_model('care', 'Region')
        try:
            user = User.objects.create(username='migration-patient', password='preserved-password-hash')
            region = Region.objects.get(city='Chennai', area='Velachery')
            doctor = Doctor.objects.create(id='preserve-doctor', name='Existing Doctor', specialty='General Physician', clinic='Existing Clinic', fee=750, initials='ED', color='green', experience=10, rating='4.5', bio='', region=region, is_accepting=True)
            slot = TimeSlot.objects.create(doctor=doctor, date='2030-01-01', time='09:00')
            booking = Appointment.objects.create(patient=user, slot=slot)
            executor = MigrationExecutor(connection)
            executor.migrate(new)
            migrated = executor.loader.project_state(new).apps
            record = migrated.get_model('care', 'Appointment').objects.get(pk=booking.pk)
            self.assertEqual(record.patient_id, user.pk)
            self.assertEqual(record.slot_id, slot.pk)
            self.assertEqual(record.status, 'confirmed')
            self.assertEqual(record.consultation_fee, 750)
            clinic = migrated.get_model('care', 'TimeSlot').objects.get(pk=slot.pk).clinic
            self.assertEqual(clinic.name, 'Existing Clinic')
            self.assertEqual(clinic.region_id, region.pk)
            self.assertEqual(clinic.fee, 750)
            self.assertEqual(clinic.address, '')
            self.assertEqual(migrated.get_model('auth', 'User').objects.get(pk=user.pk).password, 'preserved-password-hash')
        finally:
            MigrationExecutor(connection).migrate(new)
