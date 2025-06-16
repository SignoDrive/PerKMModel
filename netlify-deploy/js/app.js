// DriveNowKM Flex - Main Application JavaScript

// Global configuration
const API_BASE_URL = '/api';

// Utility functions
class APIClient {
    static async request(url, options = {}) {
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCSRFToken()
            }
        };

        const mergedOptions = {
            ...defaultOptions,
            ...options,
            headers: {
                ...defaultOptions.headers,
                ...options.headers
            }
        };

        const response = await fetch(url, mergedOptions);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return response.json();
    }

    static getCSRFToken() {
        const token = document.querySelector('[name=csrfmiddlewaretoken]');
        return token ? token.value : '';
    }

    static async get(endpoint) {
        return this.request(`${API_BASE_URL}${endpoint}`);
    }

    static async post(endpoint, data) {
        return this.request(`${API_BASE_URL}${endpoint}`, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    static async patch(endpoint, data) {
        return this.request(`${API_BASE_URL}${endpoint}`, {
            method: 'PATCH',
            body: JSON.stringify(data)
        });
    }
}

// Fleet Management Module
class FleetManager {
    constructor() {
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadInitialData();
    }

    setupEventListeners() {
        document.addEventListener('click', (e) => {
            if (e.target.matches('[data-action]')) {
                this.handleAction(e.target.dataset.action, e.target);
            }
        });
    }

    async loadInitialData() {
        try {
            // Load analytics data if available
            if (document.getElementById('analytics-chart')) {
                await this.loadAnalytics();
            }
        } catch (error) {
            console.error('Error loading fleet data:', error);
        }
    }

    async loadAnalytics() {
        try {
            const data = await APIClient.get('/analytics/');
            this.updateFleetDisplay(data);
        } catch (error) {
            console.error('Error loading analytics:', error);
            this.showAnalyticsLoadingState();
        }
    }

    updateFleetDisplay(data) {
        // Update dashboard metrics
        const elements = {
            'fleet-utilization': `${data.fleet_utilization}%`,
            'total-trips': data.total_trips,
            'completed-trips': data.completed_trips,
            'active-vehicles': data.active_vehicles
        };

        Object.entries(elements).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = value;
            }
        });

        // Create analytics chart if container exists
        this.createAnalyticsChart(data);
    }

    showAnalyticsLoadingState() {
        // Show loading skeleton for analytics
        const container = document.querySelector('.analytics-section');
        if (container) {
            container.innerHTML = `
                <div class="chart-header">
                    <h5 class="chart-title">Fleet Analytics</h5>
                </div>
                <div class="loading-skeleton" style="height: 20px; margin-bottom: 1rem;"></div>
                <div class="loading-skeleton" style="height: 300px;"></div>
            `;
        }
    }

    createAnalyticsChart(data) {
        const canvas = document.getElementById('analytics-chart');
        if (!canvas || !window.Chart) return;

        const ctx = canvas.getContext('2d');
        
        new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Active Vehicles', 'Idle Vehicles'],
                datasets: [{
                    data: [data.active_vehicles, data.total_vehicles - data.active_vehicles],
                    backgroundColor: ['#28a745', '#6c757d'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
    }

    showNotification(message, type = 'info') {
        const alertClass = type === 'success' ? 'alert-success' : 
                          type === 'error' ? 'alert-danger' : 'alert-info';
        
        const alert = document.createElement('div');
        alert.className = `alert ${alertClass} alert-dismissible fade show`;
        alert.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        const container = document.querySelector('main .container-fluid');
        if (container) {
            container.insertBefore(alert, container.firstChild);
            setTimeout(() => alert.remove(), 5000);
        }
    }
}

// Pricing Calculator Module
class PricingCalculator {
    constructor() {
        this.form = document.getElementById('pricing-form');
        if (this.form) {
            this.init();
        }
    }

    init() {
        this.form.addEventListener('submit', this.calculatePrice.bind(this));
    }

    async calculatePrice(e) {
        e.preventDefault();
        
        const data = {
            distance: parseFloat(document.getElementById('distance').value || 0),
            fuel_cost_per_km: parseFloat(document.getElementById('fuel_cost').value || 8),
            driver_cost_per_km: parseFloat(document.getElementById('driver_cost').value || 5),
            double_driver: document.getElementById('double_driver').checked
        };

        try {
            const response = await fetch('/api/pricing-calculator/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': APIClient.getCSRFToken()
                },
                body: JSON.stringify(data)
            });

            const result = await response.json();

            if (response.ok) {
                this.displayResult(result);
            } else {
                throw new Error(result.error || 'Calculation failed');
            }
        } catch (error) {
            alert('Error calculating price: ' + error.message);
        }
    }

    displayResult(result) {
        const totalCostEl = document.getElementById('total-cost');
        const costPerKmEl = document.getElementById('cost-per-km');
        const resultEl = document.getElementById('pricing-result');

        if (totalCostEl) totalCostEl.textContent = result.total_cost.toFixed(2);
        if (costPerKmEl) costPerKmEl.textContent = result.cost_per_km.toFixed(2);
        if (resultEl) resultEl.style.display = 'block';
    }
}

// Payment Request Manager
class PaymentRequestManager {
    constructor() {
        this.init();
    }

    init() {
        this.setupExpenseForm();
        this.loadPaymentHistory();
    }

    setupExpenseForm() {
        const form = document.getElementById('expense-form');
        if (form) {
            form.addEventListener('submit', this.submitExpenseRequest.bind(this));
        }
    }

    async submitExpenseRequest(e) {
        e.preventDefault();
        
        const form = e.target;
        const submitBtn = form.querySelector('button[type="submit"]');
        const originalText = submitBtn.innerHTML;
        
        // Validate file upload
        const receiptFile = form.querySelector('#receipt').files[0];
        if (!receiptFile) {
            alert('Please upload a receipt or document');
            return;
        }

        // Check file size (5MB limit)
        if (receiptFile.size > 5 * 1024 * 1024) {
            alert('File size must be less than 5MB');
            return;
        }

        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Submitting...';

        try {
            const formData = new FormData();
            formData.append('type', form.querySelector('#expense_type').value);
            formData.append('amount', form.querySelector('#amount').value);
            formData.append('description', form.querySelector('#reason').value);
            formData.append('receipt', receiptFile);

            const response = await fetch('/api/submit-payment-request/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': APIClient.getCSRFToken()
                },
                body: formData
            });

            const result = await response.json();

            if (response.ok) {
                this.showSuccessMessage('Expense request submitted successfully!');
                form.reset();
                await this.loadPaymentHistory();
            } else {
                throw new Error(result.error || 'Failed to submit request');
            }
        } catch (error) {
            alert('Error submitting request: ' + error.message);
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalText;
        }
    }

    async loadPaymentHistory() {
        const container = document.getElementById('payment-history');
        if (!container) return;

        try {
            const requests = await APIClient.get('/payment-requests/');
            this.displayPaymentHistory(requests, container);
        } catch (error) {
            container.innerHTML = '<p class="text-muted">Error loading payment history</p>';
        }
    }

    displayPaymentHistory(requests, container) {
        if (requests.length === 0) {
            container.innerHTML = `
                <div class="text-center text-muted py-3">
                    <i class="fas fa-inbox fa-2x mb-2"></i>
                    <p>No payment requests yet</p>
                </div>
            `;
            return;
        }

        let html = '<div class="table-responsive"><table class="table table-sm">';
        html += '<thead><tr><th>Date</th><th>Type</th><th>Amount</th><th>Status</th><th>Comments</th></tr></thead><tbody>';

        requests.forEach(request => {
            const statusClass = request.status === 'approved' ? 'success' : 
                               request.status === 'rejected' ? 'danger' : 'warning';
            const date = new Date(request.requested_at).toLocaleDateString();
            
            html += `
                <tr>
                    <td>${date}</td>
                    <td><span class="badge bg-secondary">${request.type}</span></td>
                    <td>₹${request.amount}</td>
                    <td><span class="badge bg-${statusClass}">${request.status}</span></td>
                    <td>${request.review_comments || '--'}</td>
                </tr>
            `;
        });

        html += '</tbody></table></div>';
        container.innerHTML = html;
    }

    showSuccessMessage(message) {
        const alert = document.createElement('div');
        alert.className = 'alert alert-success alert-dismissible fade show';
        alert.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        const container = document.querySelector('main .container-fluid');
        if (container) {
            container.insertBefore(alert, container.firstChild);
            setTimeout(() => alert.remove(), 5000);
        }
    }
}

// Trip Management
class TripManager {
    static async startTrip(tripId) {
        try {
            const response = await fetch(`/api/start-trip/${tripId}/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': APIClient.getCSRFToken()
                }
            });

            const result = await response.json();

            if (response.ok) {
                alert('Trip started successfully!');
                location.reload();
            } else {
                throw new Error(result.error);
            }
        } catch (error) {
            alert('Error: ' + error.message);
        }
    }

    static async completeTrip(tripId) {
        try {
            const response = await fetch(`/api/complete-trip/${tripId}/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': APIClient.getCSRFToken()
                },
                body: JSON.stringify({})
            });

            const result = await response.json();

            if (response.ok) {
                alert('Trip completed successfully!');
                location.reload();
            } else {
                throw new Error(result.error);
            }
        } catch (error) {
            alert('Error: ' + error.message);
        }
    }
}

// Global functions for inline event handlers
window.startTrip = function(tripId) {
    if (confirm('Are you sure you want to start this trip?')) {
        TripManager.startTrip(tripId);
    }
};

window.completeTrip = function(tripId) {
    if (confirm('Are you sure you want to mark this trip as completed?')) {
        TripManager.completeTrip(tripId);
    }
};

window.applyForJob = function(jobId) {
    if (confirm('Are you sure you want to apply for this job?')) {
        alert('Application submitted successfully! You will be notified once approved.');
    }
};

window.loadJobs = function() {
    location.reload();
};

window.loadRecentActivity = function() {
    const container = document.getElementById('recent-activity');
    if (container) {
        container.innerHTML = `
            <div class="text-muted">
                <i class="fas fa-check-circle text-success"></i> Trip completed: Mumbai to Pune<br>
                <small class="text-muted">2 hours ago</small>
            </div>
            <hr>
            <div class="text-muted">
                <i class="fas fa-clock text-warning"></i> Payment request pending: Fuel expense<br>
                <small class="text-muted">4 hours ago</small>
            </div>
        `;
    }
};

// Initialize application when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize all modules
    new FleetManager();
    new PricingCalculator();
    new PaymentRequestManager();

    // Setup tooltips if Bootstrap is available
    if (window.bootstrap && bootstrap.Tooltip) {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
});