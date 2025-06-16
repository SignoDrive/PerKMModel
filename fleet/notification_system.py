"""
Fleet Management Notification System
Handles real-time notifications for fleet owners, supervisors, and drivers
"""

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from fleet.models import User, FleetOwner, Driver, Trip, JobPosting, Notification
import json


class NotificationService:
    """Service class for handling notification creation and delivery"""
    
    @staticmethod
    def notify_trip_created(trip, created_by):
        """Notify supervisors when a new trip is created"""
        supervisors = User.objects.filter(role='supervisor', is_active=True)
        
        for supervisor in supervisors:
            Notification.objects.create(
                recipient=supervisor,
                sender=created_by,
                title="New Trip Created",
                message=f"A new trip from {trip.origin} to {trip.destination} has been created and requires assignment.",
                notification_type='trip_created',
                priority='medium',
                trip=trip,
                action_data={
                    'trip_id': trip.id,
                    'action': 'assign_trip',
                    'origin': trip.origin,
                    'destination': trip.destination,
                    'estimated_cost': str(trip.estimated_cost) if trip.estimated_cost else None
                }
            )
    
    @staticmethod
    def notify_job_posted(job_posting, created_by):
        """Notify all drivers when a job is posted"""
        # Get all active drivers
        drivers = Driver.objects.filter(is_active=True)
        
        for driver in drivers:
            Notification.objects.create(
                recipient=driver.user,
                sender=created_by,
                title="New Job Available",
                message=f"New driving job: {job_posting.title} - {job_posting.origin} to {job_posting.destination}",
                notification_type='job_posted',
                priority='medium',
                job_posting=job_posting,
                action_data={
                    'job_id': job_posting.id,
                    'action': 'apply_job',
                    'title': job_posting.title,
                    'origin': job_posting.origin,
                    'destination': job_posting.destination,
                    'estimated_cost': str(job_posting.estimated_cost) if job_posting.estimated_cost else None
                }
            )
    
    @staticmethod
    def notify_job_application(job_posting, driver, supervisor):
        """Notify supervisor when a driver applies for a job"""
        Notification.objects.create(
            recipient=supervisor,
            sender=driver.user,
            title="Job Application Received",
            message=f"Driver {driver.user.first_name} {driver.user.last_name} has applied for job: {job_posting.title}",
            notification_type='job_application',
            priority='high',
            job_posting=job_posting,
            action_data={
                'job_id': job_posting.id,
                'driver_id': driver.id,
                'action': 'review_application',
                'driver_name': f"{driver.user.first_name} {driver.user.last_name}",
                'driver_license': driver.license_number,
                'driver_experience': getattr(driver, 'experience_years', 'N/A')
            }
        )
    
    @staticmethod
    def notify_driver_assigned(trip, driver, assigned_by, fleet_owner):
        """Notify fleet owner when supervisor assigns a driver to trip"""
        Notification.objects.create(
            recipient=fleet_owner.user,
            sender=assigned_by,
            title="Driver Assigned to Trip",
            message=f"Driver {driver.user.first_name} {driver.user.last_name} has been assigned to trip {trip.origin} → {trip.destination}",
            notification_type='driver_assigned',
            priority='medium',
            trip=trip,
            action_data={
                'trip_id': trip.id,
                'driver_id': driver.id,
                'driver_name': f"{driver.user.first_name} {driver.user.last_name}",
                'driver_license': driver.license_number,
                'action': 'view_assignment'
            }
        )
        
        # Also notify the driver about the assignment
        Notification.objects.create(
            recipient=driver.user,
            sender=assigned_by,
            title="Trip Assignment",
            message=f"You have been assigned to a trip from {trip.origin} to {trip.destination}",
            notification_type='trip_assigned',
            priority='high',
            trip=trip,
            action_data={
                'trip_id': trip.id,
                'action': 'view_trip_details',
                'origin': trip.origin,
                'destination': trip.destination,
                'estimated_cost': str(trip.estimated_cost) if trip.estimated_cost else None
            }
        )
    
    @staticmethod
    def notify_trip_status_change(trip, new_status, changed_by):
        """Notify relevant users when trip status changes"""
        recipients = []
        
        # Add fleet owner
        if trip.fleet_owner:
            recipients.append(trip.fleet_owner.user)
        
        # Add assigned driver
        if trip.driver:
            recipients.append(trip.driver.user)
        
        # Add supervisors
        supervisors = User.objects.filter(role='supervisor', is_active=True)
        recipients.extend(supervisors)
        
        status_messages = {
            'in_progress': 'Trip has started',
            'completed': 'Trip has been completed',
            'cancelled': 'Trip has been cancelled'
        }
        
        message = status_messages.get(new_status, f'Trip status changed to {new_status}')
        
        for recipient in recipients:
            if recipient != changed_by:  # Don't notify the person who made the change
                Notification.objects.create(
                    recipient=recipient,
                    sender=changed_by,
                    title=f"Trip Status Update",
                    message=f"{message}: {trip.origin} → {trip.destination}",
                    notification_type='trip_started' if new_status == 'in_progress' else 'trip_completed',
                    priority='medium',
                    trip=trip,
                    action_data={
                        'trip_id': trip.id,
                        'status': new_status,
                        'action': 'view_trip'
                    }
                )


@login_required
@csrf_exempt
def get_notifications(request):
    """Get notifications for the current user"""
    notifications = Notification.objects.filter(recipient=request.user)[:20]
    
    notifications_data = []
    for notification in notifications:
        notifications_data.append({
            'id': notification.id,
            'title': notification.title,
            'message': notification.message,
            'type': notification.notification_type,
            'priority': notification.priority,
            'is_read': notification.is_read,
            'created_at': notification.created_at.isoformat(),
            'action_data': notification.action_data,
            'sender': {
                'name': f"{notification.sender.first_name} {notification.sender.last_name}" if notification.sender else 'System',
                'role': notification.sender.role if notification.sender else 'system'
            }
        })
    
    unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    
    return JsonResponse({
        'notifications': notifications_data,
        'unread_count': unread_count
    })


@login_required
def mark_notification_read(request, notification_id):
    """Mark a specific notification as read"""
    try:
        notification = Notification.objects.get(id=notification_id, recipient=request.user)
        notification.mark_as_read()
        return JsonResponse({'success': True})
    except Notification.DoesNotExist:
        return JsonResponse({'error': 'Notification not found'}, status=404)


@login_required
def mark_all_notifications_read(request):
    """Mark all notifications as read for the current user"""
    Notification.objects.filter(recipient=request.user, is_read=False).update(
        is_read=True,
        read_at=timezone.now()
    )
    return JsonResponse({'success': True})


@csrf_exempt
@login_required
def handle_notification_action(request):
    """Handle actions from notifications (like assigning trips, applying for jobs)"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        action = data.get('action')
        notification_id = data.get('notification_id')
        
        # Get the notification
        notification = Notification.objects.get(id=notification_id, recipient=request.user)
        
        if action == 'assign_trip' and request.user.role == 'supervisor':
            # Create job posting for the trip
            trip = notification.trip
            job_posting = JobPosting.objects.create(
                fleet_owner=trip.fleet_owner,
                title=f"Drive from {trip.origin} to {trip.destination}",
                origin=trip.origin,
                destination=trip.destination,
                distance=trip.distance,
                estimated_cost=trip.estimated_cost,
                requirements="Valid driving license required",
                expires_at=timezone.now() + timezone.timedelta(days=3)
            )
            
            # Notify all drivers about the new job posting
            NotificationService.notify_job_posted(job_posting, request.user)
            
            # Mark notification as read
            notification.mark_as_read()
            
            return JsonResponse({
                'success': True,
                'message': 'Job posting created and drivers notified',
                'job_id': job_posting.id
            })
        
        elif action == 'apply_job' and request.user.role == 'driver':
            # Driver applying for a job
            job_posting = notification.job_posting
            driver = Driver.objects.get(user=request.user)
            
            # Find an available supervisor
            supervisor = User.objects.filter(role='supervisor', is_active=True).first()
            
            if supervisor:
                # Notify supervisor about the application
                NotificationService.notify_job_application(job_posting, driver, supervisor)
                
                # Mark notification as read
                notification.mark_as_read()
                
                return JsonResponse({
                    'success': True,
                    'message': 'Job application submitted to supervisor'
                })
            else:
                return JsonResponse({'error': 'No supervisor available'}, status=400)
        
        elif action == 'review_application' and request.user.role == 'supervisor':
            # Supervisor reviewing driver application
            action_data = notification.action_data
            driver_id = action_data.get('driver_id')
            job_posting = notification.job_posting
            
            # For now, auto-approve the application
            driver = Driver.objects.get(id=driver_id)
            
            # Find the related trip and assign the driver
            trip = Trip.objects.filter(
                origin=job_posting.origin,
                destination=job_posting.destination,
                status='pending'
            ).first()
            
            if trip:
                trip.driver = driver
                trip.status = 'assigned'
                trip.save()
                
                # Notify fleet owner about the assignment
                NotificationService.notify_driver_assigned(trip, driver, request.user, trip.fleet_owner)
                
                # Mark job as assigned
                job_posting.status = 'assigned'
                job_posting.save()
                
                # Mark notification as read
                notification.mark_as_read()
                
                return JsonResponse({
                    'success': True,
                    'message': 'Driver assigned to trip successfully'
                })
            else:
                return JsonResponse({'error': 'Related trip not found'}, status=400)
        
        else:
            return JsonResponse({'error': 'Invalid action or insufficient permissions'}, status=400)
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)