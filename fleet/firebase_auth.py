"""
Firebase Authentication Integration for DriveNowKM
Handles Firebase ID token verification and user synchronization
"""

import json
import requests
import firebase_admin
from django.http import JsonResponse
from firebase_admin import auth as firebase_auth
from firebase_admin import credentials, auth, initialize_app
from django.conf import settings
from django.contrib.auth import login
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from .models import User, FleetOwner, Driver


@csrf_exempt
@require_http_methods(["POST"])
def firebase_login(request):
    """
    Handle Firebase authentication and sync user with Django backend
    """
    try:
        data = json.loads(request.body)
        id_token = data.get('id_token')
        role_from_client = data.get('role', 'fleet_owner')  # Optional: Default role if first time

        if not id_token:
            return JsonResponse({'error': 'Missing Firebase ID token'}, status=400)

        # Verify token securely with Firebase Admin SDK
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token.get('uid')
        email = decoded_token.get('email')
        display_name = decoded_token.get('name', '')
        photo_url = decoded_token.get('picture')

        if not uid or not email:
            return JsonResponse({'error': 'Invalid token payload'}, status=400)

        # Split display name into first & last name
        name_parts = display_name.split(' ')
        first_name = name_parts[0]
        last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''

        # Check if user exists, else create
        user, created = User.objects.get_or_create(
            username=uid,
            defaults={
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
                'role': role_from_client,
                'is_active': True,
            }
        )

        # Update user info if user already exists
        if not created:
            user.email = email
            user.first_name = first_name
            user.last_name = last_name
            user.save()

        profile_data = {}

        if created:
            # Only create profiles on first registration
            if role_from_client == 'fleet_owner':
                fleet_owner = FleetOwner.objects.create(
                    user=user,
                    company_name=f"{user.first_name}'s Fleet"
                )
                profile_data['fleet_owner_id'] = fleet_owner.id

            elif role_from_client == 'driver':
                driver = Driver.objects.create(
                    user=user,
                    license_number='',
                    vehicle_number=''
                )
                profile_data['driver_id'] = driver.id

        # Log user into Django session
        login(request, user)

        return JsonResponse({
            'success': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'role': user.role,
                **profile_data,
            }
        })

    except auth.InvalidIdTokenError:
        return JsonResponse({'error': 'Invalid Firebase ID token'}, status=401)
    except auth.ExpiredIdTokenError:
        return JsonResponse({'error': 'Expired Firebase ID token'}, status=401)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def firebase_logout(request):
    """
    Handle logout request
    """
    from django.contrib.auth import logout
    logout(request)
    return JsonResponse({'success': True})

@login_required
def get_user_profile(request):
    """
    Get current user profile information
    """
    user = request.user
    fleet_owner = getattr(user, 'fleet_owner', None)
    
    return JsonResponse({
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'role': user.role,
            'fleet_owner_id': fleet_owner.id if fleet_owner else None,
            'company_name': fleet_owner.company_name if fleet_owner else None,
            'km_balance': float(fleet_owner.km_balance) if fleet_owner else 0.0,
            'prepaid_balance': float(fleet_owner.prepaid_balance) if fleet_owner else 0.0,
        }
    })