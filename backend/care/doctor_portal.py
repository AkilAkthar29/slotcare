from datetime import timedelta
from django.db import IntegrityError, OperationalError, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from .models import Appointment, Clinic, TimeSlot
from .permissions import IsDoctor
from .serializers import ClinicInputSerializer, ClinicSerializer, DoctorAppointmentSerializer, DoctorSerializer, DoctorSettingsSerializer, DoctorSlotInputSerializer, SlotInputSerializer, SlotSerializer
from .views import available_doctors
from .scheduling import annotated_slots, future_slots, slot_has_ended


class DoctorPortalViewSet(viewsets.ViewSet):
    permission_classes = [IsDoctor]

    def doctor(self, request):
        return request.user.doctor_profile

    @action(detail=False, methods=['get', 'post'])
    def profile(self, request):
        doctor = self.doctor(request)
        if request.method == 'POST':
            serializer = DoctorSettingsSerializer(doctor, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
        return Response(DoctorSerializer(available_doctors().get(pk=doctor.pk)).data)

    @action(detail=False, methods=['get', 'post'])
    def slots(self, request):
        doctor = self.doctor(request)
        if request.method == 'POST':
            serializer = DoctorSlotInputSerializer(data=request.data, context={'doctor': doctor})
            serializer.is_valid(raise_exception=True)
            try:
                with transaction.atomic():
                    values = serializer.validated_data
                    slot, created = TimeSlot.objects.get_or_create(doctor=doctor, date=values['date'], time=values['time'], defaults={'clinic': values['clinic']})
                    if not created:
                        if slot.clinic_id != values['clinic'].pk:
                            return Response({'detail': 'You already have a slot at this time at another clinic.'}, status=409)
                        if slot.is_active:
                            return Response({'detail': 'This slot already exists.'}, status=409)
                        slot.is_active = True
                        slot.save(update_fields=['is_active'])
            except (IntegrityError, OperationalError):
                return Response({'detail': 'Slot is busy. Please refresh and try again.'}, status=409)
            return Response(SlotSerializer(annotated_slots(TimeSlot.objects.filter(pk=slot.pk)).get()).data, status=201)
        slots = future_slots(TimeSlot.objects.filter(doctor=doctor))
        return Response(SlotSerializer(annotated_slots(slots), many=True).data)

    @action(detail=False, methods=['post'], url_path='close-slot')
    def close_slot(self, request):
        serializer = SlotInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        slot = get_object_or_404(TimeSlot, pk=serializer.validated_data['slotId'], doctor=self.doctor(request))
        try:
            with transaction.atomic():
                # Acquire SQLite's write lock before testing for a confirmed booking.
                TimeSlot.objects.filter(pk=slot.pk).update(is_active=False)
                if Appointment.objects.filter(slot=slot, status='confirmed').exists():
                    raise ValidationError({'detail': 'Booked slots cannot be closed. Existing appointments must be honoured.'})
        except OperationalError:
            return Response({'detail': 'Slot is busy. Please refresh and try again.'}, status=409)
        return Response({'detail': 'Slot closed.'})

    @action(detail=False, methods=['get'])
    def appointments(self, request):
        appointments = Appointment.objects.filter(slot__doctor=self.doctor(request)).select_related('slot__clinic__region', 'slot__doctor', 'patient')
        return Response(DoctorAppointmentSerializer(appointments, many=True).data)

    @action(detail=False, methods=['get', 'post'])
    def clinics(self, request):
        doctor = self.doctor(request)
        if request.method == 'POST':
            clinic = None
            if 'clinicId' in request.data:
                try:
                    clinic_id = int(request.data['clinicId'])
                except (TypeError, ValueError):
                    raise ValidationError({'clinicId': 'Use a numeric clinic ID.'})
                clinic = get_object_or_404(Clinic, pk=clinic_id, doctor=doctor)
            serializer = ClinicInputSerializer(clinic, data=request.data, partial=clinic is not None)
            serializer.is_valid(raise_exception=True)
            try:
                with transaction.atomic():
                    saved = serializer.save(doctor=doctor)
            except IntegrityError:
                return Response({'detail': 'This clinic already exists in that area.'}, status=409)
            return Response(ClinicSerializer(saved).data, status=200 if clinic else 201)
        return Response(ClinicSerializer(doctor.clinics.select_related('region'), many=True).data)

    @action(detail=False, methods=['post'])
    def complete(self, request):
        from rest_framework import serializers
        class Input(serializers.Serializer):
            appointmentId = serializers.IntegerField(min_value=1)
        serializer = Input(data=request.data)
        serializer.is_valid(raise_exception=True)
        appointment = get_object_or_404(Appointment.objects.select_related('slot__clinic__region', 'slot__doctor', 'patient'), pk=serializer.validated_data['appointmentId'], slot__doctor=self.doctor(request))
        if not slot_has_ended(appointment.slot):
            raise ValidationError({'detail': 'A visit can be completed only after its 30-minute appointment has ended.'})
        try:
            with transaction.atomic():
                changed = Appointment.objects.filter(pk=appointment.pk, slot_id=appointment.slot_id, slot__doctor=self.doctor(request), status='confirmed').update(status='completed')
                if not changed:
                    raise ValidationError({'detail': 'Only confirmed visits can be completed.'})
        except OperationalError:
            return Response({'detail': 'Appointment is busy. Please refresh and try again.'}, status=409)
        appointment.refresh_from_db()
        return Response(DoctorAppointmentSerializer(appointment).data)
