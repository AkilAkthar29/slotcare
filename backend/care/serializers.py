from django.utils import timezone
from rest_framework import serializers
from .models import Appointment, Clinic, Doctor, Region, TimeSlot
from .scheduling import open_slots, slot_has_ended


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    portal = serializers.ChoiceField(choices=['patient', 'doctor'], default='patient')


class RegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = ['id', 'city', 'area', 'aliases']


class ClinicSerializer(serializers.ModelSerializer):
    region = RegionSerializer(read_only=True)

    class Meta:
        model = Clinic
        fields = ['id', 'name', 'address', 'fee', 'region', 'is_active']


class SlotSerializer(serializers.ModelSerializer):
    doctorId = serializers.CharField(source='doctor_id')
    time = serializers.TimeField(format='%I:%M %p')
    booked = serializers.BooleanField(read_only=True, default=False)
    clinic = ClinicSerializer(read_only=True)

    class Meta:
        model = TimeSlot
        fields = ['id', 'doctorId', 'date', 'time', 'booked', 'is_active', 'clinic']


class DoctorSerializer(serializers.ModelSerializer):
    region = RegionSerializer(read_only=True)
    acceptingAppointments = serializers.BooleanField(source='is_accepting', read_only=True)
    clinics = serializers.SerializerMethodField()
    nextAvailable = serializers.SerializerMethodField()
    available = serializers.SerializerMethodField()

    def scoped_clinics(self, obj):
        clinics = [c for c in obj.clinics.all() if c.is_active]
        request = self.context.get('request')
        if request:
            params = request.query_params
            clinics = [c for c in clinics if (not params.get('region') or str(c.region_id) == params['region']) and (not params.get('area') or (c.region and c.region.area.casefold() == params['area'].casefold())) and (not params.get('city') or (c.region and c.region.city.casefold() == params['city'].casefold()))]
        return clinics

    def get_clinics(self, obj):
        return ClinicSerializer(self.scoped_clinics(obj), many=True).data

    def next_slot(self, obj):
        cache = self.context.setdefault('next_slot_cache', {})
        if obj.pk not in cache:
            ids = {c.pk for c in self.scoped_clinics(obj)}
            # Prefetched open slots prevent per-doctor queries on directory results.
            slots = getattr(obj, 'directory_slots', None)
            cache[obj.pk] = next((s for s in slots if s.clinic_id in ids), None) if slots is not None else open_slots(TimeSlot.objects.filter(doctor=obj, clinic_id__in=ids)).first()
        return cache[obj.pk]

    def get_nextAvailable(self, obj):
        slot = self.next_slot(obj)
        return SlotSerializer(slot).data if slot else None

    def get_available(self, obj):
        return self.next_slot(obj) is not None

    class Meta:
        model = Doctor
        # Legacy fields remain readable during transition; clinic-aware clients use clinics and nextAvailable.
        fields = ['id', 'name', 'specialty', 'clinic', 'fee', 'initials', 'color', 'experience', 'rating', 'bio', 'region', 'available', 'acceptingAppointments', 'clinics', 'nextAvailable']


class DoctorSettingsSerializer(serializers.ModelSerializer):
    acceptingAppointments = serializers.BooleanField(source='is_accepting')

    class Meta:
        model = Doctor
        fields = ['acceptingAppointments']


class ClinicInputSerializer(serializers.ModelSerializer):
    regionId = serializers.PrimaryKeyRelatedField(source='region', queryset=Region.objects.all())

    class Meta:
        model = Clinic
        fields = ['name', 'address', 'fee', 'regionId']
        extra_kwargs = {'address': {'required': True, 'allow_blank': False}}


class DoctorSlotInputSerializer(serializers.Serializer):
    clinicId = serializers.PrimaryKeyRelatedField(source='clinic', queryset=Clinic.objects.all())
    date = serializers.DateField()
    time = serializers.TimeField()

    def validate(self, attrs):
        from datetime import datetime
        clinic = attrs['clinic']
        doctor = self.context['doctor']
        if clinic.doctor_id != doctor.pk or not clinic.is_active:
            raise serializers.ValidationError({'clinicId': 'Select one of your active clinics.'})
        start = timezone.make_aware(datetime.combine(attrs['date'], attrs['time']))
        if start <= timezone.now():
            raise serializers.ValidationError({'date': 'Choose a future appointment time.'})
        if attrs['time'].minute not in [0, 30] or attrs['time'].second or attrs['time'].microsecond:
            raise serializers.ValidationError({'time': 'Slots must start on the hour or half hour.'})
        return attrs


class AppointmentSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)
    doctorId = serializers.CharField(source='slot.doctor_id', read_only=True)
    doctorName = serializers.CharField(source='slot.doctor.name', read_only=True)
    specialty = serializers.CharField(source='slot.doctor.specialty', read_only=True)
    slotId = serializers.IntegerField(source='slot_id', read_only=True)
    date = serializers.DateField(source='slot.date', read_only=True)
    time = serializers.TimeField(source='slot.time', format='%I:%M %p', read_only=True)
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)
    clinic = ClinicSerializer(source='slot.clinic', read_only=True)
    fee = serializers.SerializerMethodField()

    def get_fee(self, obj):
        return obj.consultation_fee if obj.consultation_fee is not None else obj.slot.clinic.fee

    class Meta:
        model = Appointment
        fields = ['id', 'doctorId', 'doctorName', 'specialty', 'slotId', 'date', 'time', 'status', 'createdAt', 'clinic', 'fee']
        read_only_fields = fields


class SlotInputSerializer(serializers.Serializer):
    slotId = serializers.IntegerField(min_value=1)


class DoctorAppointmentSerializer(AppointmentSerializer):
    patientName = serializers.SerializerMethodField()
    canComplete = serializers.SerializerMethodField()

    def get_patientName(self, obj):
        return obj.patient.get_full_name() or obj.patient.username

    def get_canComplete(self, obj):
        return obj.status == 'confirmed' and slot_has_ended(obj.slot)

    class Meta(AppointmentSerializer.Meta):
        fields = AppointmentSerializer.Meta.fields + ['patientName', 'canComplete']
        read_only_fields = fields
