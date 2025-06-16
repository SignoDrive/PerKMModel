import requests
import json
import os
import math
from decimal import Decimal, ROUND_HALF_UP, ROUND_UP

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from fleet.models import TruckSpecification


@csrf_exempt
def calculate_distance(request):
    """
    Calculate distance between origin and destination using Ola Maps API
    and return pricing information based on truck and driver type
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)

    try:
        data = json.loads(request.body)
        origin = data.get('origin')
        destination = data.get('destination')
        truck_type = data.get('truck_type')
        driver_type = data.get('driver_type')

        if not all([origin, destination, truck_type, driver_type]):
            return JsonResponse({'error': 'Missing required parameters'}, status=400)

        # Get Ola Maps API key from environment
        api_key = settings.OLA_MAPS_API_KEY
        if not api_key:
            return JsonResponse({'error': 'Ola Maps API key not configured. Please contact administrator.'}, status=500)

        try:
            # Step 1: Get coordinates from CSV database
            from .city_autocomplete import find_city_by_name

            origin_city = find_city_by_name(origin)
            if not origin_city:
                return JsonResponse({'error': f'Origin location "{origin}" not found in database'}, status=400)
            origin_lat = origin_city['latitude']
            origin_lng = origin_city['longitude']

            destination_city = find_city_by_name(destination)
            if not destination_city:
                return JsonResponse({'error': f'Destination location "{destination}" not found in database'}, status=400)
            destination_lat = destination_city['latitude']
            destination_lng = destination_city['longitude']

            # Step 3: Calculate distance using coordinates
            distance_url = f"https://api.olamaps.io/routing/v1/distanceMatrix/basic?origins={origin_lat},{origin_lng}&destinations={destination_lat},{destination_lng}&api_key={api_key}"
            distance_response = requests.get(distance_url, timeout=10)

            if distance_response.status_code != 200:
                return JsonResponse({'error': f'Failed to calculate distance: {distance_response.status_code}'}, status=400)

            distance_data = distance_response.json()
            if not distance_data.get('rows') or not distance_data['rows'][0].get('elements'):
                return JsonResponse({'error': 'No distance data available for this route'}, status=400)

            distance_meters = distance_data["rows"][0]["elements"][0]["distance"]
            distance_km = distance_meters / 1000.0
            distance_km = math.ceil(distance_km)

        except requests.exceptions.RequestException as e:
            return JsonResponse({'error': f'Network error: {str(e)}'}, status=500)
        except (KeyError, IndexError, TypeError) as e:
            return JsonResponse({'error': f'Invalid API response format: {str(e)}'}, status=500)

        truck_quantity = int(data.get('truck_quantity', 1))
        pricing_info = calculate_trip_pricing(distance_km, truck_type, driver_type, truck_quantity)

        if not pricing_info.get('success'):
            return JsonResponse({'error': pricing_info.get('error', 'Pricing calculation failed')}, status=400)

        return JsonResponse({
            'success': True,
            'distance': round(distance_km, 2),
            'truck_quantity': truck_quantity,
            'single': pricing_info['single'],
            'multi': pricing_info['multi'],
            'metadata': pricing_info['metadata'],
        })

    except requests.exceptions.RequestException as e:
        return JsonResponse({'error': f'Network error: {str(e)}'}, status=500)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)


def calculate_trip_pricing(distance_km, truck_type, driver_type, truck_quantity=1):
    try:
        truck_spec = TruckSpecification.objects.get(truck_type=truck_type, is_active=True)

        diesel_cost = 92.0
        en_route_expenses_per_km = 2.0

        distance_km = float(distance_km)
        truck_quantity = int(truck_quantity)

        avg_kmpl = float(truck_spec.avg_kmpl)
        driver_salary = float(truck_spec.driver_salary)
        distance_traveled = float(truck_spec.distance_traveled)

        fuel_cost_per_km = round(diesel_cost / avg_kmpl, 2)

        if driver_type == 'single':
            driver_cost_per_km = round(driver_salary / distance_traveled, 2)
        else:
            driver_cost_per_km = round((driver_salary * 2) / distance_traveled, 2)

        enroute_cost_per_km = en_route_expenses_per_km

        # Nested function properly indented inside try block
        def calculate_for_quantity(qty):
            total_fuel_cost = round(fuel_cost_per_km * distance_km * qty, 2)
            total_driver_cost = round(driver_cost_per_km * distance_km * qty, 2)
            total_enroute_cost = round(enroute_cost_per_km * distance_km * qty, 2)
            base_cost = round(total_fuel_cost + total_driver_cost + total_enroute_cost, 2)

            if qty >= 20:
                service_charge_rate = 0.13
            elif qty >= 10:
                service_charge_rate = 0.15
            elif qty >= 5:
                service_charge_rate = 0.18
            else:
                service_charge_rate = 0.20

            service_charge = round(base_cost * service_charge_rate, 2)
            final_total_cost = round(base_cost + service_charge, 2)
            per_km_rate = round(final_total_cost / distance_km, 2)

            return {
                'truck_quantity': qty,
                'fuel_cost_per_km': fuel_cost_per_km,
                'driver_cost_per_km': driver_cost_per_km,
                'enroute_cost_per_km': enroute_cost_per_km,
                'total_fuel_cost': total_fuel_cost,
                'total_driver_cost': total_driver_cost,
                'total_enroute_cost': total_enroute_cost,
                'base_cost': base_cost,
                'service_charge_rate': service_charge_rate,
                'service_charge': service_charge,
                'total_cost': final_total_cost,
                'per_km_rate': per_km_rate
            }

        single_result = calculate_for_quantity(1)
        multiple_result = calculate_for_quantity(truck_quantity)
        if truck_quantity == 1:
            multiple_result = single_result.copy()
        return {
            'success': True,
            'distance': distance_km,
            'single': single_result,
            'multi': multiple_result,
            'metadata': {
                'truck_type': truck_type,
                'driver_type': driver_type,
                'diesel_cost': diesel_cost,
                'avg_kmpl': avg_kmpl
            }
        }

    except Exception as e:
        return {'success': False, 'error': f"Error in pricing calculation: {str(e)}"}


@csrf_exempt
def autocomplete_location(request):
    if request.method != 'GET':
        return JsonResponse({'error': 'Only GET method allowed'}, status=405)

    query = request.GET.get('query', '').strip()
    if not query or len(query) < 3:
        return JsonResponse({'suggestions': []})

    api_key = os.getenv('OLA_MAPS_API_KEY')
    if not api_key:
        return JsonResponse({'error': 'Ola Maps API key not configured'}, status=500)

    try:
        url = f"https://api.olamaps.io/places/v1/autocomplete"
        params = {'input': query, 'api_key': api_key, 'language': 'en'}
        headers = {'X-Request-Id': f'autocomplete_{query[:20]}_{hash(query) % 10000}'}

        response = requests.get(url, params=params, headers=headers, timeout=5)

        if response.status_code != 200:
            return JsonResponse({'error': f'Autocomplete API error: {response.status_code}'}, status=400)

        data = response.json()
        suggestions = []

        if data.get('predictions'):
            for prediction in data['predictions'][:5]:
                suggestions.append({
                    'place_id': prediction.get('place_id'),
                    'description': prediction.get('description'),
                    'structured_formatting': prediction.get('structured_formatting', {})
                })

        return JsonResponse({'suggestions': suggestions})

    except requests.exceptions.RequestException as e:
        return JsonResponse({'error': f'Network error: {str(e)}'}, status=500)
    except Exception as e:
        return JsonResponse({'error': f'Autocomplete error: {str(e)}'}, status=500)
