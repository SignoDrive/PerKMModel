import json
import requests
import os
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import Trip, FleetOwner, Driver, Vehicle, User
from .distance_calculator import get_truck_rates
from .notification_system import NotificationService
from decimal import Decimal

@csrf_exempt
@login_required
def create_trip(request):
    """
    Create a new trip with automatic distance calculation using Ola Maps API
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            origin = data.get('origin')
            destination = data.get('destination')
            truck_type = data.get('truck_type')
            driver_type = data.get('driver_type')
            primary_driver_id = data.get('primary_driver_id')
            secondary_driver_id = data.get('secondary_driver_id')
            supervisor_id = data.get('supervisor_id')
            vehicle_id = data.get('vehicle_id')
            
            # Check if distance and cost are provided (from price calculator)
            distance = data.get('distance')
            estimated_cost = data.get('estimated_cost')
            
            if not all([origin, destination, truck_type, driver_type]):
                return JsonResponse({'error': 'Missing required fields'}, status=400)
            
            # Get fleet owner
            fleet_owner, created = FleetOwner.objects.get_or_create(user=request.user)
            
            # If distance and cost are provided, use them directly (from price calculator)
            if distance and estimated_cost:
                try:
                    distance_km = float(distance)
                    final_cost = float(estimated_cost)
                    
                    # Create trip with provided data
                    trip = Trip.objects.create(
                        fleet_owner=fleet_owner,
                        origin=origin,
                        destination=destination,
                        distance=Decimal(str(distance_km)),
                        estimated_cost=Decimal(str(final_cost)),
                        status='pending'
                    )
                    
                    return JsonResponse({
                        'success': True,
                        'trip_id': trip.id,
                        'message': 'Trip created successfully'
                    })
                    
                except (ValueError, TypeError) as e:
                    return JsonResponse({'error': 'Invalid distance or cost values'}, status=400)
            
            # Get Ola Maps API key
            api_key = os.getenv('OLA_MAPS_API_KEY')
            if not api_key:
                return JsonResponse({'error': 'Ola Maps API key not configured'}, status=500)
            
            # Calculate distance using Ola Maps API
            try:
                # Geocode origin
                origin_url = f"https://api.olamaps.io/places/v1/geocode?address={origin}&language=en&api_key={api_key}"
                origin_response = requests.get(origin_url)
                
                if origin_response.status_code != 200:
                    return JsonResponse({'error': 'Failed to geocode origin address'}, status=400)
                
                origin_data = origin_response.json()
                if not origin_data.get('geocodingResults'):
                    return JsonResponse({'error': 'Origin address not found'}, status=400)
                    
                origin_lat = origin_data["geocodingResults"][0]["geometry"]["location"]["lat"]
                origin_lng = origin_data["geocodingResults"][0]["geometry"]["location"]["lng"]
                
                # Geocode destination
                destination_url = f"https://api.olamaps.io/places/v1/geocode?address={destination}&language=en&api_key={api_key}"
                destination_response = requests.get(destination_url)
                
                if destination_response.status_code != 200:
                    return JsonResponse({'error': 'Failed to geocode destination address'}, status=400)
                
                destination_data = destination_response.json()
                if not destination_data.get('geocodingResults'):
                    return JsonResponse({'error': 'Destination address not found'}, status=400)
                    
                destination_lat = destination_data["geocodingResults"][0]["geometry"]["location"]["lat"]
                destination_lng = destination_data["geocodingResults"][0]["geometry"]["location"]["lng"]
                
                # Calculate distance
                distance_url = f"https://api.olamaps.io/routing/v1/distanceMatrix/basic?origins={origin_lat},{origin_lng}&destinations={destination_lat},{destination_lng}&api_key={api_key}"
                distance_response = requests.get(distance_url)
                
                if distance_response.status_code != 200:
                    return JsonResponse({'error': 'Failed to calculate distance'}, status=400)
                
                distance_data = distance_response.json()
                if not distance_data.get('rows') or not distance_data['rows'][0].get('elements'):
                    return JsonResponse({'error': 'Distance calculation failed'}, status=400)
                    
                distance_meters = distance_data["rows"][0]["elements"][0]["distance"]
                distance_km = int(round((distance_meters / 1000.0) + 50, 0))
                
            except Exception as e:
                return JsonResponse({'error': f'Distance calculation failed: {str(e)}'}, status=400)
            
            # Get pricing information
            truck_rates = get_truck_rates()
            if truck_type not in truck_rates:
                return JsonResponse({'error': 'Invalid truck type'}, status=400)
            
            truck_info = truck_rates[truck_type]
            
            if driver_type == 'single':
                rate_per_km = truck_info['rate_single']
            elif driver_type == 'double':
                rate_per_km = truck_info['rate_double']
            else:
                return JsonResponse({'error': 'Invalid driver type'}, status=400)
            
            estimated_cost = Decimal(str(distance_km)) * Decimal(str(rate_per_km))
            
            # Get primary driver, secondary driver, supervisor, and vehicle if provided
            primary_driver = None
            secondary_driver = None
            supervisor = None
            vehicle = None
            
            if primary_driver_id:
                try:
                    primary_driver = Driver.objects.get(id=primary_driver_id, fleet_owner=fleet_owner)
                except Driver.DoesNotExist:
                    return JsonResponse({'error': 'Primary driver not found'}, status=400)
            
            if secondary_driver_id:
                try:
                    secondary_driver = Driver.objects.get(id=secondary_driver_id, fleet_owner=fleet_owner)
                except Driver.DoesNotExist:
                    return JsonResponse({'error': 'Secondary driver not found'}, status=400)
            
            if supervisor_id:
                try:
                    from fleet.models import User
                    supervisor = User.objects.get(id=supervisor_id, role='supervisor', is_active=True)
                except User.DoesNotExist:
                    return JsonResponse({'error': 'Supervisor not found'}, status=400)
            
            if vehicle_id:
                try:
                    vehicle = Vehicle.objects.get(id=vehicle_id, fleet_owner=fleet_owner)
                except Vehicle.DoesNotExist:
                    return JsonResponse({'error': 'Vehicle not found'}, status=400)
            
            # Create the trip with primary driver (for backward compatibility)
            trip = Trip.objects.create(
                fleet_owner=fleet_owner,
                driver=primary_driver,  # Use primary driver as the main driver
                vehicle=vehicle,
                origin=origin,
                destination=destination,
                distance=distance_km,
                estimated_cost=estimated_cost,
                status='pending'
            )
            
            # Send notification to supervisors about the new trip
            from fleet.notification_system import NotificationService
            NotificationService.notify_trip_created(trip, request.user)
            
            response_data = {
                'success': True,
                'trip_id': trip.id,
                'origin': origin,
                'destination': destination,
                'distance_km': distance_km,
                'truck_type': truck_type,
                'driver_type': driver_type,
                'rate_per_km': float(rate_per_km),
                'estimated_cost': float(estimated_cost),
                'coordinates': {
                    'origin': {'lat': origin_lat, 'lng': origin_lng},
                    'destination': {'lat': destination_lat, 'lng': destination_lng}
                },
                'truck_specs': {
                    'name': truck_info['name'],
                    'gross_weight': truck_info['gw'],
                    'net_weight': truck_info['net']
                }
            }
            
            return JsonResponse(response_data)
            
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        except Exception as e:
            return JsonResponse({'error': f'Internal server error: {str(e)}'}, status=500)
    
    elif request.method == 'GET':
        # Return trip creation form data including drivers, supervisors, and vehicles
        fleet_owner, created = FleetOwner.objects.get_or_create(user=request.user)
        drivers = fleet_owner.drivers.filter(is_active=True)
        vehicles = fleet_owner.vehicles.filter(status='active')
        
        # Get supervisors (users with supervisor role)
        from fleet.models import User
        supervisors = User.objects.filter(role='supervisor', is_active=True)
        
        truck_rates = get_truck_rates()
        
        return JsonResponse({
            'drivers': [{
                'id': d.id, 
                'user': {
                    'first_name': d.user.first_name or '',
                    'last_name': d.user.last_name or ''
                },
                'license_number': d.license_number or ''
            } for d in drivers],
            'supervisors': [{
                'id': s.id,
                'first_name': s.first_name or '',
                'last_name': s.last_name or ''
            } for s in supervisors],
            'vehicles': [{
                'id': v.id, 
                'vehicle_number': v.vehicle_number, 
                'model': v.model, 
                'capacity': float(v.capacity)
            } for v in vehicles],
            'truck_types': {k: {'name': v['name'], 'single_rate': v['rate_single'], 'double_rate': v['rate_double']} for k, v in truck_rates.items()}
        })
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
def get_trip_details(request, trip_id):
    """
    Get details of a specific trip for the Add KM to Trip functionality
    """
    try:
        fleet_owner, created = FleetOwner.objects.get_or_create(user=request.user)
        trip = Trip.objects.get(id=trip_id, fleet_owner=fleet_owner)
        
        return JsonResponse({
            'trip_id': trip.id,
            'origin': trip.origin,
            'destination': trip.destination,
            'distance': float(trip.distance) if trip.distance else 0,
            'estimated_cost': float(trip.estimated_cost) if trip.estimated_cost else 0,
            'status': trip.status,
            'driver': {
                'id': trip.driver.id,
                'name': f"{trip.driver.user.first_name} {trip.driver.user.last_name}"
            } if trip.driver else None,
            'vehicle': {
                'id': trip.vehicle.id,
                'number': trip.vehicle.vehicle_number,
                'model': trip.vehicle.model
            } if trip.vehicle else None,
            'created_at': trip.created_at.isoformat(),
        })
        
    except Trip.DoesNotExist:
        return JsonResponse({'error': 'Trip not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)