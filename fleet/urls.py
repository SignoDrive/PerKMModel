from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .distance_calculator import calculate_distance
from .location_autocomplete import autocomplete_location
from .firebase_auth import firebase_login, firebase_logout, get_user_profile
from .city_autocomplete import city_autocomplete, get_all_cities

# Create a router and register our viewsets with it
router = DefaultRouter()
router.register(r'drivers', views.DriverViewSet, basename='driver')
router.register(r'payment-requests', views.PaymentRequestViewSet, basename='paymentrequest')
router.register(r'job-postings', views.JobPostingViewSet, basename='jobposting')
# Note: vehicles and trips endpoints use custom function views instead of ViewSets

urlpatterns = [
    # Authentication
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Dashboard pages
    path('dashboard/', views.dashboard, name='dashboard'),
    path('driver-dashboard/', views.driver_dashboard, name='driver_dashboard'),
    path('supervisor-dashboard/', views.supervisor_dashboard, name='supervisor_dashboard'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('driver-tracking/', views.driver_tracking_view, name='driver_tracking'),
    
    # API endpoints
    path('api/', include(router.urls)),
    path('api/vehicles/', views.get_vehicles_api, name='get_vehicles_api'),
    path('api/trips/', views.get_trips_api, name='get_trips_api'),
    path('api/stats/', views.get_fleet_stats, name='get_fleet_stats_api'),
    path('api/calculate-distance/', calculate_distance, name='calculate_distance'),
    path('api/autocomplete-location/', autocomplete_location, name='autocomplete_location'),
    path('api/truck-types/', views.get_truck_types, name='get_truck_types'),
    
    # Firebase Authentication
    path('api/auth/firebase-login/', firebase_login, name='firebase_login'),
    path('api/auth/firebase-logout/', firebase_logout, name='firebase_logout'),
    path('api/auth/user-profile/', get_user_profile, name='get_user_profile'),
    path('api/create-trip/', views.create_trip_with_quantity, name='create_trip'),
    path('api/driver-tracking/', views.driver_tracking_api, name='driver_tracking_api'),
    path('api/trip-progress/', views.trip_progress_api, name='trip_progress_api'),
    
    # Payment and trip management
    path('api/approve-payment/<int:request_id>/', views.approve_payment_request, name='approve_payment_request'),
    path('api/reject-payment/<int:request_id>/', views.reject_payment_request, name='reject_payment_request'),
    path('api/assign-driver/<int:trip_id>/', views.assign_driver_to_trip, name='assign_driver_to_trip'),
    path('api/start-trip/<int:trip_id>/', views.start_trip, name='start_trip'),
    path('api/complete-trip/<int:trip_id>/', views.complete_trip, name='complete_trip'),
    path('api/submit-payment-request/', views.submit_payment_request, name='submit_payment_request'),
    path('api/apply-job/<int:job_id>/', views.apply_for_job, name='apply_for_job'),
    path('create-trip-and-payment/', views.create_trip_and_payment, name='create_trip_and_payment'),
    
    # User profile and settings
    path('change-password/', views.change_password_view, name='change_password'),
    
    # Fleet stats
    path('get_fleet_stats/', views.get_fleet_stats, name='get_fleet_stats'),
    
    # User management
    path('api/create-user/', views.create_user, name='create_user'),
    path('api/update-user/<int:user_id>/', views.update_user, name='update_user'),
    path('api/delete-user/<int:user_id>/', views.delete_user, name='delete_user'),
    path('api/activate-user/<int:user_id>/', views.activate_user, name='activate_user'),
    path('api/deactivate-user/<int:user_id>/', views.deactivate_user, name='deactivate_user'),
    
    # Payment requests
    path('api/payment-requests/', views.get_payment_requests, name='get_payment_requests'),
    path('api/pending-payment-requests/', views.get_pending_payment_requests, name='get_pending_payment_requests'),
    
    # Admin panel
    path('admin-panel/', views.admin_panel, name='admin_panel'),
    
    # City autocomplete
    path('api/city-autocomplete/', city_autocomplete, name='city_autocomplete'),
    path('api/all-cities/', get_all_cities, name='get_all_cities'),
]