from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import AppointmentViewSet, AuthViewSet, DoctorViewSet, RegionViewSet
from .doctor_portal import DoctorPortalViewSet

router = DefaultRouter()
router.register('auth', AuthViewSet, basename='auth')
router.register('regions', RegionViewSet)
router.register('doctor-portal', DoctorPortalViewSet, basename='doctor-portal')
router.register('doctors', DoctorViewSet)
router.register('appointments', AppointmentViewSet, basename='appointment')
urlpatterns = [path('', include(router.urls))]
