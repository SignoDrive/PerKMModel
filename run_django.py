#!/usr/bin/env python
import os
import sys
import subprocess

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "drivenowkm.settings")
    
    # Change to the correct directory
    os.chdir('/home/runner/workspace')
    
    # Run Django server
    subprocess.call([sys.executable, "manage.py", "runserver", "0.0.0.0:8000"])