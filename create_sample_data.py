#!/usr/bin/env python
import os
import sys
import django
from datetime import datetime, timedelta
from decimal import Decimal

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'drivenowkm.settings')
django.setup()

from fleet.models import User, FleetOwner, Driver, Vehicle, Trip, PaymentRequest, JobPosting

def create_sample_data():
    print("Creating sample data for DriveNowKM Fleet Management...")
    
    # Get existing fleet owner
    try:
        fleet_user = User.objects.get(username='fleetowner')
        fleet_owner = fleet_user.fleet_owner
        print("Using existing fleet owner")
    except User.DoesNotExist:
        print("Fleet owner not found. Please create one first.")
        return
    
    # Clear existing data for fresh start
    Vehicle.objects.filter(fleet_owner=fleet_owner).delete()
    Trip.objects.filter(fleet_owner=fleet_owner).delete()
    PaymentRequest.objects.filter(driver__fleet_owner=fleet_owner).delete()
    JobPosting.objects.filter(fleet_owner=fleet_owner).delete()
    Driver.objects.filter(fleet_owner=fleet_owner).delete()
    
    # Create vehicles
    vehicles_data = [
        {'number': 'MH-14-AB-1234', 'model': 'Tata Ace', 'capacity': '1.5', 'status': 'active'},
        {'number': 'MH-14-CD-5678', 'model': 'Mahindra Bolero', 'capacity': '2.0', 'status': 'active'},
        {'number': 'MH-14-EF-9012', 'model': 'Eicher Pro 1049', 'capacity': '3.5', 'status': 'active'},
        {'number': 'MH-14-GH-3456', 'model': 'Ashok Leyland Dost', 'capacity': '1.8', 'status': 'active'},
        {'number': 'MH-14-IJ-7890', 'model': 'Tata 407', 'capacity': '2.5', 'status': 'active'},
        {'number': 'MH-14-KL-2345', 'model': 'Mahindra Pickup', 'capacity': '1.2', 'status': 'maintenance'},
        {'number': 'MH-14-MN-6789', 'model': 'Force Traveller', 'capacity': '3.0', 'status': 'active'},
        {'number': 'MH-14-OP-0123', 'model': 'Tata Super Ace', 'capacity': '1.4', 'status': 'idle'},
    ]
    
    vehicles = []
    for vehicle_data in vehicles_data:
        vehicle = Vehicle.objects.create(
            fleet_owner=fleet_owner,
            vehicle_number=vehicle_data['number'],
            model=vehicle_data['model'],
            capacity=Decimal(vehicle_data['capacity']),
            fuel_type='diesel',
            status=vehicle_data['status']
        )
        vehicles.append(vehicle)
    print(f"Created {len(vehicles)} vehicles")
    
    # Create drivers
    drivers_data = [
        {'username': 'driver1', 'first_name': 'Amit', 'last_name': 'Sharma', 'license': 'DL-14-20190001'},
        {'username': 'driver2', 'first_name': 'Suresh', 'last_name': 'Kumar', 'license': 'DL-14-20190002'},
        {'username': 'driver3', 'first_name': 'Ravi', 'last_name': 'Singh', 'license': 'DL-14-20190003'},
        {'username': 'driver4', 'first_name': 'Deepak', 'last_name': 'Joshi', 'license': 'DL-14-20190004'},
        {'username': 'driver5', 'first_name': 'Manoj', 'last_name': 'Verma', 'license': 'DL-14-20190005'},
    ]
    
    drivers = []
    for i, driver_data in enumerate(drivers_data):
        # Create driver user
        driver_user, created = User.objects.get_or_create(
            username=driver_data['username'],
            defaults={
                'email': f"{driver_data['username']}@drivenowkm.com",
                'role': 'driver',
                'first_name': driver_data['first_name'],
                'last_name': driver_data['last_name']
            }
        )
        
        if created:
            driver_user.set_password('driver123')
            driver_user.save()
        
        # Create driver profile
        driver = Driver.objects.create(
            user=driver_user,
            fleet_owner=fleet_owner,
            license_number=driver_data['license'],
            vehicle_number=vehicles[i % len(vehicles)].vehicle_number if i < len(vehicles) else None,
            is_active=True
        )
        drivers.append(driver)
    print(f"Created {len(drivers)} drivers")
    
    # Create trips
    trips_data = [
        {
            'origin': 'Mumbai Central',
            'destination': 'Pune',
            'distance': 148.5,
            'estimated_cost': 8900.00,
            'actual_cost': 8750.00,
            'status': 'completed',
            'days_ago': 2
        },
        {
            'origin': 'Andheri East',
            'destination': 'Nashik',
            'distance': 165.2,
            'estimated_cost': 9800.00,
            'status': 'in_progress',
            'days_ago': 0
        },
        {
            'origin': 'Bandra',
            'destination': 'Aurangabad',
            'distance': 334.7,
            'estimated_cost': 18500.00,
            'status': 'pending',
            'days_ago': 0
        },
        {
            'origin': 'Thane',
            'destination': 'Nagpur',
            'distance': 712.3,
            'estimated_cost': 35600.00,
            'actual_cost': 35200.00,
            'status': 'completed',
            'days_ago': 5
        },
        {
            'origin': 'Borivali',
            'destination': 'Surat',
            'distance': 297.5,
            'estimated_cost': 16200.00,
            'status': 'in_progress',
            'days_ago': 1
        },
    ]
    
    trips = []
    for i, trip_data in enumerate(trips_data):
        trip_date = datetime.now() - timedelta(days=trip_data['days_ago'])
        
        trip = Trip.objects.create(
            fleet_owner=fleet_owner,
            driver=drivers[i % len(drivers)] if trip_data['status'] != 'pending' else None,
            vehicle=vehicles[i % len(vehicles)] if trip_data['status'] != 'pending' else None,
            origin=trip_data['origin'],
            destination=trip_data['destination'],
            distance=Decimal(str(trip_data['distance'])),
            estimated_cost=Decimal(str(trip_data['estimated_cost'])),
            actual_cost=Decimal(str(trip_data['actual_cost'])) if trip_data.get('actual_cost') else None,
            status=trip_data['status'],
            created_at=trip_date,
            start_time=trip_date if trip_data['status'] in ['in_progress', 'completed'] else None,
            end_time=trip_date + timedelta(hours=8) if trip_data['status'] == 'completed' else None
        )
        trips.append(trip)
    print(f"Created {len(trips)} trips")
    
    # Create payment requests
    payment_requests_data = [
        {
            'driver_idx': 0,
            'trip_idx': 0,
            'amount': 1200.00,
            'type': 'fuel',
            'description': 'Fuel expenses for Mumbai-Pune trip',
            'status': 'approved',
            'days_ago': 2
        },
        {
            'driver_idx': 1,
            'trip_idx': 1,
            'amount': 800.00,
            'type': 'maintenance',
            'description': 'Vehicle servicing and oil change',
            'status': 'pending',
            'days_ago': 1
        },
        {
            'driver_idx': 2,
            'trip_idx': None,
            'amount': 5000.00,
            'type': 'advance',
            'description': 'Salary advance for family emergency',
            'status': 'approved',
            'days_ago': 3
        },
    ]
    
    for req_data in payment_requests_data:
        req_date = datetime.now() - timedelta(days=req_data['days_ago'])
        
        PaymentRequest.objects.create(
            driver=drivers[req_data['driver_idx']],
            trip=trips[req_data['trip_idx']] if req_data['trip_idx'] is not None else None,
            amount=Decimal(str(req_data['amount'])),
            type=req_data['type'],
            description=req_data['description'],
            status=req_data['status'],
            requested_at=req_date,
            reviewed_at=req_date + timedelta(hours=12) if req_data['status'] != 'pending' else None,
            reviewed_by=fleet_user if req_data['status'] != 'pending' else None
        )
    print(f"Created {len(payment_requests_data)} payment requests")
    
    # Create job postings
    job_postings_data = [
        {
            'title': 'Urgent: Mumbai to Bangalore Delivery',
            'origin': 'Mumbai',
            'destination': 'Bangalore',
            'distance': 984.2,
            'estimated_cost': 45000.00,
            'requirements': 'Heavy vehicle license required. 3+ years experience.',
            'status': 'available'
        },
        {
            'title': 'Weekly Route: Mumbai to Goa',
            'origin': 'Mumbai',
            'destination': 'Goa',
            'distance': 467.3,
            'estimated_cost': 22000.00,
            'requirements': 'Tourism experience preferred. Clean driving record.',
            'status': 'available'
        },
    ]
    
    for job_data in job_postings_data:
        JobPosting.objects.create(
            fleet_owner=fleet_owner,
            title=job_data['title'],
            origin=job_data['origin'],
            destination=job_data['destination'],
            distance=Decimal(str(job_data['distance'])),
            estimated_cost=Decimal(str(job_data['estimated_cost'])),
            requirements=job_data['requirements'],
            status=job_data['status'],
            created_at=datetime.now() - timedelta(days=1),
            expires_at=datetime.now() + timedelta(days=7)
        )
    print(f"Created {len(job_postings_data)} job postings")
    
    print("\n✓ Sample data created successfully!")
    print(f"✓ Fleet: {len(vehicles)} vehicles, {len(drivers)} drivers")
    print(f"✓ Operations: {len(trips)} trips, {len(payment_requests_data)} payment requests")
    print(f"✓ Jobs: {len(job_postings_data)} job postings")
    print("\nRefresh your dashboard to see the data.")

if __name__ == '__main__':
    create_sample_data()