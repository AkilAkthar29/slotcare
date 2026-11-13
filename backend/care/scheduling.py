from datetime import datetime, timedelta
from django.db.models import Exists, OuterRef, Q
from django.utils import timezone
from .models import Appointment, TimeSlot


def future_slots(queryset=None):
    now = timezone.localtime()
    qs = queryset if queryset is not None else TimeSlot.objects.all()
    return qs.filter(Q(date__gt=now.date()) | Q(date=now.date(), time__gt=now.time().replace(tzinfo=None)))


def annotated_slots(queryset):
    return queryset.select_related('clinic__region', 'doctor').annotate(booked=Exists(Appointment.objects.filter(slot_id=OuterRef('pk'), status='confirmed')))


def open_slots(queryset=None):
    return annotated_slots(future_slots(queryset)).filter(is_active=True, clinic__is_active=True, doctor__is_accepting=True, booked=False)


def slot_has_ended(slot):
    end = timezone.make_aware(datetime.combine(slot.date, slot.time)) + timedelta(minutes=30)
    return end <= timezone.now()


def slot_is_future(slot):
    return timezone.make_aware(datetime.combine(slot.date, slot.time)) > timezone.now()
