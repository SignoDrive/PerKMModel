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
from .models import User, FleetOwner, Driver, Vehicle, Trip, PaymentRequest, JobPosting
from .serializers import VehicleSerializer, DriverSerializer, TripSerializer, PaymentRequestSerializer, JobPostingSerializer
from django.db.models import Count
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
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

                if user is not None:
                    login(request, user)
                    if user.role == 'driver':
                        return redirect('driver_dashboard')
                    elif user.role == 'supervisor':
                        return redirect('supervisor_dashboard')
                    else:
                        return redirect('dashboard')
                else:
                    messages.error(request, 'Invalid credentials')

            return render(request, 'fleet/login.html')

        @login_required
        def logout_view(request):
            logout(request)
            return redirect('login')



        @login_required
        def edit_profile(request):
            return render(request, 'profile/edit_profile.html')

        @login_required
        def change_password(request):
            if request.method == 'POST':
                form = PasswordChangeForm(request.user, request.POST)
                if form.is_valid():
                    user = form.save()
                    update_session_auth_hash(request, user)  # Keeps the user logged in
                    messages.success(request, 'Your password was successfully updated!')
                    return redirect('edit_profile')
                else:
                    messages.error(request, 'Please correct the errors below.')
            else:
                form = PasswordChangeForm(request.user)
            return render(request, 'profile/change_password.html', {'form': form})



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
            if request.user.role != 'driver':
                return redirect('dashboard')

            driver, created = Driver.objects.get_or_create(user=request.user)

            active_trips = driver.trips.filter(status__in=['pending', 'in_progress'])
            completed_trips = driver.trips.filter(status='completed').count()
            pending_payments = driver.payment_requests.filter(status='pending').count()


            # Get available job postings
            job_postings = JobPosting.objects.filter(status='available').order_by('-created_at')[:5]

            context = {
                'user': request.user,
                'driver': driver,
                'active_trips': active_trips,
                'completed_trips': completed_trips,
                'pending_payments': pending_payments,
                'job_postings': job_postings,
            }

            return render(request, 'fleet/driver_dashboard.html', context)

        @login_required
        def supervisor_dashboard(request):
            if request.user.role != 'supervisor':
                return redirect('dashboard')

            # Get all drivers under supervision
            all_drivers = Driver.objects.filter(is_active=True).select_related('user', 'fleet_owner')

            # Get all trips for monitoring
            all_trips = Trip.objects.all().select_related('driver__user', 'vehicle', 'fleet_owner').order_by('-created_at')
            completed_trips = all_trips.filter(status='completed')
            in_progress_trips = all_trips.filter(status='in_progress')
            pending_trips = all_trips.filter(status='pending')

            # Payment request management with approval workflow
            pending_requests = PaymentRequest.objects.filter(status='pending').select_related('driver__user', 'trip').order_by('-requested_at')
            approved_requests = PaymentRequest.objects.filter(status='approved').select_related('driver__user', 'reviewed_by').order_by('-reviewed_at')[:10]
            rejected_requests = PaymentRequest.objects.filter(status='rejected').select_related('driver__user', 'reviewed_by').order_by('-reviewed_at')[:10]

            # Job postings from fleet owners
            job_postings = JobPosting.objects.filter(status='available').select_related('fleet_owner').order_by('-created_at')

            # Performance metrics
            total_requests = PaymentRequest.objects.count()
            approved_today = PaymentRequest.objects.filter(
                status='approved',
                reviewed_at__date=timezone.now().date()
            ).count()

            total_earnings = sum(trip.actual_cost or 0 for trip in completed_trips)
            avg_trip_cost = total_earnings / completed_trips.count() if completed_trips.count() > 0 else 0

            # Driver performance analytics
            driver_performance = []
            for driver in all_drivers[:10]:  # Top 10 drivers for performance view
                driver_trips = Trip.objects.filter(driver=driver)
                driver_earnings = sum(trip.actual_cost or 0 for trip in driver_trips.filter(status='completed'))
                pending_payment_count = PaymentRequest.objects.filter(driver=driver, status='pending').count()
                last_trip = driver_trips.first()

                driver_performance.append({
                    'driver': driver,
                    'total_trips': driver_trips.count(),
                    'completed_trips': driver_trips.filter(status='completed').count(),
                    'earnings': driver_earnings,
                    'pending_requests': pending_payment_count,
                    'last_trip': last_trip,
                    'efficiency_score': round((driver_trips.filter(status='completed').count() / max(driver_trips.count(), 1)) * 100, 1)
                })

            # Recent activity feed
            recent_activities = []

            # Recent trips
            for trip in all_trips[:5]:
                recent_activities.append({
                    'type': 'trip',
                    'description': f"Trip from {trip.origin} to {trip.destination}",
                    'status': trip.status,
                    'driver': trip.driver.user.get_full_name() if trip.driver else 'Unassigned',
                    'timestamp': trip.created_at,
                    'amount': trip.actual_cost or trip.estimated_cost
                })

            # Recent payment requests
            for payment_req in pending_requests[:5]:
                recent_activities.append({
                    'type': 'payment_request',
                    'description': f"{payment_req.type.title()} request by {payment_req.driver.user.get_full_name()}",
                    'status': payment_req.status,
                    'driver': payment_req.driver.user.get_full_name(),
                    'timestamp': payment_req.requested_at,
                    'amount': payment_req.amount
                })

            # Sort activities by timestamp
            recent_activities.sort(key=lambda x: x['timestamp'], reverse=True)

            context = {
                'user': request.user,
                'all_drivers': all_drivers,
                'driver_performance': driver_performance,
                'all_trips': all_trips[:20],  # Recent 20 trips
                'completed_trips_count': completed_trips.count(),
                'in_progress_trips_count': in_progress_trips.count(),
                'pending_trips_count': pending_trips.count(),
                'pending_requests': pending_requests,
                'approved_requests': approved_requests,
                'rejected_requests': rejected_requests,
                'job_postings': job_postings,
                'total_requests': total_requests,
                'approved_today': approved_today,
                'total_earnings': total_earnings,
                'avg_trip_cost': avg_trip_cost,
                'recent_activities': recent_activities[:15],
                'fleet_utilization': round((in_progress_trips.count() / max(all_trips.count(), 1)) * 100, 1)
            }

            return render(request, 'fleet/supervisor_dashboard.html', context)

        @login_required
        @csrf_exempt
        def supervisor_approve_request(request, request_id):
            if request.user.role != 'supervisor':
                return JsonResponse({'error': 'Unauthorized'}, status=403)

            try:
                payment_request = PaymentRequest.objects.get(id=request_id)

                if request.method == 'POST':
                    data = json.loads(request.body)
                    action = data.get('action')  # 'approve' or 'reject'
                    comments = data.get('comments', '')

                    if action == 'approve':
                        # Supervisor approval - mark as needing admin approval
                        payment_request.status = 'supervisor_approved'
                        payment_request.review_comments = f"Supervisor approved: {comments}\n\nForwarded to admin for final approval."
                        message = 'Request approved and forwarded to admin for final approval'
                    elif action == 'reject':
                        # Supervisor rejection - final
                        payment_request.status = 'rejected'
                        payment_request.review_comments = f"Supervisor rejected: {comments}"
                        message = 'Request rejected'
                    else:
                        return JsonResponse({'error': 'Invalid action'}, status=400)

                    payment_request.reviewed_by = request.user
                    payment_request.reviewed_at = timezone.now()
                    payment_request.save()

                    return JsonResponse({'success': True, 'message': message})

                return JsonResponse({'error': 'Method not allowed'}, status=405)

            except PaymentRequest.DoesNotExist:
                return JsonResponse({'error': 'Request not found'}, status=404)
            except Exception as e:
                return JsonResponse({'error': str(e)}, status=500)

        @login_required
        @csrf_exempt  
        def get_driver_location(request, driver_id):
            if request.user.role not in ['supervisor', 'admin', 'fleet_owner']:
                return JsonResponse({'error': 'Unauthorized'}, status=403)

            try:
                driver = Driver.objects.get(id=driver_id)

                # Get current location from driver's current_location field
                if driver.current_location:
                    return JsonResponse({
                        'success': True,
                        'location': driver.current_location,
                        'driver_name': driver.user.get_full_name(),
                        'last_updated': driver.updated_at.isoformat()
                    })
                else:
                    return JsonResponse({
                        'success': False,
                        'message': 'No location data available for this driver'
                    })

            except Driver.DoesNotExist:
                return JsonResponse({'error': 'Driver not found'}, status=404)
            except Exception as e:
                return JsonResponse({'error': str(e)}, status=500)

        @login_required
        @csrf_exempt
        def update_driver_location(request, driver_id):
            """Allow drivers to update their current location"""
            try:
                driver = Driver.objects.get(id=driver_id, user=request.user)

                if request.method == 'POST':
                    data = json.loads(request.body)
                    latitude = data.get('latitude')
                    longitude = data.get('longitude')

                    if latitude and longitude:
                        driver.current_location = {
                            'latitude': float(latitude),
                            'longitude': float(longitude),
                            'timestamp': timezone.now().isoformat()
                        }
                        driver.save()

                        return JsonResponse({'success': True, 'message': 'Location updated successfully'})

                return JsonResponse({'error': 'Invalid location data'}, status=400)

            except Driver.DoesNotExist:
                return JsonResponse({'error': 'Driver not found'}, status=404)
            except Exception as e:
                return JsonResponse({'error': str(e)}, status=500)

        @login_required
        def get_ola_maps_config(request):
            """Provide Ola Maps configuration for the frontend"""
            if request.user.role not in ['supervisor', 'admin', 'fleet_owner']:
                return JsonResponse({'error': 'Unauthorized'}, status=403)

            try:
                import os
                api_key = os.environ.get('OLA_MAPS_API_KEY')

                if not api_key:
                    return JsonResponse({
                        'error': 'Ola Maps API key not configured',
                        'fallback': True
                    }, status=400)

                return JsonResponse({
                    'success': True,
                    'api_key': api_key,
                    'map_style': 'https://api.olamaps.io/tiles/vector/v1/styles/default-light-standard/style.json',
                    'fallback': False
                })

            except Exception as e:
                return JsonResponse({
                    'error': str(e),
                    'fallback': True
                }, status=500)

        # Admin Dashboard Views
        @login_required
        def admin_dashboard(request):
            """Admin dashboard with full system access"""
            if request.user.role != 'admin':
                messages.error(request, 'Access denied. Admin privileges required.')
                return redirect('dashboard')

            # Get all system data for admin view
            all_users = User.objects.all().order_by('-date_joined')
            total_users = all_users.count()
            active_users = all_users.filter(is_active=True).count()
            total_trips = Trip.objects.count()
            pending_requests = PaymentRequest.objects.filter(status='pending').count()

            # User role distribution
            role_counts = all_users.values('role').annotate(count=Count('role'))
            role_data = {item['role']: item['count'] for item in role_counts}

            context = {
                'all_users': all_users,
                'total_users': total_users,
                'active_users': active_users,
                'total_trips': total_trips,
                'pending_requests': pending_requests,
                'role_counts': role_data,
            }

            return render(request, 'fleet/admin_dashboard.html', context)

        @login_required
        @csrf_exempt
        def admin_reset_password(request):
            """Admin password reset functionality"""
            if request.user.role != 'admin':
                return JsonResponse({'error': 'Access denied'}, status=403)

            if request.method == 'POST':
                try:
                    data = json.loads(request.body)
                    user_id = data.get('user_id')
                    new_password = data.get('new_password')

                    if not user_id or not new_password:
                        return JsonResponse({'error': 'Missing required fields'}, status=400)

                    if len(new_password) < 6:
                        return JsonResponse({'error': 'Password must be at least 6 characters'}, status=400)

                    target_user = User.objects.get(id=user_id)
                    target_user.set_password(new_password)
                    target_user.save()

                    return JsonResponse({
                        'success': True,
                        'message': f'Password reset for {target_user.username}',
                        'username': target_user.username
                    })

                except User.DoesNotExist:
                    return JsonResponse({'error': 'User not found'}, status=404)
                except Exception as e:
                    return JsonResponse({'error': str(e)}, status=500)

            return JsonResponse({'error': 'Invalid request method'}, status=405)

        @login_required
        def admin_get_user(request, user_id):
            """Get user details for editing"""
            if request.user.role != 'admin':
                return JsonResponse({'error': 'Access denied'}, status=403)

            try:
                user = User.objects.get(id=user_id)
                return JsonResponse({
                    'id': user.id,
                    'username': user.username,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'email': user.email,
                    'role': user.role,
                    'is_active': user.is_active,
                    'is_staff': user.is_staff,
                    'is_superuser': user.is_superuser,
                    'last_login': user.last_login.isoformat() if user.last_login else None,
                    'date_joined': user.date_joined.isoformat()
                })
            except User.DoesNotExist:
                return JsonResponse({'error': 'User not found'}, status=404)

        @login_required
        @csrf_exempt
        def admin_update_user(request):
            """Update user information"""
            if request.user.role != 'admin':
                return JsonResponse({'error': 'Access denied'}, status=403)

            if request.method == 'POST':
                try:
                    data = json.loads(request.body)
                    user_id = data.get('user_id')

                    user = User.objects.get(id=user_id)

                    # Update user fields
                    user.username = data.get('username', user.username)
                    user.first_name = data.get('first_name', user.first_name)
                    user.last_name = data.get('last_name', user.last_name)
                    user.email = data.get('email', user.email)
                    user.role = data.get('role', user.role)
                    user.is_active = data.get('is_active', user.is_active)

                    user.save()

                    return JsonResponse({
                        'success': True,
                        'message': f'User {user.username} updated successfully'
                    })

                except User.DoesNotExist:
                    return JsonResponse({'error': 'User not found'}, status=404)
                except Exception as e:
                    return JsonResponse({'error': str(e)}, status=500)

            return JsonResponse({'error': 'Invalid request method'}, status=405)

        @login_required
        @csrf_exempt
        def admin_toggle_user_status(request):
            """Toggle user active status"""
            if request.user.role != 'admin':
                return JsonResponse({'error': 'Access denied'}, status=403)

            if request.method == 'POST':
                try:
                    data = json.loads(request.body)
                    user_id = data.get('user_id')

                    user = User.objects.get(id=user_id)

                    # Prevent admin from deactivating themselves
                    if user.id == request.user.id:
                        return JsonResponse({'error': 'Cannot modify your own account'}, status=400)

                    user.is_active = not user.is_active
                    user.save()

                    status_text = 'activated' if user.is_active else 'deactivated'

                    return JsonResponse({
                        'success': True,
                        'status': status_text,
                        'message': f'User {user.username} {status_text}'
                    })

                except User.DoesNotExist:
                    return JsonResponse({'error': 'User not found'}, status=404)
                except Exception as e:
                    return JsonResponse({'error': str(e)}, status=500)

            return JsonResponse({'error': 'Invalid request method'}, status=405)

        @api_view(['GET', 'POST'])
        @csrf_exempt
        def pricing_calculator(request):
            if request.method == 'GET':
                # Return pricing calculator form or default response for GET requests
                return JsonResponse({
                    'message': 'Pricing Calculator API',
                    'usage': 'Send POST request with distance, fuel_cost_per_km, driver_cost_per_km, and double_driver fields',
                    'truck_rates': {
                        '6_tyre_open': {'single': 26.50, 'double': 33.08},
                        '10_tyre_open': {'single': 32.89, 'double': 39.96},
                        '18_tyre_trailer': {'single': 57.40, 'double': 70.18},
                        '22_tyre_trailer': {'single': 62.10, 'double': 74.88}
                    }
                })

            try:
                data = json.loads(request.body)
                distance = Decimal(str(data.get('distance', 0)))
                fuel_cost_per_km = Decimal(str(data.get('fuel_cost_per_km', 8)))
                driver_cost_per_km = Decimal(str(data.get('driver_cost_per_km', 5)))
                double_driver = data.get('double_driver', False)

                # Apply 80% increase for double driver
                if double_driver:
                    driver_cost_per_km *= Decimal('1.8')

                # Base calculation: (fuel_cost + driver_cost + en_route_expenses) * 1.15
                en_route_expenses = Decimal('2')  # Default en-route expenses per km
                base_cost = (fuel_cost_per_km + driver_cost_per_km + en_route_expenses) * distance
                total_cost = base_cost * Decimal('1.15')  # 15% markup

                return JsonResponse({
                    'distance': float(distance),
                    'base_cost': float(base_cost),
                    'total_cost': float(total_cost),
                    'cost_per_km': float(total_cost / distance) if distance > 0 else 0,
                })

            except Exception as e:
                return JsonResponse({'error': str(e)}, status=400)

        @api_view(['GET'])
        @login_required
        def analytics_view(request):
            user = request.user

            if hasattr(user, 'fleet_owner'):
                fleet_owner = user.fleet_owner
                total_vehicles = fleet_owner.vehicles.count()
                active_vehicles = fleet_owner.vehicles.filter(status='active').count()
                utilization = (active_vehicles / total_vehicles * 100) if total_vehicles > 0 else 0

                analytics_data = {
                    'fleet_utilization': round(utilization, 2),
                    'total_vehicles': total_vehicles,
                    'active_vehicles': active_vehicles,
                    'total_trips': fleet_owner.trips.count(),
                    'completed_trips': fleet_owner.trips.filter(status='completed').count(),
                    'pending_requests': PaymentRequest.objects.filter(
                        driver__fleet_owner=fleet_owner,
                        status='pending'
                    ).count(),
                }
            else:
                analytics_data = {
                    'fleet_utilization': 0,
                    'total_vehicles': 0,
                    'active_vehicles': 0,
                    'total_trips': 0,
                    'completed_trips': 0,
                    'pending_requests': 0,
                }

            return Response(analytics_data)

        @api_view(['POST'])
        @login_required
        def submit_payment_request(request):
            if request.user.role != 'driver':
                return Response({'error': 'Only drivers can submit payment requests'}, status=403)

            driver = get_object_or_404(Driver, user=request.user)

            try:
                payment_request = PaymentRequest.objects.create(
                    driver=driver,
                    amount=request.data.get('amount'),
                    type=request.data.get('type'),
                    description=request.data.get('description'),
                    receipt_url=request.data.get('receipt_url', ''),
                )

                return Response({
                    'id': payment_request.id,
                    'message': 'Payment request submitted successfully'
                }, status=201)

            except Exception as e:
                return Response({'error': str(e)}, status=400)

        @api_view(['PATCH'])
        @login_required
        def review_payment_request(request, request_id):
            if request.user.role != 'supervisor':
                return Response({'error': 'Only supervisors can review payment requests'}, status=403)

            payment_request = get_object_or_404(PaymentRequest, id=request_id)

            try:
                payment_request.status = request.data.get('status')
                payment_request.review_comments = request.data.get('review_comments', '')
                payment_request.reviewed_by = request.user
                payment_request.reviewed_at = timezone.now()
                payment_request.save()

                return Response({'message': 'Payment request reviewed successfully'})

            except Exception as e:
                return Response({'error': str(e)}, status=400)

        @api_view(['POST'])
        @login_required
        def start_trip(request, trip_id):
            if request.user.role != 'driver':
                return Response({'error': 'Only drivers can start trips'}, status=403)

            driver = get_object_or_404(Driver, user=request.user)
            trip = get_object_or_404(Trip, id=trip_id, driver=driver)

            if trip.status != 'pending':
                return Response({'error': 'Trip cannot be started'}, status=400)

            trip.status = 'in_progress'
            trip.start_time = timezone.now()
            trip.save()

            return Response({'message': 'Trip started successfully'})

        @api_view(['POST'])
        @login_required
        def complete_trip(request, trip_id):
            if request.user.role != 'driver':
                return Response({'error': 'Only drivers can complete trips'}, status=403)

            driver = get_object_or_404(Driver, user=request.user)
            trip = get_object_or_404(Trip, id=trip_id, driver=driver)

            if trip.status != 'in_progress':
                return Response({'error': 'Trip cannot be completed'}, status=400)

            trip.status = 'completed'
            trip.end_time = timezone.now()
            trip.actual_cost = request.data.get('actual_cost', trip.estimated_cost)
            trip.save()

            return Response({'message': 'Trip completed successfully'})

        # ViewSets for API
        class VehicleViewSet(viewsets.ModelViewSet):
            serializer_class = VehicleSerializer
            permission_classes = [IsAuthenticated]

            def get_queryset(self):
                if hasattr(self.request.user, 'fleet_owner'):
                    return self.request.user.fleet_owner.vehicles.all()
                return Vehicle.objects.none()

        class DriverViewSet(viewsets.ModelViewSet):
            serializer_class = DriverSerializer
            permission_classes = [IsAuthenticated]

            def get_queryset(self):
                if hasattr(self.request.user, 'fleet_owner'):
                    return self.request.user.fleet_owner.drivers.all()
                return Driver.objects.none()

        class TripViewSet(viewsets.ModelViewSet):

            serializer_class = TripSerializer
            permission_classes = [IsAuthenticated]

            def get_queryset(self):
                user = self.request.user
                print(f"User: {user}, Authenticated: {user.is_authenticated}")
                if hasattr(self.request.user, 'fleet_owner'):
                    return self.request.user.fleet_owner.trips.all()
                elif hasattr(self.request.user, 'driver'):
                    return self.request.user.driver.trips.all()
                elif hasattr(self.request.user, "admin"):
                    return self.request.user.admin.trips.all()
                return Trip.objects.none()

        class PaymentRequestViewSet(viewsets.ModelViewSet):
            serializer_class = PaymentRequestSerializer
            permission_classes = [IsAuthenticated]

            def get_queryset(self):
                if self.request.user.role == 'supervisor':
                    return PaymentRequest.objects.all()
                elif hasattr(self.request.user, 'driver'):
                    return self.request.user.driver.payment_requests.all()
                elif hasattr(self.request.user, 'fleet_owner'):
                    return PaymentRequest.objects.filter(driver__fleet_owner=self.request.user.fleet_owner)
                return PaymentRequest.objects.none()

        class JobPostingViewSet(viewsets.ModelViewSet):
            serializer_class = JobPostingSerializer
            permission_classes = [IsAuthenticated]

            def get_queryset(self):
                if self.request.user.role == 'driver':
                    return JobPosting.objects.filter(status='available')
                elif hasattr(self.request.user, 'fleet_owner'):
                    return self.request.user.fleet_owner.job_postings.all()
                return JobPosting.objects.none()

        class CustomPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
            success_url = reverse_lazy('dashboard')
            template_name = 'fleet/base_password_change.html'  # We'll handle this in base.html directly

            def form_invalid(self, form):
                response = super().form_invalid(form)
                if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'errors': form.errors}, status=400)
                return response

            def form_valid(self, form):
                response = super().form_valid(form)
                if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'success': True})
                return response