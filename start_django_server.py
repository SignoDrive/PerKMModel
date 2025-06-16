#!/usr/bin/env python3
"""
Start Django server for DriveNowKM Fleet Management System
"""
import os
import sys
import django
from django.core.management import execute_from_command_line

if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'drivenowkm.settings')
    execute_from_command_line(['manage.py', 'runserver', '0.0.0.0:8000'])