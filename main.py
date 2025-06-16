#!/usr/bin/env python3
"""
DriveNowKM Fleet Management System - Main Entry Point
This file is executed when you click "Run" in Replit
"""

import os
import sys
import subprocess
import time

def log_message(message):
    timestamp = time.strftime('%H:%M:%S')
    print(f"[{timestamp}] {message}")

def main():
    print("=" * 60)
    print("DRIVENOWKM FLEET MANAGEMENT SYSTEM")
    print("=" * 60)
    
    log_message("Initializing system...")
    
    # Change to project directory
    os.chdir('/home/runner/workspace')
    log_message("Working directory set")
    
    # Set Django settings
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'drivenowkm.settings')
    log_message("Django environment configured")
    
    # Test Django setup
    try:
        import django
        django.setup()
        log_message("Django framework loaded successfully")
        
        from fleet.models import User
        user_count = User.objects.count()
        log_message(f"Database connected - {user_count} users found")
        
        log_message("Authentication system ready")
        log_message("Fleet management models active")
        
    except Exception as e:
        log_message(f"Setup warning: {e}")
    
    log_message("Starting Django development server on port 8000...")
    print("\nDemo Accounts Available:")
    print("- Fleet Owner: fleetowner/fleet123")
    print("- Driver: driver1/driver123")
    print("- Supervisor: supervisor/super123")
    print("\nAccess your application in the preview window")
    print("=" * 60)
    
    # Run Django server
    try:
        subprocess.call([sys.executable, 'manage.py', 'runserver', '0.0.0.0:8000'])
    except KeyboardInterrupt:
        log_message("Server shutdown requested")
    except Exception as e:
        log_message(f"Server error: {e}")

if __name__ == "__main__":
    main()