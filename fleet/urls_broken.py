from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views, notification_system
from .distance_calculator import calculate_distance
from .trip_management import create_trip, get_trip_details
from .views import CustomPasswordChangeView

router = DefaultRouter()
router.register(r'vehicles', views.VehicleViewSet, basename='vehicle')
router.register(r'drivers', views.DriverViewSet, basename='driver')
router.register(r'trips', views.TripViewSet, basename='trip')
router.register(r'payment-requests',
                views.PaymentRequestViewSet,
                basename='paymentrequest')
router.register(r'job-postings',
                views.JobPostingViewSet,
                basename='jobposting')

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('driver-dashboard/', views.driver_dashboard, name='driver_dashboard'),
    path('supervisor-dashboard/',
         views.supervisor_dashboard,
         name='supervisor_dashboard'),
    # path('profile/', views.edit_profile, name='edit_profile'),
    path('change-password/',
         CustomPasswordChangeView.as_view(),
         name='change_password'),

    # API endpoints
    path('api/', include(router.urls)),
    # path('api/analytics/', views.analytics_view, name='analytics'),
    path('api/pricing-calculator/',
         views.pricing_calculator,
         name='pricing_calculator'),
    path('api/submit-payment-request/',
         views.submit_payment_request,
         name='submit_payment_request'),
    path('api/review-payment-request/<int:request_id>/',
         views.review_payment_request,
         name='review_payment_request'),
    path('supervisor-approve-request/<int:request_id>/',
         views.supervisor_approve_request,
         name='supervisor_approve_request'),
    path('get-driver-location/<int:driver_id>/',
         views.get_driver_location,
         name='get_driver_location'),
    path('update-driver-location/<int:driver_id>/',
         views.update_driver_location,
         name='update_driver_location'),
    path('api/ola-maps-config/',
         views.get_ola_maps_config,
         name='ola_maps_config'),
    path('api/start-trip/<int:trip_id>/', views.start_trip, name='start_trip'),
    path('api/complete-trip/<int:trip_id>/',
         views.complete_trip,
         name='complete_trip'),
    path('api/calculate-distance/',
         calculate_distance,
         name='calculate_distance'),
    path('api/create-trip/', create_trip, name='create_trip'),
    path('api/trip/<int:trip_id>/', get_trip_details, name='get_trip_details'),

    # Notification system
    path('api/notifications/',
         notification_system.get_notifications,
         name='get_notifications'),
    path('api/notifications/<int:notification_id>/read/',
         notification_system.mark_notification_read,
         name='mark_notification_read'),
    path('api/notifications/mark-all-read/',
         notification_system.mark_all_notifications_read,
         name='mark_all_notifications_read'),
    path('api/notifications/action/',
         notification_system.handle_notification_action,
         name='handle_notification_action'),

    # Admin routes
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/reset-password/',
         views.admin_reset_password,
         name='admin_reset_password'),
    path('admin/get-user/<int:user_id>/',
         views.admin_get_user,
         name='admin_get_user'),
    path('admin/update-user/',
         views.admin_update_user,
         name='admin_update_user'),
    path('admin/toggle-user-status/',
         views.admin_toggle_user_status,
         name='admin_toggle_user_status'),
]
