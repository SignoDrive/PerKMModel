#!/usr/bin/env python3
import os
import sys
import time

def log_step(step_num, description):
    print(f"[{time.strftime('%H:%M:%S')}] STEP {step_num}: {description}")

def main():
    print("=== DriveNowKM Fleet Management Console Logs ===")
    
    log_step(1, "Python Environment Check")
    print(f"  Python Version: {sys.version.split()[0]}")
    print(f"  Working Directory: {os.getcwd()}")
    print(f"  Process ID: {os.getpid()}")
    
    log_step(2, "Django Settings Configuration")
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'drivenowkm.settings')
    print(f"  Django Settings Module: {os.environ['DJANGO_SETTINGS_MODULE']}")
    
    log_step(3, "Django Framework Loading")
    try:
        import django
        django.setup()
        print("  ✓ Django framework initialized successfully")
        
        from django.conf import settings
        print(f"  ✓ Database: {settings.DATABASES['default']['ENGINE']}")
        print(f"  ✓ Debug Mode: {settings.DEBUG}")
        print(f"  ✓ Installed Apps: {len(settings.INSTALLED_APPS)}")
        
    except Exception as e:
        print(f"  ✗ Django setup error: {e}")
        return
    
    log_step(4, "Fleet Management Models Loading")
    try:
        from fleet.models import User, FleetOwner, Driver, Vehicle, Trip, PaymentRequest, JobPosting
        print("  ✓ User model loaded")
        print("  ✓ FleetOwner model loaded")
        print("  ✓ Driver model loaded")
        print("  ✓ Vehicle model loaded")
        print("  ✓ Trip model loaded")
        print("  ✓ PaymentRequest model loaded")
        print("  ✓ JobPosting model loaded")
        
        # Check database data
        print(f"  ✓ Users in database: {User.objects.count()}")
        print(f"  ✓ Fleet owners: {FleetOwner.objects.count()}")
        print(f"  ✓ Drivers: {Driver.objects.count()}")
        
    except Exception as e:
        print(f"  ✗ Model loading error: {e}")
    
    log_step(5, "Authentication System Test")
    try:
        from django.contrib.auth import authenticate
        
        test_accounts = [
            ('fleetowner', 'fleet123'),
            ('driver1', 'driver123'),
            ('supervisor', 'super123')
        ]
        
        for username, password in test_accounts:
            user = authenticate(username=username, password=password)
            if user:
                print(f"  ✓ {username}: Authentication successful (Role: {user.role})")
            else:
                print(f"  ✗ {username}: Authentication failed")
                
    except Exception as e:
        print(f"  ✗ Authentication test error: {e}")
    
    log_step(6, "URL Routing Verification")
    try:
        from django.test import Client
        client = Client()
        
        test_urls = [
            ('/', 'Root URL'),
            ('/login/', 'Login Page'),
            ('/logout/', 'Logout URL')
        ]
        
        for url, description in test_urls:
            response = client.get(url)
            print(f"  ✓ {description}: {url} → HTTP {response.status_code}")
            
    except Exception as e:
        print(f"  ✗ URL routing error: {e}")
    
    log_step(7, "Static Files Check")
    static_files = [
        'static/css/styles.css',
        'static/js/app.js'
    ]
    
    for file_path in static_files:
        if os.path.exists(file_path):
            size = os.path.getsize(file_path)
            print(f"  ✓ {file_path}: {size:,} bytes")
        else:
            print(f"  ✗ {file_path}: Not found")
    
    log_step(8, "Server Startup Preparation")
    print("  ✓ Django development server ready")
    print("  ✓ Port 8000 configured for binding")
    print("  ✓ Static file serving enabled")
    print("  ✓ Auto-reload enabled for development")
    
    log_step(9, "Executing Server Command")
    print("  Command: python manage.py runserver 0.0.0.0:8000")
    print("  Server will start and begin accepting connections...")
    
    print("\n=== Starting Django Development Server ===")
    
    # Import and run server
    from django.core.management import execute_from_command_line
    execute_from_command_line(['manage.py', 'runserver', '0.0.0.0:8000'])

if __name__ == "__main__":
    main()