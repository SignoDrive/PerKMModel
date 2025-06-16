import requests
import json
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
import os

@csrf_exempt
@login_required
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
    api_key = os.getenv('OLA_MAPS_API_KEY')
    if not api_key:
    return JsonResponse({'error': 'Ola Maps API key not configured'}, status=500)

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
    distance_km = round(distance_meters / 1000.0, 0)

    # Get pricing based on truck type and driver type
    truck_rates = get_truck_rates()

    if truck_type not in truck_rates:
    return JsonResponse({'error': 'Invalid truck type'}, status=400)

    truck_info = truck_rates[truck_type]

    # Apply formula-based calculations with complete business logic
    calculated_results = calculate_trip_pricing(int(distance_km), truck_type, driver_type, truck_info)

    if 'error' in calculated_results:
    return JsonResponse(calculated_results, status=400)

    distance_km = calculated_results['distance_km']
    rate_per_km = calculated_results['rate_per_km']
    total_cost = calculated_results['total_cost']

    response_data = {
    'origin': {
    'address': origin,
    'lat': origin_lat,
    'lng': origin_lng
    },
    'destination': {
    'address': destination,
    'lat': destination_lat,
    'lng': destination_lng
    },
    'distance_km': distance_km,
    'truck_type': truck_type,
    'driver_type': driver_type,
    'rate_per_km': rate_per_km,
    'total_cost': total_cost,
    'truck_specs': calculated_results.get('truck_specs', {}),
    'calculation_details': calculated_results.get('calculation_details', {})
    }

    return JsonResponse(response_data)

    except json.JSONDecodeError:
    return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
    return JsonResponse({'error': f'Internal server error: {str(e)}'}, status=500)


def get_admin_pricing_config():
    """
    Get admin-configurable pricing parameters
    Only admin users can modify these values
    """
    return {
    'diesel_cost': 92,  # Cost per liter of diesel
    'avg_mileage': 4.5,     # Average kilometers per liter
    'driver_salary': 1500,  # Driver salary per trip
    'en_route_expenses': 2.5  # En-route expenses per km
    }


def get_minimum_charges():
    """
    Get minimum charges for different truck types
    Admin configurable values
    """
    return {
    '6_tyre_open': 3000,
    '6_tyre_closed': 3000,
    '6_tyre_open_16t': 3500,
    '6_tyre_closed_16t': 3500,
    '10_tyre_open': 4000,
    '10_tyre_closed': 4000,
    '12_tyre_rigid': 5000,
    '14_tyre_rigid': 6000,
    '14_tyre_flatbed': 5500,
    '14_tyre_container': 5500,
    '16_tyre_flatbed': 6500,
    '16_tyre_container': 6500,
    '18_tyre_trailer': 8000,
    '22_tyre_trailer': 10000
    }


def calculate_trip_pricing(distance_km, truck_type, driver_type, truck_info):
    """
    Apply exact formula-based calculations for trip pricing
    Uses the specific formulas provided for fuel, driver, and per km costs
    """
    try:
    # Get admin-configurable base values (only admin can change these)
    base_config = get_admin_pricing_config()

    # Distance calculations
    distance_traveled = distance_km + 50  # Add buffer for actual route

    # Apply the exact formulas provided
    # self.fuel_cost = (((self.distance_traveled/self.avg)*self.diesel_cost)/self.distance_traveled)
    fuel_cost = ((distance_traveled / base_config['avg_mileage']) * base_config['diesel_cost']) / distance_traveled

    # self.single_driver_cost = self.driver_salary/self.distance_traveled
    single_driver_cost = base_config['driver_salary'] / distance_traveled

    # self.double_driver_cost = (self.driver_salary*2)/self.distance_traveled
    double_driver_cost = (base_config['driver_salary'] * 2) / distance_traveled

    # self.per_km_cost_single_driver = (self.fuel_cost + self.single_driver_cost + self.en_route_expenses)*1.15
    per_km_cost_single_driver = (fuel_cost + single_driver_cost + base_config['en_route_expenses']) * 1.15

    # self.per_km_cost_double_driver = (self.fuel_cost + self.double_driver_cost + self.en_route_expenses)*1.15
    per_km_cost_double_driver = (fuel_cost + double_driver_cost + base_config['en_route_expenses']) * 1.15

    # Select appropriate rate based on driver type
    if driver_type == 'single':
    final_rate = per_km_cost_single_driver
    elif driver_type == 'double':
    final_rate = per_km_cost_double_driver
    else:
    return {'error': 'Invalid driver type'}

    # Calculate total cost
    total_cost = distance_traveled * final_rate

    # Apply minimum charges based on truck type
    minimum_charges = get_minimum_charges()
    min_charge = minimum_charges.get(truck_type, 3000)
    if total_cost < min_charge:
    total_cost = min_charge

    # Round to nearest 50
    total_cost = round(total_cost / 50) * 50

    return {
    'distance_km': int(distance_traveled),
    'rate_per_km': round(final_rate, 2),
    'total_cost': int(total_cost),
    'truck_specs': {
    'gross_weight': truck_info['gw'],
    'net_weight': truck_info['net'],
    'name': truck_info['name']
    },
    'calculation_details': {
    'fuel_cost': round(fuel_cost, 2),
    'driver_cost': round(single_driver_cost if driver_type == 'single' else double_driver_cost, 2),
    'en_route_expenses': base_config['en_route_expenses'],
    'markup': '15%',
    'final_calculation': f'{distance_traveled}km × ₹{final_rate:.2f}/km = ₹{total_cost}'
    }
    }

    except Exception as e:
    return {'error': f'Calculation error: {str(e)}'}


def get_truck_rates():
    """
    Return truck rates and specifications based on the CSV data provided
    """
    return {
    '6_tyre_open': {
    'rate_single': 26.50,
    'rate_double': 33.08,
    'gw': 13000,
    'net': 7000,
    'name': '6 Tyre Trucks OPEN (13T GW)'
    },
    '6_tyre_closed': {
    'rate_single': 26.50,
    'rate_double': 33.08,
    'gw': 13000,
    'net': 7000,
    'name': '6 Tyre Trucks CLOSED (13T GW)'
    },
    '6_tyre_open_16t': {
    'rate_single': 29.20,
    'rate_double': 36.87,
    'gw': 16000,
    'net': 10000,
    'name': '6 Tyre Trucks OPEN (16T GW)'
    },
    '6_tyre_closed_16t': {
    'rate_single': 28.11,
    'rate_double': 34.68,
    'gw': 16000,
    'net': 10000,
    'name': '6 Tyre Trucks CLOSED (16T GW)'
    },
    '10_tyre_open': {
    'rate_single': 32.89,
    'rate_double': 39.96,
    'gw': 25000,
    'net': 18000,
    'name': '10 Tyre Multi Axle Truck OPEN (25T GW)'
    },
    '10_tyre_closed': {
    'rate_single': 32.89,
    'rate_double': 39.96,
    'gw': 25000,
    'net': 18000,
    'name': '10 Tyre Multi Axle Truck CLOSED (25T GW)'
    },
    '12_tyre_rigid': {
    'rate_single': 35.32,
    'rate_double': 41.89,
    'gw': 31000,
    'net': 25000,
    'name': '12 Tyre Single Chassis Truck Rigid OPEN (31T GW)'
    },
    '14_tyre_rigid': {
    'rate_single': 39.61,
    'rate_double': 46.68,
    'gw': 37000,
    'net': 30000,
    'name': '14 Tyre Single Chassis Truck Rigid OPEN (37T GW)'
    },
    '14_tyre_flatbed': {
    'rate_single': 38.33,
    'rate_double': 47.92,
    'gw': 29000,
    'net': 22000,
    'name': '14 Tyre Trailer FLAT BED (29T GW)'
    },
    '14_tyre_container': {
    'rate_single': 38.33,
    'rate_double': 47.92,
    'gw': 29000,
    'net': 22000,
    'name': '14 Tyre Trailer CONTAINER (29T GW)'
    },
    '16_tyre_flatbed': {
    'rate_single': 40.10,
    'rate_double': 49.68,
    'gw': 35000,
    'net': 27000,
    'name': '16 Tyre Trailer FLAT BED (35T GW)'
    },
    '16_tyre_container': {
    'rate_single': 40.10,
    'rate_double': 49.68,
    'gw': 35000,
    'net': 27000,
    'name': '16 Tyre Trailer CONTAINER (35T GW)'
    },
    '18_tyre_trailer': {
    'rate_single': 57.40,
    'rate_double': 70.18,
    'gw': 40200,
    'net': 35000,
    'name': '18 Tyre Trailer (40.2T GW)'
    },
    '22_tyre_trailer': {
    'rate_single': 62.10,
    'rate_double': 74.88,
    'gw': 49000,
    'net': 40000,
    'name': '22 Tyre Trailer (49T GW)'
    }
    }