from rest_framework.permissions import BasePermission


class IsPatient(BasePermission):
    message = 'Use a patient account to manage patient bookings.'

    def has_permission(self, request, view):
        return bool(request.user.is_authenticated and not hasattr(request.user, 'doctor_profile'))


class IsDoctor(BasePermission):
    message = 'A linked doctor account is required for this portal.'

    def has_permission(self, request, view):
        return bool(request.user.is_authenticated and hasattr(request.user, 'doctor_profile'))
