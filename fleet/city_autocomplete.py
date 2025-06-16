"""
City Autocomplete Service using CSV data
Provides fast city lookup with latitude/longitude coordinates
"""

import csv
import os
from django.http import JsonResponse
from django.conf import settings

# Cache for city data to avoid reading CSV repeatedly
_city_cache = None

def load_cities_data():
    """Load cities data from CSV file into memory cache"""
    global _city_cache
    
    if _city_cache is not None:
        return _city_cache
    
    # Path to the CSV file
    csv_path = os.path.join(settings.BASE_DIR, 'attached_assets', 'Indian Cities Geo Data_1749647118764.csv')
    
    cities = []
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Clean up location name by removing "Latitude and Longitude" suffix
                location = row['Location'].replace(' Latitude and Longitude', '')
                
                cities.append({
                    'city': location,
                    'state': row['State'],
                    'latitude': float(row['Latitude']),
                    'longitude': float(row['Longitude']),
                    'display_name': f"{location}, {row['State']}"
                })
    except FileNotFoundError:
        print(f"Cities CSV file not found at: {csv_path}")
        return []
    except Exception as e:
        print(f"Error loading cities data: {e}")
        return []
    
    _city_cache = cities
    return cities

def city_autocomplete(request):
    """
    Autocomplete API for city suggestions
    Returns matching cities with coordinates for map integration
    """
    query = request.GET.get('q', '').strip().lower()
    
    if len(query) < 2:
        return JsonResponse({'results': []})
    
    cities = load_cities_data()
    
    # Filter cities matching the query
    matching_cities = []
    for city in cities:
        if (query in city['city'].lower() or 
            query in city['state'].lower() or
            query in city['display_name'].lower()):
            matching_cities.append({
                'id': f"{city['latitude']},{city['longitude']}",
                'text': city['display_name'],
                'city': city['city'],
                'state': city['state'],
                'latitude': city['latitude'],
                'longitude': city['longitude']
            })
    
    # Sort by relevance (exact matches first, then contains)
    matching_cities.sort(key=lambda x: (
        not x['city'].lower().startswith(query),
        len(x['city']),
        x['city'].lower()
    ))
    
    return JsonResponse({'results': matching_cities[:10]})

def get_all_cities(request):
    """
    Return all cities for dropdown population
    Returns all 4,233 cities in the database
    """
    cities = load_cities_data()
    
    # Format for dropdown usage
    formatted_cities = []
    for city in cities:
        formatted_cities.append({
            'text': city['display_name'],
            'city': city['city'],
            'state': city['state'],
            'latitude': city['latitude'],
            'longitude': city['longitude']
        })
    
    return JsonResponse({'results': formatted_cities})

def get_city_coordinates(city_name, state_name=None):
    """
    Get coordinates for a specific city
    Returns (latitude, longitude) tuple or None if not found
    """
    cities = load_cities_data()
    
    for city in cities:
        if city['city'].lower() == city_name.lower():
            if state_name is None or city['state'].lower() == state_name.lower():
                return (city['latitude'], city['longitude'])
    
    return None

def find_city_by_name(location_string):
    """
    Find city data by parsing location string
    Handles formats like "Mumbai, Maharashtra" or just "Mumbai"
    """
    cities = load_cities_data()
    location_string = location_string.strip()
    
    # Try exact match first
    for city in cities:
        if city['display_name'].lower() == location_string.lower():
            return city
        if city['city'].lower() == location_string.lower():
            return city
    
    # Try partial match
    location_lower = location_string.lower()
    for city in cities:
        if (location_lower in city['city'].lower() or 
            location_lower in city['display_name'].lower()):
            return city
    
    return None