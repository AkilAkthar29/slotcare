from datetime import datetime, timedelta
from django.contrib.auth import authenticate, login, logout
from django.db import IntegrityError, OperationalError, transaction
from django.db.models import Exists, F, OuterRef, Prefetch, Q, TextField
from django.db.models.functions import Cast
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from .models import Appointment, Clinic, Doctor, Region, TimeSlot
from .scheduling import annotated_slots, future_slots, open_slots, slot_is_future
from .permissions import IsDoctor, IsPatient
from .serializers import AppointmentSerializer, DoctorSerializer, LoginSerializer, RegionSerializer, SlotInputSerializer, SlotSerializer


def patient_data(user):
    return {'username': user.username, 'name': user.get_full_name() or user.username, 'role': 'doctor' if hasattr(user, 'doctor_profile') else 'patient'}


class LoginThrottle(AnonRateThrottle):
    scope = 'login'


@method_decorator(csrf_protect, name='dispatch')
class AuthViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]

    @action(detail=False, methods=['get'], url_path='session')
    def session(self, request):
        response = Response({'user': patient_data(request.user) if request.user.is_authenticated else None, 'csrfToken': get_token(request)})
        response['Cache-Control'] = 'no-store'
        return response

    @action(detail=False, methods=['post'], throttle_classes=[LoginThrottle], url_path='login')
    def login(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        credentials = dict(serializer.validated_data)
        portal = credentials.pop('portal')
        user = authenticate(request, **credentials)
        if user is None:
            raise ValidationError({'detail': 'Incorrect username or password.'})
        if patient_data(user)['role'] != portal:
            raise ValidationError({'detail': f'This account cannot sign in to the {portal} portal. Use the correct portal.'})
        login(request, user)
        return Response({'user': patient_data(user), 'csrfToken': get_token(request)})

    @action(detail=False, methods=['post'], url_path='logout')
    def logout(self, request):
        logout(request)
        return Response({'user': None, 'csrfToken': get_token(request)})


def available_doctors():
    return Doctor.objects.select_related('region').prefetch_related(
        Prefetch('clinics', queryset=Clinic.objects.select_related('region')),
        Prefetch('slots', queryset=open_slots().order_by('date', 'time'), to_attr='directory_slots'),
    ).order_by('id')


def scoped_clinics(params):
    qs = Clinic.objects.filter(is_active=True)
    for param, field in [('city', 'region__city__iexact'), ('area', 'region__area__iexact')]:
        if params.get(param):
            qs = qs.filter(**{field: params[param]})
    if params.get('region'):
        if not params['region'].isdigit():
            raise ValidationError({'region': 'Use a numeric neighbourhood ID.'})
        qs = qs.filter(region_id=int(params['region']))
    return qs


class RegionViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    serializer_class = RegionSerializer
    queryset = Region.objects.all()

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get('city'):
            qs = qs.filter(city__iexact=self.request.query_params['city'])
        if self.request.query_params.get('search'):
            qs = qs.annotate(alias_text=Cast('aliases', TextField())).filter(Q(area__icontains=self.request.query_params['search']) | Q(alias_text__icontains=self.request.query_params['search']))
        return qs


class DoctorViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    serializer_class = DoctorSerializer
    queryset = Doctor.objects.all()

    def get_queryset(self):
        params = self.request.query_params
        clinics = scoped_clinics(params)
        qs = available_doctors()
        # Detail reads remain valid for a doctor's appointments even without an active clinic.
        if self.action == 'list':
            qs = qs.filter(Exists(clinics.filter(doctor_id=OuterRef('pk'))))
        if params.get('specialty'):
            qs = qs.filter(specialty__iexact=params['specialty'])
        if params.get('q'):
            term = params['q'].strip()
            matching_clinics = clinics.filter(Q(name__icontains=term) | Q(address__icontains=term) | Q(region__area__icontains=term))
            qs = qs.annotate(clinic_matches=Exists(matching_clinics.filter(doctor_id=OuterRef('pk')))).filter(Q(name__icontains=term) | Q(specialty__icontains=term) | Q(clinic_matches=True))
        if 'available' in params:
            if params['available'] not in ['true', 'false']:
                raise ValidationError({'available': 'Use true or false.'})
            free = open_slots(TimeSlot.objects.filter(clinic_id__in=clinics.values('pk'), doctor_id=OuterRef('pk')))
            qs = qs.annotate(has_open_slot=Exists(free)).filter(has_open_slot=params['available'] == 'true')
        return qs

    @action(detail=True, methods=['get'])
    def slots(self, request, pk=None):
        doctor = self.get_object()
        qs = future_slots(TimeSlot.objects.filter(doctor=doctor, is_active=True, clinic__is_active=True))
        qs = qs.filter(clinic_id__in=scoped_clinics(request.query_params).values('pk'))
        if request.query_params.get('clinic'):
            if not request.query_params['clinic'].isdigit():
                raise ValidationError({'clinic': 'Use a numeric clinic ID.'})
            qs = qs.filter(clinic_id=int(request.query_params['clinic']))
        if not doctor.is_accepting:
            qs = qs.none()
        if request.query_params.get('date'):
            try:
                date = datetime.strptime(request.query_params['date'], '%Y-%m-%d').date()
            except ValueError:
                raise ValidationError({'date': 'Use YYYY-MM-DD.'})
            qs = qs.filter(date=date)
        return Response(SlotSerializer(annotated_slots(qs), many=True).data)


class AppointmentViewSet(viewsets.GenericViewSet):
    permission_classes = [IsPatient]
    serializer_class = AppointmentSerializer

    def get_queryset(self):
        return Appointment.objects.filter(patient=self.request.user).select_related('slot__doctor', 'slot__clinic__region')

    def list(self, request):
        return Response(self.get_serializer(self.get_queryset(), many=True).data)

    def retrieve(self, request, pk=None):
        return Response(self.get_serializer(self.get_object()).data)

    def requested_slot(self, request):
        serializer = SlotInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        slot = get_object_or_404(TimeSlot.objects.select_related('clinic', 'doctor'), pk=serializer.validated_data['slotId'])
        if not slot_is_future(slot):
            raise ValidationError({'detail': 'Please choose a future appointment.'})
        if not slot.is_active or not slot.doctor.is_accepting or not slot.clinic.is_active:
            raise ValidationError({'detail': 'This doctor or slot is no longer available. Choose another time.'})
        return slot

    @staticmethod
    def conflict():
        return Response({'detail': 'That slot was taken or is unavailable. Times have been refreshed; please choose another time.'}, status=409)

    def lock_slot(self, slot):
        # A first write serializes SQLite booking/closing operations before rechecking availability.
        eligible = Doctor.objects.filter(pk=slot.doctor_id, is_accepting=True).update(is_accepting=F('is_accepting'))
        return eligible and TimeSlot.objects.filter(pk=slot.pk, is_active=True, clinic__is_active=True).exists()

    def create(self, request):
        slot = self.requested_slot(request)
        try:
            with transaction.atomic():
                if not self.lock_slot(slot):
                    return self.conflict()
                appointment = Appointment.objects.create(patient=request.user, slot=slot, consultation_fee=slot.clinic.fee)
        except (IntegrityError, OperationalError):
            return self.conflict()
        return Response(self.get_serializer(appointment).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        appointment = self.get_object()
        try:
            with transaction.atomic():
                changed = Appointment.objects.filter(pk=appointment.pk, patient=request.user, status='confirmed').update(status='cancelled')
                if not changed and Appointment.objects.filter(pk=appointment.pk, status='completed').exists():
                    raise ValidationError({'detail': 'Completed visits cannot be cancelled.'})
        except OperationalError:
            return self.conflict()
        appointment.refresh_from_db()
        return Response(self.get_serializer(appointment).data)

    @action(detail=True, methods=['post'])
    def reschedule(self, request, pk=None):
        appointment = self.get_object()
        slot = self.requested_slot(request)
        if slot.doctor_id != appointment.slot.doctor_id:
            raise ValidationError({'detail': 'Choose a slot with the same doctor.'})
        try:
            with transaction.atomic():
                if not self.lock_slot(slot):
                    return self.conflict()
                changed = Appointment.objects.filter(pk=appointment.pk, patient=request.user, status='confirmed').update(slot=slot, consultation_fee=slot.clinic.fee)
                if not changed:
                    raise ValidationError({'detail': 'Only confirmed appointments can be rescheduled.'})
        except (IntegrityError, OperationalError):
            return self.conflict()
        appointment.refresh_from_db()
        return Response(self.get_serializer(appointment).data)
