"""
Salary Management Routes
Flask blueprint for salary management functionality
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session, flash, send_from_directory
from werkzeug.utils import secure_filename
import os
import json
from datetime import datetime, date
from functools import wraps

from .models import SalaryComponent, SalaryHistory, SalaryRequest, get_effective_components
from .services import (
    calculate_net_salary, calculate_hourly_rate, calculate_value_per_rupee,
    get_employee_performance_score, validate_salary_component, validate_salary_request,
    format_currency, get_salary_summary
)

# Import database and utilities - will be imported after app initialization

salary_bp = Blueprint('salary', __name__)

# File upload configuration for salary requests
SALARY_UPLOAD_FOLDER = 'static/uploads/salary_requests'
os.makedirs(SALARY_UPLOAD_FOLDER, exist_ok=True)
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

# Allowed file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Global variables for database and utilities
db = None
log_audit_event = None

def init_salary_module(database, audit_logger):
    """Initialize salary module with database and audit logger"""
    global db, log_audit_event
    db = database
    log_audit_event = audit_logger

def _get_mongo_client_or_none(db):
    """Check if database supports MongoDB transactions"""
    client = getattr(db, 'client', None)
    if client and hasattr(client, 'start_session'):
        return client
    return None

def admin_required(f):
    """Decorator to require admin privileges"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        
        if session.get('user_role') != 'admin':
            return jsonify({'error': 'Admin privileges required'}), 403
        
        return f(*args, **kwargs)
    return decorated_function


def employee_required(f):
    """Decorator to require employee authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        
        return f(*args, **kwargs)
    return decorated_function


@salary_bp.route('/admin')
@admin_required
def admin_dashboard():
    """Admin salary management dashboard"""
    try:
        # Get all employees with their salary summaries
        employees = list(db.employees.find({}, {'password': 0}))
        
        employee_summaries = []
        for employee in employees:
            summary = get_salary_summary(employee['_id'], db)
            if 'error' not in summary:
                employee_summaries.append({
                    'employee': employee,
                    'net_salary': summary['net_salary'],
                    'hourly_rate': summary['hourly_rate'],
                    'performance_score': summary['performance_score'],
                    'value_per_rupee': summary['value_per_rupee']
                })
        
        # Get pending salary requests
        pending_requests = list(db.salary_requests.find({'status': 'pending'}).sort('created_at', -1))
        
        # Add employee names to requests
        for req in pending_requests:
            employee = db.employees.find_one({'_id': req['employee_id']}, {'name': 1, 'email': 1})
            req['employee_name'] = employee['name'] if employee else 'Unknown'
            req['employee_email'] = employee['email'] if employee else 'Unknown'
        
        log_audit_event('VIEW_SALARY_ADMIN', 'salary_admin_dashboard', session['user_id'])
        
        return render_template('salary/salary_admin.html', 
                             employee_summaries=employee_summaries,
                             pending_requests=pending_requests)
        
    except Exception as e:
        flash(f'Error loading salary dashboard: {str(e)}', 'error')
        return redirect(url_for('dashboard'))


@salary_bp.route('/admin/<employee_id>/components')
@admin_required
def get_employee_components(employee_id):
    """Get salary components for an employee"""
    try:
        components = list(db.salary_components.find({'employee_id': employee_id}).sort('created_at', -1))
        return jsonify(components)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@salary_bp.route('/admin/<employee_id>/components', methods=['POST'])
@admin_required
def add_employee_component(employee_id):
    """Add or update a salary component for an employee"""
    try:
        data = request.get_json()
        data['employee_id'] = employee_id
        data['created_by'] = session['user_id']
        
        # Validate component data
        errors = validate_salary_component(data)
        if errors:
            return jsonify({'error': 'Validation failed', 'details': errors}), 400
        
        # Create component
        component = SalaryComponent(
            employee_id=employee_id,
            component_type=data['component_type'],
            label=data['label'],
            amount=float(data['amount']),
            effective_from=data['effective_from'],
            effective_to=data.get('effective_to'),
            created_by=session['user_id']
        )
        
        # Insert into database
        result = db.salary_components.insert_one(component.to_dict())
        
        # Log audit event
        log_audit_event('ADD_SALARY_COMPONENT', f'employee_{employee_id}', session['user_id'], {
            'component_type': data['component_type'],
            'label': data['label'],
            'amount': data['amount'],
            'effective_from': data['effective_from']
        })
        
        return jsonify({'message': 'Component added successfully', 'id': result.inserted_id})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@salary_bp.route('/admin/components/<component_id>', methods=['DELETE'])
@admin_required
def delete_component(component_id):
    """Delete a salary component"""
    try:
        # Get component for logging
        component = db.salary_components.find_one({'_id': component_id})
        if not component:
            return jsonify({'error': 'Component not found'}), 404
        
        # Delete component
        result = db.salary_components.delete_one({'_id': component_id})
        
        if result.deleted_count > 0:
            # Log audit event
            log_audit_event('DELETE_SALARY_COMPONENT', f'component_{component_id}', session['user_id'], {
                'employee_id': component['employee_id'],
                'component_type': component['component_type'],
                'label': component['label']
            })
            
            return jsonify({'message': 'Component deleted successfully'})
        else:
            return jsonify({'error': 'Component not found'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@salary_bp.route('/admin/<employee_id>/generate', methods=['POST'])
@admin_required
def generate_salary_history(employee_id):
    """Generate salary history snapshot for an employee"""
    try:
        data = request.get_json()
        period_start = data.get('period_start')
        period_end = data.get('period_end')
        
        if not period_start or not period_end:
            return jsonify({'error': 'period_start and period_end are required'}), 400
        
        # Get components for the period
        components = list(db.salary_components.find({'employee_id': employee_id}))
        effective_components = get_effective_components(components, period_end)
        
        # Calculate net salary
        net_amount = calculate_net_salary(effective_components, period_end)
        
        # Create salary history
        history = SalaryHistory(
            employee_id=employee_id,
            components_snapshot=effective_components,
            net_amount=net_amount,
            period_start=period_start,
            period_end=period_end
        )
        
        # Insert into database
        result = db.salary_history.insert_one(history.to_dict())
        
        # Log audit event
        log_audit_event('GENERATE_SALARY_HISTORY', f'employee_{employee_id}', session['user_id'], {
            'period_start': period_start,
            'period_end': period_end,
            'net_amount': net_amount
        })
        
        return jsonify({'message': 'Salary history generated successfully', 'id': result.inserted_id})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@salary_bp.route('/employee')
@employee_required
def employee_salary():
    """Employee salary page"""
    try:
        employee_id = session['user_id']
        summary = get_salary_summary(employee_id, db)
        
        if 'error' in summary:
            flash(f'Error loading salary data: {summary["error"]}', 'error')
            return redirect(url_for('dashboard'))
        
        # Get employee's salary requests
        requests = list(db.salary_requests.find({'employee_id': employee_id}).sort('created_at', -1))
        
        return render_template('salary/employee_salary.html', 
                             summary=summary,
                             requests=requests)
        
    except Exception as e:
        flash(f'Error loading salary page: {str(e)}', 'error')
        return redirect(url_for('dashboard'))


@salary_bp.route('/employee/request', methods=['POST'])
@employee_required
def submit_salary_request():
    """Submit a salary/bonus request"""
    try:
        employee_id = session['user_id']
        
        # Get form data
        request_type = request.form.get('request_type')
        requested_amount = request.form.get('requested_amount')
        reason = request.form.get('reason')
        
        # Validate data
        data = {
            'request_type': request_type,
            'requested_amount': requested_amount,
            'reason': reason
        }
        
        errors = validate_salary_request(data)
        if errors:
            return jsonify({'error': 'Validation failed', 'details': errors}), 400
        
        # Handle file upload
        attachment_filename = None
        if 'attachment' in request.files:
            file = request.files['attachment']
            if file and file.filename:
                if allowed_file(file.filename):
                    filename = secure_filename(f"{employee_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
                    file_path = os.path.join(SALARY_UPLOAD_FOLDER, filename)
                    file.save(file_path)
                    attachment_filename = filename
                else:
                    return jsonify({'error': 'Invalid file type. Allowed: PNG, JPG, JPEG, GIF, WEBP, PDF'}), 400
        
        # Create salary request
        salary_request = SalaryRequest(
            employee_id=employee_id,
            request_type=request_type,
            requested_amount=float(requested_amount),
            reason=reason,
            attachment_filename=attachment_filename
        )
        
        # Insert into database
        result = db.salary_requests.insert_one(salary_request.to_dict())
        
        # Log audit event
        log_audit_event('SUBMIT_SALARY_REQUEST', f'request_{result.inserted_id}', employee_id, {
            'request_type': request_type,
            'requested_amount': requested_amount,
            'has_attachment': bool(attachment_filename)
        })
        
        return jsonify({'message': 'Salary request submitted successfully'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@salary_bp.route('/requests/<request_id>/approve', methods=['POST'])
@admin_required
def approve_salary_request(request_id):
    """Approve a salary request with atomic operations"""
    try:
        from bson import ObjectId
        
        # Convert request_id to ObjectId if needed
        try:
            if isinstance(request_id, str) and len(request_id) == 24:
                request_obj_id = ObjectId(request_id)
            else:
                request_obj_id = request_id
        except:
            return jsonify({'success': False, 'error': 'Invalid request ID'}), 400
        
        # Check if MongoDB transactions are supported
        mongo_client = _get_mongo_client_or_none(db)
        
        if mongo_client:
            # Use MongoDB transactions for atomic operations
            with mongo_client.start_session() as session:
                with session.start_transaction():
                    return _process_approve_request(request_obj_id, session)
        else:
            # Fallback for MockDB/mongomock - use ordered operations with rollback
            return _process_approve_request_fallback(request_obj_id)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def _process_approve_request(request_obj_id, session=None):
    """Process approve request with MongoDB session support"""
    # Get the salary request
    salary_request = db.salary_requests.find_one({'_id': request_obj_id}, session=session)
    if not salary_request:
        return jsonify({'success': False, 'error': 'Request not found'}), 404
    
    if salary_request['status'] != 'pending':
        return jsonify({'success': False, 'error': 'Request already processed'}), 400
    
    # Update request status to approved
    db.salary_requests.update_one(
        {'_id': request_obj_id},
        {
            '$set': {
                'status': 'approved',
                'resolved_at': datetime.now()
            }
        },
        session=session
    )
    
    # Add salary component (bonus or hike)
    from .models import SalaryComponent
    from datetime import date
    
    if salary_request['request_type'] == 'hike':
        # For salary hike, update base salary
        current_components = list(db.salary_components.find({
            'employee_id': salary_request['employee_id'],
            'component_type': 'base'
        }).sort('created_at', -1).limit(1))
        
        current_base = current_components[0]['amount'] if current_components else 0
        new_base = current_base + salary_request['requested_amount']
        
        new_component = SalaryComponent(
            employee_id=salary_request['employee_id'],
            component_type='base',
            label='Base Salary (Updated)',
            amount=new_base,
            effective_from=date.today().isoformat(),
            created_by=session['user_id']
        )
        
    elif salary_request['request_type'] == 'bonus':
        # For bonus, add bonus component
        new_component = SalaryComponent(
            employee_id=salary_request['employee_id'],
            component_type='bonus',
            label='Approved Bonus',
            amount=salary_request['requested_amount'],
            effective_from=date.today().isoformat(),
            created_by=session['user_id']
        )
    
    # Insert the new component
    db.salary_components.insert_one(new_component.to_dict(), session=session)
    
    # Get updated employee summary for response
    employee_summary = get_salary_summary(salary_request['employee_id'], db)
    if 'error' in employee_summary:
        raise Exception(f"Error getting employee summary: {employee_summary['error']}")
    
    # Get updated counts
    pending_count = db.salary_requests.count_documents({'status': 'pending'}, session=session)
    
    # Calculate total payroll
    employees = list(db.employees.find({}, {'password': 0}, session=session))
    total_payroll = 0
    for emp in employees:
        summary = get_salary_summary(emp['_id'], db)
        if 'error' not in summary:
            total_payroll += summary['net_salary']
    
    # Log audit event
    log_audit_event('APPROVE_SALARY_REQUEST', f'request_{request_obj_id}', session['user_id'], {
        'employee_id': salary_request['employee_id'],
        'request_type': salary_request['request_type'],
        'requested_amount': salary_request['requested_amount']
    })
    
    return jsonify({
        'success': True,
        'payroll_total': total_payroll,
        'pending_count': pending_count,
        'employee_update': {
            'employee_id': salary_request['employee_id'],
            'net_salary': employee_summary['net_salary'],
            'request_type': salary_request['request_type'],
            'requested_amount': salary_request['requested_amount']
        }
    })

def _process_approve_request_fallback(request_obj_id):
    """Process approve request for MockDB/mongomock without transactions"""
    try:
        # Get the salary request
        salary_request = db.salary_requests.find_one({'_id': request_obj_id})
        if not salary_request:
            return jsonify({'success': False, 'error': 'Request not found'}), 404
        
        if salary_request['status'] != 'pending':
            return jsonify({'success': False, 'error': 'Request already processed'}), 400
        
        # Store original status for rollback
        original_status = salary_request['status']
        
        # Update request status to approved
        db.salary_requests.update_one(
            {'_id': request_obj_id},
            {
                '$set': {
                    'status': 'approved',
                    'resolved_at': datetime.now()
                }
            }
        )
        
        try:
            # Add salary component (bonus or hike)
            from .models import SalaryComponent
            from datetime import date
            
            if salary_request['request_type'] == 'hike':
                # For salary hike, update base salary
                current_components = list(db.salary_components.find({
                    'employee_id': salary_request['employee_id'],
                    'component_type': 'base'
                }).sort('created_at', -1).limit(1))
                
                current_base = current_components[0]['amount'] if current_components else 0
                new_base = current_base + salary_request['requested_amount']
                
                new_component = SalaryComponent(
                    employee_id=salary_request['employee_id'],
                    component_type='base',
                    label='Base Salary (Updated)',
                    amount=new_base,
                    effective_from=date.today().isoformat(),
                    created_by=session['user_id']
                )
                
            elif salary_request['request_type'] == 'bonus':
                # For bonus, add bonus component
                new_component = SalaryComponent(
                    employee_id=salary_request['employee_id'],
                    component_type='bonus',
                    label='Approved Bonus',
                    amount=salary_request['requested_amount'],
                    effective_from=date.today().isoformat(),
                    created_by=session['user_id']
                )
            
            # Insert the new component
            db.salary_components.insert_one(new_component.to_dict())
            
            # Get updated employee summary for response
            employee_summary = get_salary_summary(salary_request['employee_id'], db)
            if 'error' in employee_summary:
                raise Exception(f"Error getting employee summary: {employee_summary['error']}")
            
            # Get updated counts
            pending_count = db.salary_requests.count_documents({'status': 'pending'})
            
            # Calculate total payroll
            employees = list(db.employees.find({}, {'password': 0}))
            total_payroll = 0
            for emp in employees:
                summary = get_salary_summary(emp['_id'], db)
                if 'error' not in summary:
                    total_payroll += summary['net_salary']
            
            # Log audit event
            log_audit_event('APPROVE_SALARY_REQUEST', f'request_{request_obj_id}', session['user_id'], {
                'employee_id': salary_request['employee_id'],
                'request_type': salary_request['request_type'],
                'requested_amount': salary_request['requested_amount']
            })
            
            return jsonify({
                'success': True,
                'payroll_total': total_payroll,
                'pending_count': pending_count,
                'employee_update': {
                    'employee_id': salary_request['employee_id'],
                    'net_salary': employee_summary['net_salary'],
                    'request_type': salary_request['request_type'],
                    'requested_amount': salary_request['requested_amount']
                }
            })
            
        except Exception as e:
            # Rollback: restore original status
            db.salary_requests.update_one(
                {'_id': request_obj_id},
                {'$set': {'status': original_status}}
            )
            raise e
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@salary_bp.route('/requests/<request_id>/reject', methods=['POST'])
@admin_required
def reject_salary_request(request_id):
    """Reject a salary request with atomic operations"""
    try:
        from bson import ObjectId
        
        # Convert request_id to ObjectId if needed
        try:
            if isinstance(request_id, str) and len(request_id) == 24:
                request_obj_id = ObjectId(request_id)
            else:
                request_obj_id = request_id
        except:
            return jsonify({'success': False, 'error': 'Invalid request ID'}), 400
        
        # Check if MongoDB transactions are supported
        mongo_client = _get_mongo_client_or_none(db)
        
        if mongo_client:
            # Use MongoDB transactions for atomic operations
            with mongo_client.start_session() as session:
                with session.start_transaction():
                    return _process_reject_request(request_obj_id, session)
        else:
            # Fallback for MockDB/mongomock - use ordered operations with rollback
            return _process_reject_request_fallback(request_obj_id)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def _process_reject_request(request_obj_id, session=None):
    """Process reject request with MongoDB session support"""
    # Get the salary request
    salary_request = db.salary_requests.find_one({'_id': request_obj_id}, session=session)
    if not salary_request:
        return jsonify({'success': False, 'error': 'Request not found'}), 404
    
    if salary_request['status'] != 'pending':
        return jsonify({'success': False, 'error': 'Request already processed'}), 400
    
    # Update request status to rejected
    db.salary_requests.update_one(
        {'_id': request_obj_id},
        {
            '$set': {
                'status': 'rejected',
                'resolved_at': datetime.now()
            }
        },
        session=session
    )
    
    # Get updated counts (no payroll change for reject)
    pending_count = db.salary_requests.count_documents({'status': 'pending'}, session=session)
    
    # Calculate current total payroll (unchanged)
    employees = list(db.employees.find({}, {'password': 0}, session=session))
    total_payroll = 0
    for emp in employees:
        summary = get_salary_summary(emp['_id'], db)
        if 'error' not in summary:
            total_payroll += summary['net_salary']
    
    # Log audit event
    log_audit_event('REJECT_SALARY_REQUEST', f'request_{request_obj_id}', session['user_id'], {
        'employee_id': salary_request['employee_id'],
        'request_type': salary_request['request_type'],
        'requested_amount': salary_request['requested_amount']
    })
    
    return jsonify({
        'success': True,
        'payroll_total': total_payroll,
        'pending_count': pending_count,
        'employee_update': {
            'employee_id': salary_request['employee_id'],
            'request_type': salary_request['request_type'],
            'requested_amount': salary_request['requested_amount']
        }
    })

def _process_reject_request_fallback(request_obj_id):
    """Process reject request for MockDB/mongomock without transactions"""
    try:
        # Get the salary request
        salary_request = db.salary_requests.find_one({'_id': request_obj_id})
        if not salary_request:
            return jsonify({'success': False, 'error': 'Request not found'}), 404
        
        if salary_request['status'] != 'pending':
            return jsonify({'success': False, 'error': 'Request already processed'}), 400
        
        # Store original status for rollback
        original_status = salary_request['status']
        
        try:
            # Update request status to rejected
            db.salary_requests.update_one(
                {'_id': request_obj_id},
                {
                    '$set': {
                        'status': 'rejected',
                        'resolved_at': datetime.now()
                    }
                }
            )
            
            # Get updated counts (no payroll change for reject)
            pending_count = db.salary_requests.count_documents({'status': 'pending'})
            
            # Calculate current total payroll (unchanged)
            employees = list(db.employees.find({}, {'password': 0}))
            total_payroll = 0
            for emp in employees:
                summary = get_salary_summary(emp['_id'], db)
                if 'error' not in summary:
                    total_payroll += summary['net_salary']
            
            # Log audit event
            log_audit_event('REJECT_SALARY_REQUEST', f'request_{request_obj_id}', session['user_id'], {
                'employee_id': salary_request['employee_id'],
                'request_type': salary_request['request_type'],
                'requested_amount': salary_request['requested_amount']
            })
            
            return jsonify({
                'success': True,
                'payroll_total': total_payroll,
                'pending_count': pending_count,
                'employee_update': {
                    'employee_id': salary_request['employee_id'],
                    'request_type': salary_request['request_type'],
                    'requested_amount': salary_request['requested_amount']
                }
            })
            
        except Exception as e:
            # Rollback: restore original status
            db.salary_requests.update_one(
                {'_id': request_obj_id},
                {'$set': {'status': original_status}}
            )
            raise e
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@salary_bp.route('/admin/export/history')
@admin_required
def export_salary_history():
    """Export salary history as CSV"""
    try:
        import csv
        import io
        
        # Get all salary history
        history = list(db.salary_history.find().sort('generated_at', -1))
        
        # Create CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['Employee ID', 'Period Start', 'Period End', 'Net Amount', 'Generated At'])
        
        # Write data
        for record in history:
            writer.writerow([
                record['employee_id'],
                record['period_start'],
                record['period_end'],
                record['net_amount'],
                record['generated_at'].isoformat()
            ])
        
        # Return CSV
        output.seek(0)
        return output.getvalue(), 200, {
            'Content-Type': 'text/csv',
            'Content-Disposition': 'attachment; filename=salary_history.csv'
        }
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@salary_bp.route('/admin/refresh-data')
@admin_required
def refresh_salary_data():
    """Get updated salary data for AJAX refresh"""
    try:
        # Get all employees with their salary summaries
        employees = list(db.employees.find({}, {'password': 0}))
        
        employee_summaries = []
        for employee in employees:
            summary = get_salary_summary(employee['_id'], db)
            if 'error' not in summary:
                employee_summaries.append({
                    'employee': employee,
                    'net_salary': summary['net_salary'],
                    'hourly_rate': summary['hourly_rate'],
                    'performance_score': summary['performance_score'],
                    'value_per_rupee': summary['value_per_rupee']
                })
        
        # Get pending salary requests
        pending_requests = list(db.salary_requests.find({'status': 'pending'}).sort('created_at', -1))
        
        # Add employee names to requests
        for req in pending_requests:
            employee = db.employees.find_one({'_id': req['employee_id']}, {'name': 1, 'email': 1})
            req['employee_name'] = employee['name'] if employee else 'Unknown'
            req['employee_email'] = employee['email'] if employee else 'Unknown'
        
        # Calculate total payroll
        total_payroll = sum(summary['net_salary'] for summary in employee_summaries)
        
        return jsonify({
            'employee_summaries': employee_summaries,
            'pending_requests': pending_requests,
            'total_payroll': total_payroll,
            'total_employees': len(employee_summaries),
            'pending_count': len(pending_requests)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@salary_bp.route('/admin/export/payroll')
@admin_required
def export_payroll_snapshot():
    """Export current payroll snapshot as CSV"""
    try:
        import csv
        import io
        
        # Get all employees with current salary data
        employees = list(db.employees.find({}, {'password': 0}))
        
        # Create CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['Employee ID', 'Name', 'Email', 'Department', 'Net Salary', 'Hourly Rate', 'Performance Score'])
        
        # Write data
        for employee in employees:
            summary = get_salary_summary(employee['_id'], db)
            if 'error' not in summary:
                writer.writerow([
                    employee['_id'],
                    employee['name'],
                    employee['email'],
                    employee.get('department', ''),
                    summary['net_salary'],
                    summary['hourly_rate'],
                    summary['performance_score'] or 'N/A'
                ])
        
        # Return CSV
        output.seek(0)
        return output.getvalue(), 200, {
            'Content-Type': 'text/csv',
            'Content-Disposition': 'attachment; filename=payroll_snapshot.csv'
        }
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@salary_bp.route('/uploads/salary_requests/<filename>')
@employee_required
def download_salary_attachment(filename):
    """Download salary request attachment"""
    try:
        # Verify the file belongs to the current user or user is admin
        if session.get('user_role') != 'admin':
            # Check if the file belongs to current user
            request_record = db.salary_requests.find_one({'attachment_filename': filename})
            if not request_record or request_record['employee_id'] != session['user_id']:
                return jsonify({'error': 'Access denied'}), 403
        
        return send_from_directory(SALARY_UPLOAD_FOLDER, filename)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
