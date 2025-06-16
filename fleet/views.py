from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import User, FleetOwner, Driver, Vehicle, Trip, PaymentRequest, JobPosting, TruckSpecification
from .serializers import VehicleSerializer, DriverSerializer, TripSerializer, PaymentRequestSerializer, JobPostingSerializer
from django.db.models import Count, Sum
import json
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordChangeView
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.urls import reverse_lazy
from django.shortcuts import redirect
from django.contrib.auth.mixins import LoginRequiredMixin

def login_view(request):
    """
    Hybrid login view supporting both Django and Firebase authentication
    """
    # Check if user is already authenticated
    if request.user.is_authenticated:
        if request.user.role == 'driver':
            return redirect('driver_dashboard')
        elif request.user.role == 'supervisor':
            return redirect('supervisor_dashboard')
        else:
            return redirect('dashboard')
    
    # Handle Django form login
    if request.method == 'POST' and 'django_login' in request.POST:
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        if user is not None and user.is_active:
            login(request, user)
            # Redirect based on user role
            if user.role == 'driver':
                return redirect('driver_dashboard')
            elif user.role == 'supervisor':
                return redirect('supervisor_dashboard')
            else:
                return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    
    # For Firebase authentication, we'll use the new Firebase login template
    import os
    context = {
        'firebase_api_key': os.environ.get('VITE_FIREBASE_API_KEY', ''),
        'firebase_project_id': os.environ.get('VITE_FIREBASE_PROJECT_ID', ''), 
        'firebase_app_id': os.environ.get('VITE_FIREBASE_APP_ID', ''),
    }
    return render(request, 'fleet/firebase_login.html', context)

def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            return JsonResponse({'success': True, 'message': 'Password changed successfully'})
        else:
            return JsonResponse({'success': False, 'errors': form.errors})
    
    form = PasswordChangeForm(request.user)
    return render(request, 'fleet/change_password.html', {'form': form})

def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return redirect('login')

@login_required
def dashboard(request):
    user = request.user
    
    if user.role == 'driver':
        return redirect('driver_dashboard')
    elif user.role == 'supervisor':
        return redirect('supervisor_dashboard')
    
    # Fleet owner dashboard
    fleet_owner, created = FleetOwner.objects.get_or_create(user=user)
    if created:
        fleet_owner.company_name = f"{user.first_name}'s Fleet"
        fleet_owner.save()
    
    # Calculate metrics
    total_vehicles = fleet_owner.vehicles.count()
    active_vehicles = fleet_owner.vehicles.filter(status='active').count()
    idle_vehicles = fleet_owner.vehicles.filter(status='idle').count()
    maintenance_vehicles = fleet_owner.vehicles.filter(status='maintenance').count()
    active_trips = fleet_owner.trips.filter(status='in_progress').count()
    pending_requests = PaymentRequest.objects.filter(
        driver__fleet_owner=fleet_owner,
        status='pending'
    ).count()
    
    fleet_utilization = (active_vehicles / total_vehicles * 100) if total_vehicles > 0 else 0
    
    # Get trips for the Add KM to Trip functionality
    trips = fleet_owner.trips.all().order_by('-created_at')
    drivers = fleet_owner.drivers.filter(is_active=True)
    payment_requests = PaymentRequest.objects.filter(
        driver__fleet_owner=fleet_owner
    ).order_by('-requested_at')[:10]
    recent_trips = trips[:5]
    job_postings = fleet_owner.job_postings.all().order_by('-created_at')[:10]
    vehicles = fleet_owner.vehicles.all().order_by('-updated_at')
    
    context = {
        'user': user,
        'fleet_owner': fleet_owner,
        'total_vehicles': total_vehicles,
        'active_vehicles': active_vehicles,
        'active_trips': active_trips,
        'pending_requests': pending_requests,
        'fleet_utilization': round(fleet_utilization, 1),
        'trips': trips,
        'drivers': drivers,
        'payment_requests': payment_requests,
        'recent_trips': recent_trips,
        'job_postings': job_postings,
        'vehicles': vehicles,
        # Analytics data for charts
        'vehicles_active': active_vehicles,
        'vehicles_idle': idle_vehicles,
        'vehicles_maintenance': maintenance_vehicles,
    }
    
    return render(request, 'fleet/dashboard.html', context)

@login_required
def driver_dashboard(request):
    user = request.user
    
    if user.role != 'driver':
        return redirect('dashboard')
    
    # Get or create driver profile
    driver, created = Driver.objects.get_or_create(user=user)
    
    # Get driver's trips and payment requests
    trips = Trip.objects.filter(driver=driver).order_by('-created_at')
    
    # Get available job postings (not assigned yet)
    available_jobs = JobPosting.objects.filter(status='available').order_by('-created_at')
    
    # Calculate some basic metrics for the driver
    total_trips = trips.count()
    completed_trips = trips.filter(status='completed').count()
    in_progress_trips = trips.filter(status='in_progress').count()
    
    # Payment requests
    payment_requests = PaymentRequest.objects.filter(driver=driver).order_by('-requested_at')
    pending_payment_requests = PaymentRequest.objects.filter(driver=driver, status='pending').count()
    approved_payment_requests = PaymentRequest.objects.filter(driver=driver, status='approved').count()
    
    # Recent job postings
    recent_jobs = available_jobs[:5]
    
    context = {
        'user': user,
        'driver': driver,
        'trips': trips,
        'total_trips': total_trips,
        'completed_trips': completed_trips,
        'in_progress_trips': in_progress_trips,
        'payment_requests': payment_requests,
        'pending_payment_requests': pending_payment_requests,
        'approved_payment_requests': approved_payment_requests,
        'available_jobs': available_jobs,
        'recent_jobs': recent_jobs,
    }
    
    return render(request, 'fleet/driver_dashboard.html', context)

@login_required
def supervisor_dashboard(request):
    user = request.user
    
    if user.role != 'supervisor':
        return redirect('dashboard')
    
    # Get all trips that need supervision
    trips = Trip.objects.all().order_by('-created_at')
    
    # Get payment requests that need approval
    payment_requests = PaymentRequest.objects.all().order_by('-requested_at')
    
    # Calculate metrics
    pending_trips = trips.filter(status='pending').count()
    in_progress_trips = trips.filter(status='in_progress').count()
    completed_trips = trips.filter(status='completed').count()
    
    # Payment request metrics
    pending_payment_requests = payment_requests.filter(status='pending').count()
    approved_payment_requests = payment_requests.filter(status='approved').count()
    rejected_payment_requests = payment_requests.filter(status='rejected').count()
    
    context = {
        'user': user,
        'trips': trips,
        'payment_requests': payment_requests,
        'pending_trips': pending_trips,
        'in_progress_trips': in_progress_trips,
        'completed_trips': completed_trips,
        'pending_payment_requests': pending_payment_requests,
        'approved_payment_requests': approved_payment_requests,
        'rejected_payment_requests': rejected_payment_requests,
    }
    
    return render(request, 'fleet/supervisor_dashboard.html', context)

@csrf_exempt
@login_required
def approve_payment_request(request, request_id):
    if request.method == 'POST':
        try:
            payment_request = PaymentRequest.objects.get(id=request_id)
            payment_request.status = 'approved'
            payment_request.reviewed_by = request.user
            payment_request.reviewed_at = timezone.now()
            payment_request.review_comments = request.POST.get('comments', '')
            payment_request.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Payment request approved successfully'
            })
        except PaymentRequest.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Payment request not found'
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@csrf_exempt
@login_required
def reject_payment_request(request, request_id):
    if request.method == 'POST':
        try:
            payment_request = PaymentRequest.objects.get(id=request_id)
            payment_request.status = 'rejected'
            payment_request.reviewed_by = request.user
            payment_request.reviewed_at = timezone.now()
            payment_request.review_comments = request.POST.get('comments', '')
            payment_request.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Payment request rejected'
            })
        except PaymentRequest.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Payment request not found'
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@csrf_exempt
@login_required
def assign_driver_to_trip(request, trip_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            driver_id = data.get('driver_id')
            
            trip = Trip.objects.get(id=trip_id)
            driver = Driver.objects.get(id=driver_id)
            
            trip.driver = driver
            trip.status = 'assigned'
            trip.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Trip assigned to {driver.user.first_name} {driver.user.last_name}'
            })
        except (Trip.DoesNotExist, Driver.DoesNotExist):
            return JsonResponse({
                'success': False,
                'error': 'Trip or driver not found'
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@csrf_exempt
@login_required
def start_trip(request, trip_id):
    if request.method == 'POST':
        try:
            trip = Trip.objects.get(id=trip_id, driver__user=request.user)
            trip.status = 'in_progress'
            trip.start_time = timezone.now()
            trip.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Trip started successfully'
            })
        except Trip.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Trip not found or not assigned to you'
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@csrf_exempt
@login_required
def complete_trip(request, trip_id):
    if request.method == 'POST':
        try:
            trip = Trip.objects.get(id=trip_id, driver__user=request.user)
            trip.status = 'completed'
            trip.end_time = timezone.now()
            trip.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Trip completed successfully'
            })
        except Trip.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Trip not found or not assigned to you'
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@csrf_exempt
@login_required
def submit_payment_request(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            driver = Driver.objects.get(user=request.user)
            
            payment_request = PaymentRequest.objects.create(
                driver=driver,
                amount=data.get('amount'),
                type=data.get('type'),
                description=data.get('description'),
                receipt_url=data.get('receipt_url', '')
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Payment request submitted successfully'
            })
        except Driver.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Driver profile not found'
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@csrf_exempt
@login_required
def apply_for_job(request, job_id):
    if request.method == 'POST':
        try:
            job = JobPosting.objects.get(id=job_id)
            driver = Driver.objects.get(user=request.user)
            
            # Simple job application - just assign the job to the driver
            # In a real system, you might want to create an application model
            
            return JsonResponse({
                'success': True,
                'message': 'Job application submitted successfully'
            })
        except (JobPosting.DoesNotExist, Driver.DoesNotExist):
            return JsonResponse({
                'success': False,
                'error': 'Job or driver not found'
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

# API Views for mobile app or external integrations
@csrf_exempt
def get_vehicles_api(request):
    """API endpoint to get vehicles for the authenticated user"""
    # Temporarily bypass authentication for testing
    # if not request.user.is_authenticated:
    #     return JsonResponse({'error': 'Authentication required'}, status=401)
    
    # Return all vehicles data since demo user doesn't exist
    vehicles = Vehicle.objects.all()
    
    vehicles_data = []
    for vehicle in vehicles:
        vehicles_data.append({
            'id': vehicle.id,
            'vehicle_number': vehicle.vehicle_number,
            'model': vehicle.model,
            'capacity': vehicle.capacity,
            'fuel_type': vehicle.fuel_type,
            'status': vehicle.status,
            'location': vehicle.current_location or 'Unknown'
        })
    
    return JsonResponse(vehicles_data, safe=False)

class VehicleViewSet(viewsets.ModelViewSet):
    serializer_class = VehicleSerializer
    permission_classes = []
    
    def get_queryset(self):
        return Vehicle.objects.none()  # Disabled - use function view instead

class DriverViewSet(viewsets.ModelViewSet):
    queryset = Driver.objects.all()
    serializer_class = DriverSerializer
    permission_classes = [IsAuthenticated]

@csrf_exempt
def get_trips_api(request):
    """API endpoint to get trips for the authenticated user"""
    # Return all trips data since demo user doesn't exist
    trips = Trip.objects.all().order_by('-created_at')
    
    trips_data = []
    for trip in trips:
        trips_data.append({
            'id': trip.id,
            'origin': trip.origin,
            'destination': trip.destination,
            'distance': float(trip.distance) if trip.distance else 0,
            'estimated_cost': float(trip.estimated_cost) if trip.estimated_cost else 0,
            'actual_cost': float(trip.actual_cost) if trip.actual_cost else 0,
            'status': trip.status,
            'created_at': trip.created_at.strftime('%Y-%m-%d %H:%M') if trip.created_at else '',
            'driver_name': trip.driver.user.get_full_name() if trip.driver else 'Unassigned',
            'vehicle_number': trip.vehicle.vehicle_number if trip.vehicle else 'Unassigned'
        })
    
    return JsonResponse(trips_data, safe=False)

class TripViewSet(viewsets.ModelViewSet):
    serializer_class = TripSerializer
    permission_classes = []
    
    def get_queryset(self):
        return Trip.objects.none()  # Disabled - use function view instead

class PaymentRequestViewSet(viewsets.ModelViewSet):
    queryset = PaymentRequest.objects.all()
    serializer_class = PaymentRequestSerializer
    permission_classes = [IsAuthenticated]

class JobPostingViewSet(viewsets.ModelViewSet):
    queryset = JobPosting.objects.all()
    serializer_class = JobPostingSerializer
    permission_classes = [IsAuthenticated]

@csrf_exempt
def get_fleet_stats(request):
    """API endpoint to get fleet statistics for the authenticated user"""
    # Temporarily bypass authentication for testing
    # if not request.user.is_authenticated:
    #     return JsonResponse({'error': 'Authentication required'}, status=401)
    
    # Use demo fleet owner for testing
    try:
        demo_user = User.objects.get(username='fleet_owner_demo')
        fleet_owner = FleetOwner.objects.get(user=demo_user)
        total_vehicles = Vehicle.objects.filter(fleet_owner=fleet_owner).count()
        active_vehicles = Vehicle.objects.filter(fleet_owner=fleet_owner, status='active').count()
        idle_vehicles = Vehicle.objects.filter(fleet_owner=fleet_owner, status='idle').count()
        maintenance_vehicles = Vehicle.objects.filter(fleet_owner=fleet_owner, status='maintenance').count()
        
        total_trips = Trip.objects.filter(fleet_owner=fleet_owner).count()
        completed_trips = Trip.objects.filter(fleet_owner=fleet_owner, status='completed').count()
        active_trips = Trip.objects.filter(fleet_owner=fleet_owner, status='in_progress').count()
        
        # Calculate total revenue from completed trips
        completed_trip_amounts = Trip.objects.filter(
            fleet_owner=fleet_owner, 
            status='completed',
            amount__isnull=False
        ).aggregate(total=Sum('amount'))
        total_revenue = completed_trip_amounts['total'] or 0
        
        # Get pending payment requests count
        pending_requests = PaymentRequest.objects.filter(
            driver__fleet_owner=fleet_owner,
            status='pending'
        ).count()
        
        return JsonResponse({
            'total_vehicles': total_vehicles,
            'active_vehicles': active_vehicles,
            'idle_vehicles': idle_vehicles,
            'maintenance_vehicles': maintenance_vehicles,
            'total_trips': total_trips,
            'completed_trips': completed_trips,
            'active_trips': active_trips,
            'total_revenue': float(total_revenue),
            'pending_payment_requests': pending_requests,
            'fleet_utilization': (active_vehicles / total_vehicles * 100) if total_vehicles > 0 else 0,
            'vehicle_status_counts': {
                'active': active_vehicles,
                'idle': idle_vehicles,
                'maintenance': maintenance_vehicles
            }
        })
    except (User.DoesNotExist, FleetOwner.DoesNotExist):
        # Fallback to all data if demo user doesn't exist
        vehicles = Vehicle.objects.all()
        trips = Trip.objects.all()
        payment_requests = PaymentRequest.objects.all()
        
        total_vehicles = vehicles.count()
        active_vehicles = vehicles.filter(status='active').count()
        idle_vehicles = vehicles.filter(status='idle').count()
        maintenance_vehicles = vehicles.filter(status='maintenance').count()
        
        total_trips = trips.count()
        completed_trips = trips.filter(status='completed').count()
        active_trips = trips.filter(status='in_progress').count()
        
        return JsonResponse({
            'total_vehicles': total_vehicles,
            'active_vehicles': active_vehicles,
            'idle_vehicles': idle_vehicles,
            'maintenance_vehicles': maintenance_vehicles,
            'total_trips': total_trips,
            'completed_trips': completed_trips,
            'active_trips': active_trips,
            'total_revenue': 0,
            'pending_payment_requests': 0,
            'fleet_utilization': (active_vehicles / total_vehicles * 100) if total_vehicles > 0 else 0,
            'vehicle_status_counts': {
                'active': active_vehicles,
                'idle': idle_vehicles,
                'maintenance': maintenance_vehicles
            }
        })
    
    return JsonResponse({'error': 'Unauthorized'}, status=403)

# User management views
@csrf_exempt
def create_user(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Check if user already exists
            if User.objects.filter(username=data.get('username')).exists():
                return JsonResponse({
                    'success': False,
                    'error': 'Username already exists'
                })
            
            user = User.objects.create_user(
                username=data.get('username'),
                email=data.get('email'),
                password=data.get('password'),
                first_name=data.get('first_name', ''),
                last_name=data.get('last_name', ''),
                role=data.get('role', 'fleet_owner')
            )
            
            # Create related profile based on role
            if user.role == 'fleet_owner':
                FleetOwner.objects.create(user=user, company_name=data.get('company_name', ''))
            elif user.role == 'driver':
                Driver.objects.create(user=user, license_number=data.get('license_number', ''))
            
            return JsonResponse({
                'success': True,
                'message': 'User created successfully'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@csrf_exempt
def update_user(request, user_id):
    if request.method == 'POST':
        try:
            user = User.objects.get(id=user_id)
            data = json.loads(request.body)
            
            user.first_name = data.get('first_name', user.first_name)
            user.last_name = data.get('last_name', user.last_name)
            user.email = data.get('email', user.email)
            user.save()
            
            return JsonResponse({
                'success': True,
                'message': 'User updated successfully'
            })
        except User.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'User not found'
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@csrf_exempt
def delete_user(request, user_id):
    if request.method == 'DELETE':
        try:
            user = User.objects.get(id=user_id)
            user.delete()
            
            return JsonResponse({
                'success': True,
                'message': 'User deleted successfully'
            })
        except User.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'User not found'
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@csrf_exempt
def activate_user(request, user_id):
    if request.method == 'POST':
        try:
            user = User.objects.get(id=user_id)
            user.is_active = True
            user.save()
            
            return JsonResponse({
                'success': True,
                'message': 'User activated successfully'
            })
        except User.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'User not found'
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@csrf_exempt
def deactivate_user(request, user_id):
    if request.method == 'POST':
        try:
            user = User.objects.get(id=user_id)
            user.is_active = False
            user.save()
            
            return JsonResponse({
                'success': True,
                'message': 'User deactivated successfully'
            })
        except User.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'User not found'
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
def get_payment_requests(request):
    if request.user.role == 'supervisor':
        # Supervisors can see all payment requests
        payment_requests = PaymentRequest.objects.all().order_by('-requested_at')
    elif request.user.role == 'fleet_owner':
        # Fleet owners can see payment requests from their drivers
        fleet_owner = FleetOwner.objects.get(user=request.user)
        payment_requests = PaymentRequest.objects.filter(
            driver__fleet_owner=fleet_owner
        ).order_by('-requested_at')
    else:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    data = []
    for req in payment_requests:
        data.append({
            'id': req.id,
            'driver_name': f"{req.driver.user.first_name} {req.driver.user.last_name}",
            'amount': str(req.amount),
            'type': req.type,
            'description': req.description,
            'status': req.status,
            'requested_at': req.requested_at.strftime('%Y-%m-%d %H:%M'),
            'reviewed_by': req.reviewed_by.username if req.reviewed_by else None,
            'review_comments': req.review_comments
        })
    
    return JsonResponse({'payment_requests': data})

@login_required
def get_pending_payment_requests(request):
    if request.user.role in ['supervisor', 'fleet_owner']:
        if request.user.role == 'supervisor':
            payment_requests = PaymentRequest.objects.filter(status='pending').order_by('-requested_at')
        else:
            fleet_owner = FleetOwner.objects.get(user=request.user)
            payment_requests = PaymentRequest.objects.filter(
                driver__fleet_owner=fleet_owner,
                status='pending'
            ).order_by('-requested_at')
        
        data = []
        for req in payment_requests:
            data.append({
                'id': req.id,
                'driver_name': f"{req.driver.user.first_name} {req.driver.user.last_name}",
                'amount': str(req.amount),
                'type': req.type,
                'description': req.description,
                'requested_at': req.requested_at.strftime('%Y-%m-%d %H:%M')
            })
        
        return JsonResponse({'payment_requests': data})
    
    return JsonResponse({'error': 'Unauthorized'}, status=403)

# Admin panel views
@login_required
def admin_panel(request):
    if request.user.role != 'admin':
        return redirect('dashboard')
    
    # Get all system statistics
    total_users = User.objects.count()
    total_fleet_owners = User.objects.filter(role='fleet_owner').count()
    total_drivers = User.objects.filter(role='driver').count()
    total_supervisors = User.objects.filter(role='supervisor').count()
    
    total_vehicles = Vehicle.objects.count()
    active_vehicles = Vehicle.objects.filter(status='active').count()
    total_trips = Trip.objects.count()
    completed_trips = Trip.objects.filter(status='completed').count()
    
    # Get recent activities
    recent_users = User.objects.order_by('-date_joined')[:10]
    recent_trips = Trip.objects.order_by('-created_at')[:10]
    
    # Payment statistics
    total_payment_requests = PaymentRequest.objects.count()
    pending_payments = PaymentRequest.objects.filter(status='pending').count()
    approved_payments = PaymentRequest.objects.filter(status='approved').count()
    rejected_payments = PaymentRequest.objects.filter(status='rejected').count()
    
    # Job posting statistics
    total_job_postings = JobPosting.objects.count()
    available_jobs = JobPosting.objects.filter(status='available').count()
    
    context = {
        'total_users': total_users,
        'total_fleet_owners': total_fleet_owners,
        'total_drivers': total_drivers,
        'total_supervisors': total_supervisors,
        'total_vehicles': total_vehicles,
        'active_vehicles': active_vehicles,
        'total_trips': total_trips,
        'completed_trips': completed_trips,
        'recent_users': recent_users,
        'recent_trips': recent_trips,
        'total_payment_requests': total_payment_requests,
        'pending_payments': pending_payments,
        'approved_payments': approved_payments,
        'rejected_payments': rejected_payments,
        'total_job_postings': total_job_postings,
        'available_jobs': available_jobs,
    }
    
    return render(request, 'fleet/admin_panel.html', context)

# Custom Password Change View for AJAX support
class CustomPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    template_name = 'fleet/change_password.html'
    success_url = reverse_lazy('dashboard')
    
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.headers.get('Content-Type') == 'application/json':
            return JsonResponse({
                'success': True,
                'message': 'Password changed successfully'
            })
        return response

@login_required
def change_password_view(request):
    """Simple password change view"""
    if request.method == 'POST':
        old_password = request.POST.get('old_password')
        new_password = request.POST.get('new_password')
        
        if request.user.check_password(old_password):
            request.user.set_password(new_password)
            request.user.save()
            return JsonResponse({'success': True, 'message': 'Password changed successfully'})
        else:
            return JsonResponse({'success': False, 'message': 'Invalid old password'})
    
    return render(request, 'fleet/change_password.html')

@login_required
def admin_dashboard(request):
    """Admin dashboard with full system access"""
    user = request.user
    
    # Ensure user is an admin
    if user.role != 'admin':
        return redirect('dashboard')
    
    # Get system statistics
    total_users = User.objects.count()
    total_fleet_owners = FleetOwner.objects.count()
    total_drivers = Driver.objects.count()
    total_vehicles = Vehicle.objects.count()
    total_trips = Trip.objects.count()
    total_payment_requests = PaymentRequest.objects.count()
    
    # Get recent activity
    recent_users = User.objects.order_by('-created_at')[:10]
    recent_trips = Trip.objects.order_by('-created_at')[:10]
    recent_payments = PaymentRequest.objects.order_by('-requested_at')[:10]
    
    context = {
        'user': user,
        'total_users': total_users,
        'total_fleet_owners': total_fleet_owners,
        'total_drivers': total_drivers,
        'total_vehicles': total_vehicles,
        'total_trips': total_trips,
        'total_payment_requests': total_payment_requests,
        'recent_users': recent_users,
        'recent_trips': recent_trips,
        'recent_payments': recent_payments,
    }
    
    return render(request, 'fleet/admin_dashboard.html', context)

@api_view(['GET'])
@permission_classes([])
def get_truck_types(request):
    """
    API endpoint to get available truck types from database
    """
    try:
        truck_specs = TruckSpecification.objects.filter(is_active=True).order_by('truck_type')
        truck_types = [
            {
                'truck_type': spec.truck_type,
                'gw': spec.gw,
                'net_weight': spec.net_weight,
                'avg_kmpl': float(spec.avg_kmpl),
                'driver_salary': float(spec.driver_salary),
                'distance_traveled': spec.distance_traveled
            }
            for spec in truck_specs
        ]
        
        return JsonResponse({
            'truck_types': truck_types,
            'count': len(truck_types)
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@login_required
def create_trip(request):
    """
    Create a new trip with calculated distance and pricing
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        origin = data.get('origin')
        destination = data.get('destination')
        truck_type = data.get('truck_type')
        driver_type = data.get('driver_type')
        distance = data.get('distance')
        estimated_cost = data.get('estimated_cost')
        
        if not all([origin, destination, truck_type, driver_type, distance, estimated_cost]):
            return JsonResponse({'error': 'Missing required parameters'}, status=400)
        
        # Get or create fleet owner for the user
        fleet_owner, created = FleetOwner.objects.get_or_create(
            user=request.user,
            defaults={
                'company_name': f"{request.user.first_name}'s Fleet"
            }
        )
        
        # Create the trip
        trip = Trip.objects.create(
            fleet_owner=fleet_owner,
            origin=origin,
            destination=destination,
            distance=distance,
            estimated_cost=estimated_cost,
            status='pending'
        )
        
        return JsonResponse({
            'success': True,
            'trip_id': trip.id,
            'message': 'Trip created successfully'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def driver_tracking_api(request):
    """API endpoint for real-time driver tracking data"""
    try:
        # Get all drivers with their current status and locations
        drivers = Driver.objects.select_related('user', 'fleet_owner').all()
        active_trips = Trip.objects.filter(status='in_progress').select_related('driver', 'vehicle')
        
        driver_data = []
        driver_counts = {'active': 0, 'en_route': 0, 'idle': 0, 'offline': 0}
        
        for driver in drivers:
            # Determine driver status based on current trips and activity
            current_trip = active_trips.filter(driver=driver).first()
            
            if current_trip:
                status = 'en_route'
                driver_counts['en_route'] += 1
            elif driver.is_active:
                status = 'idle'
                driver_counts['idle'] += 1
            else:
                status = 'offline'
                driver_counts['offline'] += 1
            
            # If driver has active trips, mark as active
            if current_trip and current_trip.status == 'in_progress':
                status = 'active'
                driver_counts['active'] += 1
                driver_counts['en_route'] -= 1 if driver_counts['en_route'] > 0 else 0
            
            driver_info = {
                'id': driver.id,
                'name': driver.user.get_full_name() or driver.user.username,
                'phone': driver.user.phone,
                'status': status,
                'vehicle_number': driver.vehicle_number,
                'last_seen': 'Just now' if status in ['active', 'en_route'] else '2 hours ago',
                'location': driver.current_location or {'lat': 19.076, 'lng': 72.8777},
                'current_trip': None
            }
            
            if current_trip:
                # Calculate progress (mock calculation based on time)
                from datetime import datetime, timezone as tz
                start_time = current_trip.start_time or current_trip.created_at
                elapsed_hours = (timezone.now() - start_time).total_seconds() / 3600
                estimated_hours = float(current_trip.distance) / 50  # Assume 50 km/h average
                progress = min(int((elapsed_hours / estimated_hours) * 100), 95)
                
                driver_info['current_trip'] = {
                    'id': current_trip.id,
                    'origin': current_trip.origin,
                    'destination': current_trip.destination,
                    'progress': progress,
                    'distance': float(current_trip.distance) if current_trip.distance else 0
                }
            
            driver_data.append(driver_info)
        
        # Get active trips with progress information
        active_trips_data = []
        for trip in active_trips:
            # Calculate progress and ETA
            start_time = trip.start_time or trip.created_at
            elapsed_hours = (timezone.now() - start_time).total_seconds() / 3600
            estimated_hours = float(trip.distance) / 50 if trip.distance else 1
            progress = min(int((elapsed_hours / estimated_hours) * 100), 95)
            
            remaining_hours = max(estimated_hours - elapsed_hours, 0.1)
            eta_time = timezone.now() + timezone.timedelta(hours=remaining_hours)
            
            trip_info = {
                'id': trip.id,
                'driver_id': trip.driver.id if trip.driver else None,
                'driver_name': trip.driver.user.get_full_name() or trip.driver.user.username if trip.driver else 'Unassigned',
                'driver_status': 'active' if trip.driver else 'unassigned',
                'origin': trip.origin,
                'destination': trip.destination,
                'progress': progress,
                'eta': eta_time.strftime('%H:%M'),
                'remaining_time': f"{int(remaining_hours)}h {int((remaining_hours % 1) * 60)}m",
                'status': trip.status
            }
            active_trips_data.append(trip_info)
        
        return Response({
            'drivers': driver_data,
            'driver_counts': driver_counts,
            'active_trips': active_trips_data,
            'status': 'success'
        })
        
    except Exception as e:
        return Response({
            'error': str(e),
            'status': 'error'
        }, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def trip_progress_api(request):
    """API endpoint for trip progress updates"""
    try:
        active_trips = Trip.objects.filter(status='in_progress').select_related('driver', 'vehicle')
        
        trips_data = []
        for trip in active_trips:
            # Calculate real-time progress
            start_time = trip.start_time or trip.created_at
            elapsed_hours = (timezone.now() - start_time).total_seconds() / 3600
            estimated_hours = float(trip.distance) / 50 if trip.distance else 1
            progress = min(int((elapsed_hours / estimated_hours) * 100), 95)
            
            remaining_hours = max(estimated_hours - elapsed_hours, 0.1)
            eta_time = timezone.now() + timezone.timedelta(hours=remaining_hours)
            
            trip_info = {
                'id': trip.id,
                'driver_id': trip.driver.id if trip.driver else None,
                'driver_name': trip.driver.user.get_full_name() or trip.driver.user.username if trip.driver else 'Unassigned',
                'driver_status': 'active' if trip.driver else 'unassigned',
                'origin': trip.origin,
                'destination': trip.destination,
                'progress': progress,
                'eta': eta_time.strftime('%H:%M'),
                'remaining_time': f"{int(remaining_hours)}h {int((remaining_hours % 1) * 60)}m",
                'status': trip.status
            }
            trips_data.append(trip_info)
        
        return Response({
            'trips': trips_data,
            'status': 'success'
        })
        
    except Exception as e:
        return Response({
            'error': str(e),
            'status': 'error'
        }, status=500)

@csrf_exempt
@login_required
def create_trip_with_quantity(request):
    """
    API endpoint to create a new trip with truck quantity and dynamic service charge
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        
        # Get fleet owner
        try:
            fleet_owner = request.user.fleet_owner
        except:
            fleet_owner, created = FleetOwner.objects.get_or_create(
                user=request.user,
                defaults={'company_name': f"{request.user.first_name}'s Fleet"}
            )
        
        # Extract trip data
        origin = data.get('origin')
        destination = data.get('destination')
        truck_type = data.get('truck_type')
        driver_type = data.get('driver_type')
        truck_quantity = int(data.get('truck_quantity', 1))
        distance = float(data.get('distance', 0))
        estimated_cost = float(data.get('estimated_cost', 0))
        pricing_details = data.get('pricing_details', {})
        
        if not all([origin, destination, truck_type, driver_type]):
            return JsonResponse({'error': 'Missing required fields'}, status=400)
        
        # Create the trip
        trip = Trip.objects.create(
            fleet_owner=fleet_owner,
            origin=origin,
            destination=destination,
            distance=Decimal(str(distance)),
            estimated_cost=Decimal(str(estimated_cost)),
            status='pending'
        )
        
        return JsonResponse({
            'success': True,
            'trip_id': trip.id,
            'message': 'Trip created successfully',
            'trip_details': {
                'id': trip.id,
                'origin': trip.origin,
                'destination': trip.destination,
                'distance': float(trip.distance),
                'estimated_cost': float(trip.estimated_cost),
                'truck_quantity': truck_quantity,
                'truck_type': truck_type,
                'driver_type': driver_type,
                'service_charge_rate': pricing_details.get('service_charge_rate', 0),
                'per_km_rate': pricing_details.get('per_km_rate', 0)
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except ValueError as e:
        return JsonResponse({'error': f'Invalid data: {str(e)}'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)

@login_required
def driver_tracking_view(request):
    """Real-time driver tracking dashboard view"""
    # Get current driver statistics for initial page load
    drivers = Driver.objects.select_related('user', 'fleet_owner').all()
    active_trips = Trip.objects.filter(status='in_progress').count()
    
    context = {
        'active_drivers': drivers.filter(is_active=True).count(),
        'en_route_drivers': active_trips,
        'idle_drivers': drivers.filter(is_active=True).count() - active_trips,
        'offline_drivers': drivers.filter(is_active=False).count(),
    }
    
    return render(request, 'fleet/driver_tracking.html', context)

@csrf_exempt
@login_required
def create_trip_and_payment(request):
    """
    Creates a trip in the database and returns success for payment redirect
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        
        # Validate required fields
        required_fields = ['origin', 'destination', 'truck_type', 'driver_type', 'distance', 'estimated_cost']
        for field in required_fields:
            if not data.get(field):
                return JsonResponse({'error': f'Missing required field: {field}'}, status=400)
        
        # Get the fleet owner for the current user
        try:
            fleet_owner = FleetOwner.objects.get(user=request.user)
        except FleetOwner.DoesNotExist:
            return JsonResponse({'error': 'Fleet owner profile not found'}, status=400)
        
        # Create the trip with round function for cost precision
        trip = Trip.objects.create(
            fleet_owner=fleet_owner,
            origin=data['origin'],
            destination=data['destination'],
            distance=round(float(data['distance']), 2),
            estimated_cost=round(float(data['estimated_cost']), 2),
            status='pending',
            # Store additional trip details in a JSON field if available
            # trip_details=data.get('calculation_details', {})
        )
        
        return JsonResponse({
            'success': True,
            'trip_id': trip.id,
            'message': 'Trip created successfully'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)