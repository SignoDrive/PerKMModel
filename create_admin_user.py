#!/usr/bin/env python
"""
Create Admin User for DriveNowKM Fleet Management System
This script creates a superuser with full system access and admin capabilities.
"""

import os
import sys
import django
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'drivenowkm.settings')
django.setup()

from fleet.models import User, FleetOwner

def create_admin_user():
    """Create admin user with full system privileges"""
    
    # Admin user credentials
    admin_username = 'admin'
    admin_email = 'admin@drivenowkm.com'
    admin_password = 'admin123'
    
    try:
        # Check if admin user already exists
        admin_user = User.objects.get(username=admin_username)
        print(f"Admin user '{admin_username}' already exists!")
        
        # Update admin privileges
        admin_user.is_staff = True
        admin_user.is_superuser = True
        admin_user.role = 'admin'
        admin_user.save()
        
        print("Updated existing admin user with full privileges.")
        
    except User.DoesNotExist:
        # Create new admin user
        admin_user = User.objects.create_user(
            username=admin_username,
            email=admin_email,
            password=admin_password,
            first_name='System',
            last_name='Administrator',
            role='admin',
            is_staff=True,
            is_superuser=True,
            is_active=True
        )
        
        print(f"Created admin user: {admin_username}")
        print(f"Email: {admin_email}")
        print(f"Password: {admin_password}")
        
        # Create admin fleet owner profile
        admin_fleet_owner = FleetOwner.objects.create(
            user=admin_user,
            company_name="DriveNowKM Admin",
            km_balance=999999.00,
            prepaid_balance=999999.00
        )
        
        print("Created admin fleet owner profile with unlimited balance.")
    
    # Assign all permissions to admin user
    all_permissions = Permission.objects.all()
    admin_user.user_permissions.set(all_permissions)
    
    print(f"Assigned {all_permissions.count()} permissions to admin user.")
    
    return admin_user

def main():
    """Main function"""
    print("=" * 60)
    print("DriveNowKM Fleet Management - Admin User Creation")
    print("=" * 60)
    
    try:
        admin_user = create_admin_user()
        
        print("\n" + "=" * 60)
        print("ADMIN USER CREATED SUCCESSFULLY")
        print("=" * 60)
        print(f"Username: {admin_user.username}")
        print(f"Email: {admin_user.email}")
        print(f"Role: {admin_user.role}")
        print(f"Staff Status: {admin_user.is_staff}")
        print(f"Superuser Status: {admin_user.is_superuser}")
        print("\nAdmin Access URLs:")
        print("- Main Dashboard: /dashboard/")
        print("- Django Admin: /admin/")
        print("- User Management: /admin/fleet/user/")
        print("- Fleet Management: /admin/fleet/")
        print("\nAdmin Capabilities:")
        print("- View and edit all user accounts")
        print("- Reset passwords for any user")
        print("- Access all fleet data")
        print("- Manage trips, payments, and vehicles")
        print("- View analytics and reports")
        print("- Full system administration")
        
    except Exception as e:
        print(f"Error creating admin user: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()