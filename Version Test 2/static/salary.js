/**
 * Salary Management JavaScript
 * Handles AJAX requests for salary management functionality
 */

// Global variables
let currentEmployeeId = null;
let currentRequestId = null;
let currentAction = null;

/**
 * Load salary components for an employee
 */
function loadComponents(employeeId, isEdit = false) {
    fetch(`/salary/admin/${employeeId}/components`)
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                showAlert('Error loading components: ' + data.error, 'error');
                return;
            }
            
            if (isEdit) {
                displayEditComponents(data);
            } else {
                displayComponents(data);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showAlert('Error loading components', 'error');
        });
}

/**
 * Display components in view mode
 */
function displayComponents(components) {
    const content = document.getElementById('componentsContent');
    
    if (components.length === 0) {
        content.innerHTML = '<p class="text-muted">No salary components found.</p>';
        return;
    }
    
    let html = `
        <div class="table-responsive">
            <table class="table table-hover">
                <thead>
                    <tr>
                        <th>Type</th>
                        <th>Label</th>
                        <th>Amount</th>
                        <th>Effective From</th>
                        <th>Effective To</th>
                        <th>Created</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    components.forEach(component => {
        const typeClass = getComponentTypeClass(component.component_type);
        const amountClass = component.component_type === 'deduction' ? 'text-danger' : 'text-success';
        const amountPrefix = component.component_type === 'deduction' ? '-' : '+';
        
        html += `
            <tr>
                <td><span class="badge ${typeClass}">${component.component_type.charAt(0).toUpperCase() + component.component_type.slice(1)}</span></td>
                <td>${component.label}</td>
                <td class="${amountClass} fw-bold">${amountPrefix}₹${formatCurrency(component.amount)}</td>
                <td>${component.effective_from}</td>
                <td>${component.effective_to || 'Ongoing'}</td>
                <td>${new Date(component.created_at).toLocaleDateString()}</td>
            </tr>
        `;
    });
    
    html += `
                </tbody>
            </table>
        </div>
    `;
    
    content.innerHTML = html;
}

/**
 * Display components in edit mode
 */
function displayEditComponents(components) {
    const content = document.getElementById('editComponentsContent');
    
    let html = `
        <div class="mb-3">
            <button class="btn btn-primary" onclick="showAddComponentForm()">
                <i class="fas fa-plus me-1"></i>Add Component
            </button>
        </div>
        
        <div id="addComponentForm" style="display: none;" class="card mb-3">
            <div class="card-header">
                <h6 class="mb-0">Add New Component</h6>
            </div>
            <div class="card-body">
                <form id="componentForm">
                    <div class="row">
                        <div class="col-md-6">
                            <div class="mb-3">
                                <label for="componentType" class="form-label">Type</label>
                                <select class="form-select" id="componentType" name="component_type" required>
                                    <option value="">Select type...</option>
                                    <option value="base">Base Salary</option>
                                    <option value="allowance">Allowance</option>
                                    <option value="bonus">Bonus</option>
                                    <option value="deduction">Deduction</option>
                                </select>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="mb-3">
                                <label for="componentLabel" class="form-label">Label</label>
                                <input type="text" class="form-control" id="componentLabel" name="label" required>
                            </div>
                        </div>
                    </div>
                    
                    <div class="row">
                        <div class="col-md-6">
                            <div class="mb-3">
                                <label for="componentAmount" class="form-label">Amount</label>
                                <div class="input-group">
                                    <span class="input-group-text">₹</span>
                                    <input type="number" class="form-control" id="componentAmount" name="amount" 
                                           min="0" step="0.01" required>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="mb-3">
                                <label for="effectiveFrom" class="form-label">Effective From</label>
                                <input type="date" class="form-control" id="effectiveFrom" name="effective_from" required>
                            </div>
                        </div>
                    </div>
                    
                    <div class="mb-3">
                        <label for="effectiveTo" class="form-label">Effective To (Optional)</label>
                        <input type="date" class="form-control" id="effectiveTo" name="effective_to">
                    </div>
                    
                    <div class="d-flex gap-2">
                        <button type="button" class="btn btn-primary" onclick="addComponent()">Add Component</button>
                        <button type="button" class="btn btn-secondary" onclick="hideAddComponentForm()">Cancel</button>
                    </div>
                </form>
            </div>
        </div>
        
        <div class="table-responsive">
            <table class="table table-hover">
                <thead>
                    <tr>
                        <th>Type</th>
                        <th>Label</th>
                        <th>Amount</th>
                        <th>Effective From</th>
                        <th>Effective To</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    components.forEach(component => {
        const typeClass = getComponentTypeClass(component.component_type);
        const amountClass = component.component_type === 'deduction' ? 'text-danger' : 'text-success';
        const amountPrefix = component.component_type === 'deduction' ? '-' : '+';
        
        html += `
            <tr>
                <td><span class="badge ${typeClass}">${component.component_type.charAt(0).toUpperCase() + component.component_type.slice(1)}</span></td>
                <td>${component.label}</td>
                <td class="${amountClass} fw-bold">${amountPrefix}₹${formatCurrency(component.amount)}</td>
                <td>${component.effective_from}</td>
                <td>${component.effective_to || 'Ongoing'}</td>
                <td>
                    <button class="btn btn-sm btn-danger" onclick="deleteComponent('${component._id}')">
                        <i class="fas fa-trash"></i>
                    </button>
                </td>
            </tr>
        `;
    });
    
    html += `
                </tbody>
            </table>
        </div>
    `;
    
    content.innerHTML = html;
}

/**
 * Load salary history for an employee
 */
function loadHistory(employeeId) {
    // For now, show a placeholder - in a real implementation, you'd fetch from an API
    const content = document.getElementById('historyContent');
    content.innerHTML = `
        <div class="text-center py-4">
            <i class="fas fa-history fa-3x text-muted mb-3"></i>
            <p class="text-muted">Salary history will be displayed here.</p>
            <p class="text-muted">Use the "Generate New Snapshot" button to create salary history records.</p>
        </div>
    `;
}

/**
 * Show add component form
 */
function showAddComponentForm() {
    document.getElementById('addComponentForm').style.display = 'block';
    // Set default effective from date to today
    document.getElementById('effectiveFrom').value = new Date().toISOString().split('T')[0];
}

/**
 * Hide add component form
 */
function hideAddComponentForm() {
    document.getElementById('addComponentForm').style.display = 'none';
    document.getElementById('componentForm').reset();
}

/**
 * Add a new salary component
 */
function addComponent() {
    const form = document.getElementById('componentForm');
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());
    
    // Validate form
    if (!data.component_type || !data.label || !data.amount || !data.effective_from) {
        showAlert('Please fill in all required fields.', 'error');
        return;
    }
    
    if (parseFloat(data.amount) <= 0) {
        showAlert('Amount must be greater than 0.', 'error');
        return;
    }
    
    // Submit component
    fetch(`/salary/admin/${currentEmployeeId}/components`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            showAlert('Error adding component: ' + data.error, 'error');
        } else {
            showAlert('Component added successfully!', 'success');
            hideAddComponentForm();
            loadComponents(currentEmployeeId, true); // Reload components
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showAlert('Error adding component', 'error');
    });
}

/**
 * Delete a salary component
 */
function deleteComponent(componentId) {
    if (!confirm('Are you sure you want to delete this component?')) {
        return;
    }
    
    fetch(`/salary/admin/components/${componentId}`, {
        method: 'DELETE'
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            showAlert('Error deleting component: ' + data.error, 'error');
        } else {
            showAlert('Component deleted successfully!', 'success');
            loadComponents(currentEmployeeId, true); // Reload components
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showAlert('Error deleting component', 'error');
    });
}

/**
 * Submit request action (approve/reject)
 */
function submitRequestAction() {
    const adminResponse = document.getElementById('adminResponse').value;
    
    const url = currentAction === 'approve' 
        ? `/salary/admin/request/${currentRequestId}/approve`
        : `/salary/admin/request/${currentRequestId}/reject`;
    
    fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            admin_response: adminResponse
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            showAlert('Error processing request: ' + data.error, 'error');
        } else {
            showAlert(data.message, 'success');
            $('#requestActionModal').modal('hide');
            // Clear the form
            document.getElementById('adminResponse').value = '';
            // Refresh data dynamically
            refreshSalaryData();
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showAlert('Error processing request', 'error');
    });
}

/**
 * Generate salary history
 */
function submitGenerateHistory() {
    const periodStart = document.getElementById('periodStart').value;
    const periodEnd = document.getElementById('periodEnd').value;
    
    if (!periodStart || !periodEnd) {
        showAlert('Please select both start and end dates.', 'error');
        return;
    }
    
    if (new Date(periodStart) >= new Date(periodEnd)) {
        showAlert('End date must be after start date.', 'error');
        return;
    }
    
    fetch(`/salary/admin/${currentEmployeeId}/generate`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            period_start: periodStart,
            period_end: periodEnd
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            showAlert('Error generating history: ' + data.error, 'error');
        } else {
            showAlert('Salary history generated successfully!', 'success');
            $('#generateHistoryModal').modal('hide');
            loadHistory(currentEmployeeId); // Reload history
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showAlert('Error generating history', 'error');
    });
}

/**
 * Refresh salary data dynamically
 */
function refreshSalaryData() {
    fetch('/salary/admin/refresh-data')
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                showAlert('Error refreshing data: ' + data.error, 'error');
                return;
            }
            
            // Update KPI cards
            updateKPICards(data);
            
            // Update pending requests table
            updatePendingRequestsTable(data.pending_requests);
            
            // Update employee salary table
            updateEmployeeSalaryTable(data.employee_summaries);
            
        })
        .catch(error => {
            console.error('Error:', error);
            showAlert('Error refreshing data', 'error');
        });
}

/**
 * Update KPI cards with new data
 */
function updateKPICards(data) {
    // Update total employees
    const totalEmployeesCard = document.querySelector('.card.bg-primary .card-title');
    if (totalEmployeesCard) {
        totalEmployeesCard.textContent = data.total_employees;
    }
    
    // Update pending requests
    const pendingRequestsCard = document.querySelector('.card.bg-warning .card-title');
    if (pendingRequestsCard) {
        pendingRequestsCard.textContent = data.pending_count;
    }
    
    // Update total payroll
    const totalPayrollCard = document.querySelector('.card.bg-success .card-title');
    if (totalPayrollCard) {
        totalPayrollCard.textContent = '₹' + formatCurrency(data.total_payroll);
    }
    
    // Update average performance
    const avgPerformance = data.employee_summaries.length > 0 
        ? (data.employee_summaries.reduce((sum, emp) => sum + (emp.performance_score || 0), 0) / data.employee_summaries.length)
        : 0;
    const avgPerformanceCard = document.querySelector('.card.bg-info .card-title');
    if (avgPerformanceCard) {
        avgPerformanceCard.textContent = avgPerformance.toFixed(1);
    }
}

/**
 * Update pending requests table
 */
function updatePendingRequestsTable(pendingRequests) {
    // Find the pending requests section by looking for the specific header text
    const pendingSection = Array.from(document.querySelectorAll('.card')).find(card => {
        const header = card.querySelector('.card-header h5');
        return header && header.textContent.includes('Pending Salary Requests');
    });
    
    if (pendingRequests.length === 0) {
        // Hide the pending requests section if no pending requests
        if (pendingSection) {
            pendingSection.style.display = 'none';
        }
        return;
    }
    
    // Show the section if it was hidden
    if (pendingSection) {
        pendingSection.style.display = 'block';
    }
    
    // Update the table body - find the table with "Employee" header
    const tables = Array.from(document.querySelectorAll('.table'));
    const pendingTable = tables.find(table => {
        const headers = Array.from(table.querySelectorAll('th'));
        return headers.some(th => th.textContent.includes('Employee'));
    });
    
    const tbody = pendingTable ? pendingTable.querySelector('tbody') : null;
    if (!tbody) return;
    
    let html = '';
    pendingRequests.forEach(request => {
        const requestTypeClass = request.request_type === 'bonus' ? 'success' : 'primary';
        const requestDate = new Date(request.created_at).toLocaleDateString();
        
        html += `
            <tr>
                <td>
                    <div class="d-flex align-items-center">
                        <div class="avatar-sm bg-primary text-white rounded-circle d-flex align-items-center justify-content-center me-2">
                            ${request.employee_name[0].toUpperCase()}
                        </div>
                        <div>
                            <div class="fw-bold">${request.employee_name}</div>
                            <small class="text-muted">${request.employee_email}</small>
                        </div>
                    </div>
                </td>
                <td>
                    <span class="badge bg-${requestTypeClass}">
                        ${request.request_type.charAt(0).toUpperCase() + request.request_type.slice(1)}
                    </span>
                </td>
                <td class="fw-bold">₹${formatCurrency(request.requested_amount)}</td>
                <td>
                    <div class="text-truncate" style="max-width: 200px;" title="${request.reason}">
                        ${request.reason}
                    </div>
                </td>
                <td>${requestDate}</td>
                <td>
                    <button class="btn btn-sm btn-success me-1" onclick="approveRequest('${request._id}')">
                        <i class="fas fa-check"></i>
                    </button>
                    <button class="btn btn-sm btn-danger" onclick="rejectRequest('${request._id}')">
                        <i class="fas fa-times"></i>
                    </button>
                </td>
            </tr>
        `;
    });
    
    tbody.innerHTML = html;
}

/**
 * Update employee salary table
 */
function updateEmployeeSalaryTable(employeeSummaries) {
    const tbody = document.querySelector('#salaryTable tbody');
    if (!tbody) return;
    
    let html = '';
    employeeSummaries.forEach(summary => {
        const employee = summary.employee;
        const performanceScore = summary.performance_score;
        const performanceBadge = performanceScore 
            ? `<span class="badge bg-${performanceScore >= 80 ? 'success' : performanceScore >= 60 ? 'warning' : 'danger'}">
                ${performanceScore.toFixed(1)}%
               </span>`
            : '<span class="badge bg-secondary">N/A</span>';
        
        const valuePerRupee = summary.value_per_rupee 
            ? `<span class="badge bg-info">${summary.value_per_rupee.toFixed(3)}</span>`
            : '<span class="text-muted">—</span>';
        
        const photo = employee.photo 
            ? `<img src="/static/uploads/${employee.photo}" class="rounded-circle" width="40" height="40" alt="Photo">`
            : `<div class="avatar-sm bg-secondary text-white rounded-circle d-flex align-items-center justify-content-center">
                ${employee.name[0].toUpperCase()}
               </div>`;
        
        html += `
            <tr>
                <td>${photo}</td>
                <td class="fw-bold">${employee.name}</td>
                <td><code>${employee._id.substring(0, 8)}...</code></td>
                <td>${employee.department || ''}</td>
                <td class="fw-bold text-success">₹${formatCurrency(summary.net_salary)}</td>
                <td>₹${summary.hourly_rate.toFixed(2)}</td>
                <td>${performanceBadge}</td>
                <td>${valuePerRupee}</td>
                <td>
                    <div class="btn-group" role="group">
                        <button class="btn btn-sm btn-outline-primary" onclick="viewComponents('${employee._id}')">
                            <i class="fas fa-eye"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-warning" onclick="editComponents('${employee._id}')">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-info" onclick="viewHistory('${employee._id}')">
                            <i class="fas fa-history"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    });
    
    tbody.innerHTML = html;
}

/**
 * Utility functions
 */
function getComponentTypeClass(type) {
    const classes = {
        'base': 'bg-primary',
        'allowance': 'bg-success',
        'bonus': 'bg-info',
        'deduction': 'bg-danger'
    };
    return classes[type] || 'bg-secondary';
}

function formatCurrency(amount) {
    return parseFloat(amount).toLocaleString('en-IN', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}

function showAlert(message, type) {
    const alertClass = type === 'error' ? 'alert-danger' : 'alert-success';
    const alertHtml = `
        <div class="alert ${alertClass} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    // Remove existing alerts
    document.querySelectorAll('.alert').forEach(alert => alert.remove());
    
    // Add new alert
    const container = document.querySelector('.container-fluid') || document.body;
    container.insertAdjacentHTML('afterbegin', alertHtml);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        const alert = document.querySelector('.alert');
        if (alert) {
            alert.remove();
        }
    }, 5000);
}

// New atomic approve/reject functions
function approveRequest(requestId) {
    if (!confirm('Are you sure you want to approve this salary request?')) {
        return;
    }
    
    // Show loading state
    const approveBtn = document.querySelector(`button[onclick="approveRequest('${requestId}')"]`);
    const originalContent = approveBtn.innerHTML;
    approveBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    approveBtn.disabled = true;
    
    // Call approve endpoint
    fetch(`/salary/requests/${requestId}/approve`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({})
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Update UI on success
            updateUIAfterAction(data, requestId, 'approved');
            showToast('Request approved successfully!', 'success');
        } else {
            showToast(`Error: ${data.error}`, 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('Network error occurred', 'error');
    })
    .finally(() => {
        // Restore button state
        approveBtn.innerHTML = originalContent;
        approveBtn.disabled = false;
    });
}

function rejectRequest(requestId) {
    if (!confirm('Are you sure you want to reject this salary request?')) {
        return;
    }
    
    // Show loading state
    const rejectBtn = document.querySelector(`button[onclick="rejectRequest('${requestId}')"]`);
    const originalContent = rejectBtn.innerHTML;
    rejectBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    rejectBtn.disabled = true;
    
    // Call reject endpoint
    fetch(`/salary/requests/${requestId}/reject`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({})
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Update UI on success
            updateUIAfterAction(data, requestId, 'rejected');
            showToast('Request rejected successfully!', 'success');
        } else {
            showToast(`Error: ${data.error}`, 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('Network error occurred', 'error');
    })
    .finally(() => {
        // Restore button state
        rejectBtn.innerHTML = originalContent;
        rejectBtn.disabled = false;
    });
}

function updateUIAfterAction(data, requestId, action) {
    // Remove the request row from pending table
    const requestRow = document.querySelector(`button[onclick="${action === 'approved' ? 'approve' : 'reject'}Request('${requestId}')"]`).closest('tr');
    if (requestRow) {
        requestRow.remove();
    }
    
    // Update KPI cards
    updateKPICardsAfterAction(data);
    
    // Update employee salary table if approved
    if (action === 'approved' && data.employee_update) {
        updateEmployeeSalaryAfterApproval(data.employee_update);
    }
    
    // Hide pending requests section if no more pending requests
    if (data.pending_count === 0) {
        const pendingSection = Array.from(document.querySelectorAll('.card')).find(card => {
            const header = card.querySelector('.card-header h5');
            return header && header.textContent.includes('Pending Salary Requests');
        });
        if (pendingSection) {
            pendingSection.style.display = 'none';
        }
    }
}

function updateKPICardsAfterAction(data) {
    // Update pending requests count
    const pendingRequestsCard = document.querySelector('.card.bg-warning .card-title');
    if (pendingRequestsCard) {
        pendingRequestsCard.textContent = data.pending_count;
    }
    
    // Update total payroll
    const totalPayrollCard = document.querySelector('.card.bg-success .card-title');
    if (totalPayrollCard) {
        totalPayrollCard.textContent = '₹' + formatCurrency(data.payroll_total);
    }
}

function updateEmployeeSalaryAfterApproval(employeeUpdate) {
    // Find the employee row in the salary overview table
    const salaryTable = document.querySelector('#salaryTable tbody');
    if (!salaryTable) return;
    
    const rows = Array.from(salaryTable.querySelectorAll('tr'));
    const employeeRow = rows.find(row => {
        const employeeIdCell = row.querySelector('code');
        return employeeIdCell && employeeIdCell.textContent.includes(employeeUpdate.employee_id.substring(0, 8));
    });
    
    if (employeeRow) {
        // Update net salary
        const netSalaryCell = employeeRow.querySelector('td:nth-child(5)'); // Net Salary column
        if (netSalaryCell) {
            netSalaryCell.innerHTML = `<span class="fw-bold text-success">₹${formatCurrency(employeeUpdate.net_salary)}</span>`;
        }
        
        // Update hourly rate
        const hourlyRateCell = employeeRow.querySelector('td:nth-child(6)'); // Hourly Rate column
        if (hourlyRateCell) {
            const hourlyRate = employeeUpdate.net_salary / 160; // Assuming 160 hours per month
            hourlyRateCell.textContent = `₹${hourlyRate.toFixed(2)}`;
        }
    }
}

function showToast(message, type) {
    // Create toast element
    const toastHtml = `
        <div class="toast align-items-center text-white bg-${type === 'error' ? 'danger' : 'success'} border-0" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="d-flex">
                <div class="toast-body">
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        </div>
    `;
    
    // Create toast container if it doesn't exist
    let toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
        toastContainer.style.zIndex = '9999';
        document.body.appendChild(toastContainer);
    }
    
    // Add toast to container
    toastContainer.insertAdjacentHTML('beforeend', toastHtml);
    
    // Show the toast
    const toastElement = toastContainer.lastElementChild;
    const toast = new bootstrap.Toast(toastElement, { delay: 5000 });
    toast.show();
    
    // Remove toast element after it's hidden
    toastElement.addEventListener('hidden.bs.toast', () => {
        toastElement.remove();
    });
}
