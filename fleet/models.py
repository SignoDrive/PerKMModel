from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

class User(AbstractUser):
    ROLE_CHOICES = [
        ('fleet_owner', 'Fleet Owner'),
        ('driver', 'Driver'),
        ('supervisor', 'Supervisor'),
        ('admin', 'Admin'),
    ]
    
    email = models.EmailField(unique=True, null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='fleet_owner')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

class FleetOwner(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='fleet_owner')
    company_name = models.CharField(max_length=255, null=True, blank=True)
    km_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    prepaid_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.company_name or 'Fleet Owner'}"

class Driver(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='driver')
    fleet_owner = models.ForeignKey(FleetOwner, on_delete=models.CASCADE, related_name='drivers', null=True, blank=True)
    license_number = models.CharField(max_length=50, null=True, blank=True)
    vehicle_number = models.CharField(max_length=20, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    current_location = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.license_number or 'Driver'}"

class TruckSpecification(models.Model):
    """
    Truck specifications based on the spreadsheet data
    Contains all the parameters needed for formula-based pricing calculations
    """
    truck_type = models.CharField(max_length=100, unique=True, help_text="Exact truck type name from spreadsheet")
    gw = models.IntegerField(help_text="Gross Weight in kg")
    net_weight = models.IntegerField(help_text="Net Weight in kg")
    avg_kmpl = models.DecimalField(max_digits=5, decimal_places=2, help_text="Average KM per liter")
    driver_salary = models.DecimalField(max_digits=10, decimal_places=2, help_text="Monthly driver salary")
    distance_traveled = models.IntegerField(help_text="Average monthly distance traveled in km")
    en_route_expenses = models.DecimalField(max_digits=5, decimal_places=2, default=2.0, help_text="En-route expenses per km")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['truck_type']
        verbose_name = "Truck Specification"
        verbose_name_plural = "Truck Specifications"

    def __str__(self):
        return f"{self.truck_type} (GW: {self.gw}kg)"

    def calculate_fuel_cost_per_km(self, diesel_cost=92.0):
        """Calculate fuel cost per km using exact formula"""
        return ((self.distance_traveled / self.avg_kmpl) * diesel_cost) / self.distance_traveled

    def calculate_driver_cost_per_km(self, driver_type='single'):
        """Calculate driver cost per km based on driver type"""
        if driver_type == 'double':
            return (self.driver_salary * 2) / self.distance_traveled
        return self.driver_salary / self.distance_traveled

    def calculate_per_km_cost(self, driver_type='single', diesel_cost=92.0):
        """Calculate final per km cost with 15% markup"""
        fuel_cost = self.calculate_fuel_cost_per_km(diesel_cost)
        driver_cost = self.calculate_driver_cost_per_km(driver_type)
        base_cost = fuel_cost + driver_cost + self.en_route_expenses
        return base_cost * 1.15

class Vehicle(models.Model):
    VEHICLE_STATUS_CHOICES = [
        ('active', 'Active'),
        ('maintenance', 'Maintenance'),
        ('idle', 'Idle'),
    ]

    fleet_owner = models.ForeignKey(FleetOwner, on_delete=models.CASCADE, related_name='vehicles')
    vehicle_number = models.CharField(max_length=20, unique=True)
    model = models.CharField(max_length=100)
    capacity = models.DecimalField(max_digits=8, decimal_places=2)
    fuel_type = models.CharField(max_length=20, default='diesel')
    status = models.CharField(max_length=20, choices=VEHICLE_STATUS_CHOICES, default='active')
    current_location = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.vehicle_number} - {self.model}"

class Trip(models.Model):
    TRIP_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    fleet_owner = models.ForeignKey(FleetOwner, on_delete=models.CASCADE, related_name='trips')
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name='trips', null=True, blank=True)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='trips', null=True, blank=True)
    origin = models.CharField(max_length=255)
    destination = models.CharField(max_length=255)
    distance = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    actual_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=TRIP_STATUS_CHOICES, default='pending')
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.origin} to {self.destination} - {self.status}"

class PaymentRequest(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('supervisor_approved', 'Supervisor Approved'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    PAYMENT_TYPES = [
        ('fuel', 'Fuel'),
        ('maintenance', 'Maintenance'),
        ('salary', 'Salary'),
        ('advance', 'Advance'),
        ('other', 'Other'),
    ]

    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name='payment_requests')
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='payment_requests', null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    type = models.CharField(max_length=20, choices=PAYMENT_TYPES)
    description = models.TextField()
    receipt_url = models.URLField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    requested_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_requests')
    review_comments = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.driver.user.username} - {self.type} - ₹{self.amount}"

class JobPosting(models.Model):
    fleet_owner = models.ForeignKey(FleetOwner, on_delete=models.CASCADE, related_name='job_postings')
    title = models.CharField(max_length=200)
    origin = models.CharField(max_length=255)
    destination = models.CharField(max_length=255)
    distance = models.DecimalField(max_digits=8, decimal_places=2)
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=2)
    requirements = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=20, default='available')  # available, assigned, completed
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def __str__(self):
        return f"{self.title} - {self.origin} to {self.destination}"


class Notification(models.Model):
    """Model to store notifications for users"""
    NOTIFICATION_TYPES = [
        ('trip_created', 'Trip Created'),
        ('trip_assigned', 'Trip Assigned'),
        ('job_posted', 'Job Posted'),
        ('job_application', 'Job Application'),
        ('driver_assigned', 'Driver Assigned'),
        ('trip_started', 'Trip Started'),
        ('trip_completed', 'Trip Completed'),
        ('payment_request', 'Payment Request'),
        ('payment_approved', 'Payment Approved'),
    ]
    
    PRIORITY_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_notifications', null=True, blank=True)
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    priority = models.CharField(max_length=10, choices=PRIORITY_LEVELS, default='medium')
    
    # Related objects
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, null=True, blank=True)
    job_posting = models.ForeignKey(JobPosting, on_delete=models.CASCADE, null=True, blank=True)
    
    # Metadata
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Action data
    action_data = models.JSONField(null=True, blank=True)  # Store additional data for actions
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.title} - {self.recipient.username}"
    
    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()