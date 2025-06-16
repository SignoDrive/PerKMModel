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
from django.utils import timezone

def create_demo_data():
    print("Setting up DriveNowKM Fleet Management Demo Data...")
    
    # Get existing fleet owner or create if doesn't exist
    try:
        fleet_user = User.objects.get(username='fleetowner')
        fleet_owner = fleet_user.fleet_owner
        print("Found existing fleet owner")
    except User.DoesNotExist:
        fleet_user = User.objects.create_user(
            username='fleetowner',
            email='owner@drivenowkm.com',
            password='fleet123',
            role='fleet_owner',
            first_name='Rajesh',
            last_name='Patel'
        )
        
        fleet_owner = FleetOwner.objects.create(
            user=fleet_user,
            company_name='Mumbai Transport Co.',
            km_balance=Decimal('25000.00'),
            prepaid_balance=Decimal('75000.00')
        )
        print("Created new fleet owner")
    
    # Clear existing sample data to refresh
    Vehicle.objects.filter(fleet_owner=fleet_owner).delete()
    Trip.objects.filter(fleet_owner=fleet_owner).delete()
    PaymentRequest.objects.filter(driver__fleet_owner=fleet_owner).delete()
    JobPosting.objects.filter(fleet_owner=fleet_owner).delete()
    
    # Create comprehensive vehicle fleet
    vehicles_data = [
        {'number': 'MH-14-AB-1234', 'model': 'Tata Ace', 'capacity': '1.5', 'status': 'active'},
        {'number': 'MH-14-CD-5678', 'model': 'Mahindra Bolero', 'capacity': '2.0', 'status': 'active'},
        {'number': 'MH-14-EF-9012', 'model': 'Eicher Pro 1049', 'capacity': '3.5', 'status': 'active'},
        {'number': 'MH-14-GH-3456', 'model': 'Ashok Leyland Dost', 'capacity': '1.8', 'status': 'active'},
        {'number': 'MH-14-IJ-7890', 'model': 'Tata 407', 'capacity': '2.5', 'status': 'active'},
        {'number': 'MH-14-KL-2345', 'model': 'Mahindra Pickup', 'capacity': '1.2', 'status': 'maintenance'},
        {'number': 'MH-14-MN-6789', 'model': 'Force Traveller', 'capacity': '3.0', 'status': 'active'},
        {'number': 'MH-14-OP-0123', 'model': 'Tata Super Ace', 'capacity': '1.4', 'status': 'idle'},
        {'number': 'MH-14-QR-4567', 'model': 'Isuzu D-Max', 'capacity': '2.2', 'status': 'active'},
        {'number': 'MH-14-ST-8901', 'model': 'Bajaj Maxitruck', 'capacity': '1.0', 'status': 'active'},
        {'number': 'MH-14-UV-3456', 'model': 'Mahindra Jeeto', 'capacity': '0.8', 'status': 'active'},
        {'number': 'MH-14-WX-7890', 'model': 'Eicher Pro 3009', 'capacity': '4.0', 'status': 'active'},
        {'number': 'MH-14-YZ-1234', 'model': 'Ashok Leyland Partner', 'capacity': '1.6', 'status': 'active'},
        {'number': 'GJ-05-AB-5678', 'model': 'Tata Intra V10', 'capacity': '1.7', 'status': 'active'},
        {'number': 'GJ-05-CD-9012', 'model': 'Maruti Super Carry', 'capacity': '0.7', 'status': 'active'},
    ]
    
    vehicles = []
    for vehicle_data in vehicles_data:
        vehicle = Vehicle.objects.create(
            fleet_owner=fleet_owner,
            vehicle_number=vehicle_data['number'],
            model=vehicle_data['model'],
            capacity=Decimal(vehicle_data['capacity']),
            fuel_type='diesel',
            status=vehicle_data['status'],
            current_location={'lat': 19.0760 + (len(vehicles) * 0.01), 'lng': 72.8777 + (len(vehicles) * 0.01)}
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
        {'username': 'driver6', 'first_name': 'Prakash', 'last_name': 'Yadav', 'license': 'DL-14-20190006'},
        {'username': 'driver7', 'first_name': 'Vikash', 'last_name': 'Gupta', 'license': 'DL-14-20190007'},
        {'username': 'driver8', 'first_name': 'Santosh', 'last_name': 'Mishra', 'license': 'DL-14-20190008'},
    ]
    
    drivers = []
    for i, driver_data in enumerate(drivers_data):
        # Create or get driver user
        try:
            driver_user = User.objects.get(username=driver_data['username'])
        except User.DoesNotExist:
            driver_user = User.objects.create_user(
                username=driver_data['username'],
                email=f"{driver_data['username']}@drivenowkm.com",
                password='driver123',
                role='driver',
                first_name=driver_data['first_name'],
                last_name=driver_data['last_name']
            )
        
        # Create or get driver profile
        driver, created = Driver.objects.get_or_create(
            user=driver_user,
            defaults={
                'fleet_owner': fleet_owner,
                'license_number': driver_data['license'],
                'vehicle_number': vehicles[i % len(vehicles)].vehicle_number if i < len(vehicles) else None,
                'is_active': True,
                'current_location': {
                    'latitude': 19.0760 + (i * 0.005), 
                    'longitude': 72.8777 + (i * 0.005),
                    'timestamp': timezone.now().isoformat()
                }
            }
        )
        drivers.append(driver)
    print(f"Created {len(drivers)} drivers")
    
    # Create realistic trips with various statuses
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
            'actual_cost': None,
            'status': 'in_progress',
            'days_ago': 0
        },
        {
            'origin': 'Bandra',
            'destination': 'Aurangabad',
            'distance': 334.7,
            'estimated_cost': 18500.00,
            'actual_cost': None,
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
            'actual_cost': None,
            'status': 'in_progress',
            'days_ago': 1
        },
        {
            'origin': 'Goregaon',
            'destination': 'Rajkot',
            'distance': 389.1,
            'estimated_cost': 21000.00,
            'actual_cost': None,
            'status': 'pending',
            'days_ago': 0
        },
        {
            'origin': 'Worli',
            'destination': 'Indore',
            'distance': 588.9,
            'estimated_cost': 29400.00,
            'actual_cost': 29100.00,
            'status': 'completed',
            'days_ago': 7
        },
        {
            'origin': 'Powai',
            'destination': 'Solapur',
            'distance': 456.8,
            'estimated_cost': 24300.00,
            'actual_cost': None,
            'status': 'pending',
            'days_ago': 0
        },
        {
            'origin': 'Malad',
            'destination': 'Ahmednagar',
            'distance': 267.4,
            'estimated_cost': 14800.00,
            'actual_cost': 14600.00,
            'status': 'completed',
            'days_ago': 3
        },
        {
            'origin': 'Vikhroli',
            'destination': 'Kolhapur',
            'distance': 412.6,
            'estimated_cost': 22700.00,
            'actual_cost': None,
            'status': 'in_progress',
            'days_ago': 0
        },
        {
            'origin': 'Mulund',
            'destination': 'Sangli',
            'distance': 378.2,
            'estimated_cost': 20500.00,
            'actual_cost': None,
            'status': 'pending',
            'days_ago': 0
        },
        {
            'origin': 'Ghatkopar',
            'destination': 'Satara',
            'distance': 289.7,
            'estimated_cost': 16100.00,
            'actual_cost': 15950.00,
            'status': 'completed',
            'days_ago': 4
        }
    ]
    
    trips = []
    
    # Assign most trips to the first driver (demo driver - driver1)
    for i, trip_data in enumerate(trips_data):
        trip_date = datetime.now() - timedelta(days=trip_data['days_ago'])
        
        # Assign 70% of trips to driver1 for better demo experience
        if i < 7:  # First 7 trips go to driver1
            assigned_driver = drivers[0] if trip_data['status'] != 'pending' else None
            assigned_vehicle = vehicles[0] if trip_data['status'] != 'pending' else None
        else:  # Remaining trips distributed among other drivers
            driver_index = (i - 7) % (len(drivers) - 1) + 1
            assigned_driver = drivers[driver_index] if trip_data['status'] != 'pending' else None
            assigned_vehicle = vehicles[driver_index] if trip_data['status'] != 'pending' else None
        
        trip = Trip.objects.create(
            fleet_owner=fleet_owner,
            driver=assigned_driver,
            vehicle=assigned_vehicle,
            origin=trip_data['origin'],
            destination=trip_data['destination'],
            distance=Decimal(str(trip_data['distance'])),
            estimated_cost=Decimal(str(trip_data['estimated_cost'])),
            actual_cost=Decimal(str(trip_data['actual_cost'])) if trip_data['actual_cost'] else None,
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
            'driver': drivers[0],
            'trip': trips[0],
            'amount': 1200.00,
            'type': 'fuel',
            'description': 'Fuel expenses for Mumbai-Pune trip',
            'status': 'approved',
            'days_ago': 2
        },
        {
            'driver': drivers[1],
            'trip': trips[1],
            'amount': 800.00,
            'type': 'maintenance',
            'description': 'Vehicle servicing and oil change',
            'status': 'pending',
            'days_ago': 1
        },
        {
            'driver': drivers[2],
            'trip': None,
            'amount': 5000.00,
            'type': 'advance',
            'description': 'Salary advance for family emergency',
            'status': 'approved',
            'days_ago': 3
        },
        {
            'driver': drivers[3],
            'trip': trips[3],
            'amount': 650.00,
            'type': 'other',
            'description': 'Toll charges and parking fees',
            'status': 'approved',
            'days_ago': 5
        },
        {
            'driver': drivers[4],
            'trip': trips[4],
            'amount': 950.00,
            'type': 'fuel',
            'description': 'Diesel refill at highway pump',
            'status': 'pending',
            'days_ago': 1
        },
        {
            'driver': drivers[5],
            'trip': None,
            'amount': 2500.00,
            'type': 'maintenance',
            'description': 'Tire replacement and alignment',
            'status': 'rejected',
            'days_ago': 4
        }
    ]
    
    for req_data in payment_requests_data:
        req_date = datetime.now() - timedelta(days=req_data['days_ago'])
        
        PaymentRequest.objects.create(
            driver=req_data['driver'],
            trip=req_data['trip'],
            amount=Decimal(str(req_data['amount'])),
            type=req_data['type'],
            description=req_data['description'],
            status=req_data['status'],
            requested_at=req_date,
            reviewed_at=req_date + timedelta(hours=12) if req_data['status'] != 'pending' else None,
            reviewed_by=fleet_user if req_data['status'] != 'pending' else None,
            review_comments='Approved for business expense' if req_data['status'] == 'approved' else 
                           'Rejected - insufficient documentation' if req_data['status'] == 'rejected' else None
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
        {
            'title': 'Local Delivery: Mumbai Port to Warehouses',
            'origin': 'Mumbai Port',
            'destination': 'Multiple Warehouses',
            'distance': 45.6,
            'estimated_cost': 2800.00,
            'requirements': 'Local area knowledge. Container handling experience.',
            'status': 'assigned'
        }
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
    
    print("\n✓ Demo data setup completed successfully!")
    print(f"✓ Fleet: {len(vehicles)} vehicles, {len(drivers)} drivers")
    print(f"✓ Operations: {len(trips)} trips, {len(payment_requests_data)} payment requests")
    print(f"✓ Opportunities: {len(job_postings_data)} job postings")
    print("\nYou can now refresh your dashboard to see the populated data.")


if __name__ == '__main__':
    create_demo_data()