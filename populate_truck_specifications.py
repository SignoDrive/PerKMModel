#!/usr/bin/env python3
"""
Populate TruckSpecification table with exact data from the spreadsheet
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'drivenowkm.settings')
django.setup()

from fleet.models import TruckSpecification

def populate_truck_specifications():
    """Populate truck specifications with exact spreadsheet data"""
    
    truck_data = [
        {
            'truck_type': '6 Tyre trucks OPEN',
            'gw': 13000,
            'net_weight': 7000,
            'avg_kmpl': 6.00,
            'driver_salary': 40000,
            'distance_traveled': 7000,
            'en_route_expenses': 2.0
        },
        {
            'truck_type': '6 Tyre trucks CLOSED',
            'gw': 13000,
            'net_weight': 7000,
            'avg_kmpl': 6.00,
            'driver_salary': 40000,
            'distance_traveled': 7000,
            'en_route_expenses': 2.0
        },
        {
            'truck_type': '6 Tyre trucks OPEN (10T)',
            'gw': 16000,
            'net_weight': 10000,
            'avg_kmpl': 5.50,
            'driver_salary': 40000,
            'distance_traveled': 6000,
            'en_route_expenses': 2.0
        },
        {
            'truck_type': '6 Tyre trucks CLOSED (10T)',
            'gw': 16000,
            'net_weight': 10000,
            'avg_kmpl': 5.50,
            'driver_salary': 40000,
            'distance_traveled': 7000,
            'en_route_expenses': 2.0
        },
        {
            'truck_type': '10 tyres Multi axle Truck OPEN',
            'gw': 25000,
            'net_weight': 18000,
            'avg_kmpl': 4.50,
            'driver_salary': 40000,
            'distance_traveled': 6500,
            'en_route_expenses': 2.0
        },
        {
            'truck_type': '10 tyres Multi axle Truck CLOSED',
            'gw': 25000,
            'net_weight': 18000,
            'avg_kmpl': 4.50,
            'driver_salary': 40000,
            'distance_traveled': 6500,
            'en_route_expenses': 2.0
        },
        {
            'truck_type': '12 Tyre Single Chassis truck Rigid OPEN',
            'gw': 31000,
            'net_weight': 25000,
            'avg_kmpl': 4.00,
            'driver_salary': 40000,
            'distance_traveled': 7000,
            'en_route_expenses': 2.0
        },
        {
            'truck_type': '14 Tyre Single Chassis truck Rigid OPEN',
            'gw': 37000,
            'net_weight': 30000,
            'avg_kmpl': 3.50,
            'driver_salary': 40000,
            'distance_traveled': 6500,
            'en_route_expenses': 2.0
        },
        {
            'truck_type': '14 Tyre Trailer FLAT BED',
            'gw': 29000,
            'net_weight': 22000,
            'avg_kmpl': 4.00,
            'driver_salary': 50000,
            'distance_traveled': 6000,
            'en_route_expenses': 2.0
        },
        {
            'truck_type': '14 Tyre Trailer CONTAINER',
            'gw': 29000,
            'net_weight': 22000,
            'avg_kmpl': 4.00,
            'driver_salary': 50000,
            'distance_traveled': 6000,
            'en_route_expenses': 2.0
        },
        {
            'truck_type': '16 Tyre Trailer FLAT BED',
            'gw': 35000,
            'net_weight': 27000,
            'avg_kmpl': 3.75,
            'driver_salary': 50000,
            'distance_traveled': 6000,
            'en_route_expenses': 2.0
        },
        {
            'truck_type': '16 Tyre Trailer CONTAINER',
            'gw': 35000,
            'net_weight': 27000,
            'avg_kmpl': 3.75,
            'driver_salary': 50000,
            'distance_traveled': 6000,
            'en_route_expenses': 2.0
        },
        {
            'truck_type': '18 Tyre Trailer',
            'gw': 40200,
            'net_weight': 35000,
            'avg_kmpl': 2.50,
            'driver_salary': 50000,
            'distance_traveled': 4500,
            'en_route_expenses': 2.0
        },
        {
            'truck_type': '22 Tyre Trailer',
            'gw': 49000,
            'net_weight': 40000,
            'avg_kmpl': 2.25,
            'driver_salary': 50000,
            'distance_traveled': 4500,
            'en_route_expenses': 2.0
        }
    ]
    
    created_count = 0
    updated_count = 0
    
    for truck_spec in truck_data:
        obj, created = TruckSpecification.objects.update_or_create(
            truck_type=truck_spec['truck_type'],
            defaults=truck_spec
        )
        
        if created:
            created_count += 1
            print(f"Created: {truck_spec['truck_type']}")
        else:
            updated_count += 1
            print(f"Updated: {truck_spec['truck_type']}")
    
    print(f"\nPopulation complete:")
    print(f"Created: {created_count} records")
    print(f"Updated: {updated_count} records")
    print(f"Total: {TruckSpecification.objects.count()} truck specifications in database")

if __name__ == '__main__':
    populate_truck_specifications()