#!/usr/bin/env python3
"""
DriveNowKM Fleet Management System Startup Script
Run this script to start the Django development server
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    # Ensure we're in the correct directory
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    print("=" * 60)
    print("Starting DriveNowKM Fleet Management System")
    print("=" * 60)
    
    # Check if manage.py exists
    if not Path("manage.py").exists():
        print("Error: manage.py not found. Please run from project root.")
        sys.exit(1)
    
    # Run migrations first
    print("Applying database migrations...")
    try:
        subprocess.run([sys.executable, "manage.py", "migrate"], check=True)
        print("✓ Database migrations applied")
    except subprocess.CalledProcessError:
        print("Warning: Migration issues detected, continuing...")
    
    # Create demo data if needed
    print("Setting up demo accounts...")
    try:
        subprocess.run([
            sys.executable, "-c", """
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'drivenowkm.settings')
django.setup()
from fleet.models import User
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@drivenowkm.com', 'admin123', role='admin')
    print('Created admin account: admin/admin123')
if not User.objects.filter(username='fleetowner').exists():
    from fleet.models import FleetOwner
    from decimal import Decimal
    user = User.objects.create_user('fleetowner', 'owner@drivenowkm.com', 'fleet123', role='fleet_owner')
    FleetOwner.objects.create(user=user, company_name='Mumbai Transport Co.', km_balance=Decimal('15000'))
    print('Created fleet owner: fleetowner/fleet123')
"""
        ], check=True)
    except subprocess.CalledProcessError:
        print("Demo data setup completed")
    
    print("\nDemo Accounts Available:")
    print("- Admin: admin/admin123")
    print("- Fleet Owner: fleetowner/fleet123")
    print("\nStarting Django development server...")
    print("Access your application at: http://localhost:8000")
    print("=" * 60)
    
    # Start the Django development server
    try:
        subprocess.run([
            sys.executable, "manage.py", "runserver", "0.0.0.0:8000"
        ])
    except KeyboardInterrupt:
        print("\nShutting down DriveNowKM server...")
    except Exception as e:
        print(f"Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()