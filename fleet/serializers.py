from rest_framework import serializers
from .models import User, FleetOwner, Driver, Vehicle, Trip, PaymentRequest, JobPosting

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'phone', 'role', 'first_name', 'last_name']
        extra_kwargs = {'password': {'write_only': True}}

class FleetOwnerSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = FleetOwner
        fields = ['id', 'user', 'company_name', 'km_balance', 'prepaid_balance', 'created_at']

class DriverSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    fleet_owner = FleetOwnerSerializer(read_only=True)
    
    class Meta:
        model = Driver
        fields = ['id', 'user', 'fleet_owner', 'license_number', 'vehicle_number', 'is_active', 'current_location']

class VehicleSerializer(serializers.ModelSerializer):
    fleet_owner = FleetOwnerSerializer(read_only=True)
    
    class Meta:
        model = Vehicle
        fields = ['id', 'fleet_owner', 'vehicle_number', 'model', 'capacity', 'fuel_type', 'status', 'current_location']

class TripSerializer(serializers.ModelSerializer):
    fleet_owner = FleetOwnerSerializer(read_only=True)
    driver = DriverSerializer(read_only=True)
    vehicle = VehicleSerializer(read_only=True)
    
    class Meta:
        model = Trip
        fields = ['id', 'fleet_owner', 'driver', 'vehicle', 'origin', 'destination', 'distance', 
                 'estimated_cost', 'actual_cost', 'status', 'start_time', 'end_time', 'created_at']

class PaymentRequestSerializer(serializers.ModelSerializer):
    driver = DriverSerializer(read_only=True)
    trip = TripSerializer(read_only=True)
    reviewed_by = UserSerializer(read_only=True)
    
    class Meta:
        model = PaymentRequest
        fields = ['id', 'driver', 'trip', 'amount', 'type', 'description', 'receipt_url', 
                 'status', 'requested_at', 'reviewed_at', 'reviewed_by', 'review_comments']

class JobPostingSerializer(serializers.ModelSerializer):
    fleet_owner = FleetOwnerSerializer(read_only=True)
    
    class Meta:
        model = JobPosting
        fields = ['id', 'fleet_owner', 'title', 'origin', 'destination', 'distance', 
                 'estimated_cost', 'requirements', 'status', 'created_at', 'expires_at']