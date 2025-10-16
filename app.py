from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime, date
import json
import functools

# Database imports - choose one
# For MongoDB:
from pymongo import MongoClient
from bson import ObjectId

# For MySQL (uncomment if using MySQL):
# import mysql.connector
# from mysql.connector import Error

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'

# Database Configuration
# MongoDB Configuration
MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "employee_management"

# MySQL Configuration (uncomment if using MySQL)
# MYSQL_CONFIG = {
#     'host': 'localhost',
#     'database': 'employee_management',
#     'user': 'root',
#     'password': 'your_password'
# }

# Create a mock database object for demo purposes
class MockDB:
    def __init__(self):
        self.employees = MockCollection()
        self.leave_applications = MockCollection()
        self.attendance = MockCollection()

class MockCollection:
    def __init__(self):
        self.data = []
        self._id_counter = 1
        self._filtered_data = []
        self._sorted = False
        self._limited = False
    
    def find_one(self, query, projection=None):
        if query == {}:
            return None
        
        # Find the matching item
        result = None
        if 'email' in query:
            for item in self.data:
                if item.get('email') == query['email']:
                    result = item
                    break
        elif '_id' in query:
            for item in self.data:
                if item.get('_id') == query['_id']:
                    result = item
                    break
        
        # Handle projection (field selection)
        if result and projection:
            filtered_result = {}
            for key, value in result.items():
                # If projection value is 0, exclude the field
                if key in projection and projection[key] == 0:
                    continue
                # If projection value is 1, include the field
                elif key in projection and projection[key] == 1:
                    filtered_result[key] = value
                # If field not in projection, include it (default behavior)
                elif key not in projection:
                    filtered_result[key] = value
            result = filtered_result
        
        return result
    
    def find(self, query=None, projection=None):
        # Create a new cursor-like object for method chaining
        data_copy = self.data.copy()
        
        # Handle query filtering first
        if query:
            filtered_data = []
            for item in data_copy:
                match = True
                for key, value in query.items():
                    if item.get(key) != value:
                        match = False
                        break
                if match:
                    filtered_data.append(item)
            data_copy = filtered_data
        
        # Handle projection (field selection) - remove fields specified in projection
        if projection:
            filtered_data = []
            for item in data_copy:
                filtered_item = {}
                for key, value in item.items():
                    # If projection value is 0, exclude the field
                    if key in projection and projection[key] == 0:
                        continue
                    # If projection value is 1, include the field
                    elif key in projection and projection[key] == 1:
                        filtered_item[key] = value
                    # If field not in projection, include it (default behavior)
                    elif key not in projection:
                        filtered_item[key] = value
                filtered_data.append(filtered_item)
            data_copy = filtered_data
        
        cursor = MockCursor(data_copy)
        return cursor
    
    def count_documents(self, query):
        if not query:
            return len(self.data)
        
        count = 0
        for item in self.data:
            match = True
            for key, value in query.items():
                if item.get(key) != value:
                    match = False
                    break
            if match:
                count += 1
        return count
    
    def insert_one(self, document):
        import time
        import random
        # Generate a more unique ID using timestamp and random number
        timestamp = int(time.time() * 1000)  # milliseconds
        random_num = random.randint(1000, 9999)
        document['_id'] = f"mock_id_{timestamp}_{random_num}"
        self._id_counter += 1
        self.data.append(document)
        return type('Result', (), {'inserted_id': document['_id']})()
    
    def update_one(self, query, update):
        # Find the document to update
        for i, doc in enumerate(self.data):
            if '_id' in query and doc.get('_id') == query['_id']:
                # Apply the update operation
                if '$set' in update:
                    doc.update(update['$set'])
                return type('Result', (), {'modified_count': 1})()
        return type('Result', (), {'modified_count': 0})()

class MockCursor:
    def __init__(self, data):
        self.data = data
    
    def sort(self, field, direction):
        # Sort the data based on the field and direction
        if direction == -1:  # Descending
            self.data.sort(key=lambda x: x.get(field, ''), reverse=True)
        else:  # Ascending
            self.data.sort(key=lambda x: x.get(field, ''), reverse=False)
        return self

    def limit(self, n):
        # Limit the number of results
        self.data = self.data[:n]
        return self
    
    def __iter__(self):
        # Make the cursor iterable
        return iter(self.data)
    
    def __list__(self):
        # Support list() conversion
        return self.data

# Initialize MongoDB
try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)  # 2 second timeout
    db = client[DB_NAME]
    # Test the connection
    client.admin.command('ping')
    print("Connected to MongoDB successfully!")
except Exception as e:
    print(f"MongoDB connection error: {e}")
    print("Please install MongoDB or set up MongoDB Atlas")
    print("For now, the app will run in demo mode without database")
    db = MockDB()
    
    # Add demo users to mock database
    admin_user = {
        'name': 'Admin User',
        'email': 'admin@company.com',
        'phone': '1234567890',
        'department': 'IT',
        'role': 'admin',
        'password': generate_password_hash('123456'),
        'created_at': datetime.now()
    }
    
    employee_user = {
        'name': 'John Doe',
        'email': 'john@company.com',
        'phone': '0987654321',
        'department': 'HR',
        'role': 'employee',
        'password': generate_password_hash('654321'),
        'created_at': datetime.now()
    }
    
    admin_result = db.employees.insert_one(admin_user)
    employee_result = db.employees.insert_one(employee_user)
    
    # Add some sample leave applications using the actual employee ID
    sample_leaves = [
        {
            'employee_id': employee_result.inserted_id,  # John Doe's actual ID
            'from_date': '2025-10-15',
            'to_date': '2025-10-17',
            'leave_type': 'Sick Leave',
            'reason': 'Medical appointment',
            'status': 'Approved',
            'applied_at': datetime.now()
        },
        {
            'employee_id': employee_result.inserted_id,  # John Doe's actual ID
            'from_date': '2025-10-20',
            'to_date': '2025-10-22',
            'leave_type': 'Personal Leave',
            'reason': 'Family event',
            'status': 'Pending',
            'applied_at': datetime.now()
        }
    ]
    
    for leave in sample_leaves:
        db.leave_applications.insert_one(leave)
    
    print("Demo users created!")
    print("Admin: admin@company.com / 123456")
    print("Employee: john@company.com / 654321")

# Initialize MySQL (uncomment if using MySQL)
# def get_mysql_connection():
#     try:
#         connection = mysql.connector.connect(**MYSQL_CONFIG)
#         return connection
#     except Error as e:
#         print(f"MySQL connection error: {e}")
#         return None

# Admin validation decorator
def admin_required(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first!', 'error')
            return redirect(url_for('login'))
        
        if session.get('user_role') != 'admin':
            flash('Access denied! Admin privileges required.', 'error')
            log_audit_event('UNAUTHORIZED_ACCESS', f.__name__, session.get('user_id', 'unknown'))
            return redirect(url_for('dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function

# Audit logging function
def log_audit_event(action, target, actor_id, details=None):
    """Log administrative actions for audit trail"""
    try:
        # Get actor information
        actor = db.employees.find_one({'_id': actor_id}, {'name': 1, 'email': 1}) if actor_id != 'unknown' else None
        actor_name = actor['name'] if actor else 'Unknown User'
        actor_email = actor['email'] if actor else 'unknown@unknown.com'
        
        audit_log = {
            'action': action,
            'target': target,
            'actor_id': actor_id,
            'actor_name': actor_name,
            'actor_email': actor_email,
            'timestamp': datetime.now(),
            'details': details or {},
            'ip_address': request.remote_addr if request else 'unknown'
        }
        
        # Store in audit collection
        if hasattr(db, 'audit_logs'):
            db.audit_logs.insert_one(audit_log)
        else:
            # For mock database, create audit_logs collection
            if not hasattr(db, 'audit_logs'):
                db.audit_logs = MockCollection()
            db.audit_logs.insert_one(audit_log)
            
        print(f"AUDIT: {action} by {actor_name} ({actor_email}) on {target} at {audit_log['timestamp']}")
        
    except Exception as e:
        print(f"Audit logging error: {e}")

# Check if user can be deleted (not admin)
def can_delete_user(user_id):
    """Check if a user can be deleted (non-admin users only)"""
    try:
        user = db.employees.find_one({'_id': user_id}, {'role': 1})
        return user and user.get('role') != 'admin'
    except:
        return False

# Database Models
class Employee:
    def __init__(self, name, email, phone, department, role, password=None):
        self.name = name
        self.email = email
        self.phone = phone
        self.department = department
        self.role = role
        self.password = password
        self.created_at = datetime.now()

    def to_dict(self):
        return {
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'department': self.department,
            'role': self.role,
            'password': self.password,
            'created_at': self.created_at
        }

class Attendance:
    def __init__(self, employee_id, date, status, check_in, check_out):
        self.employee_id = employee_id
        self.date = date
        self.status = status
        self.check_in = check_in
        self.check_out = check_out

    def to_dict(self):
        return {
            'employee_id': self.employee_id,
            'date': self.date,
            'status': self.status,
            'check_in': self.check_in,
            'check_out': self.check_out
        }

class LeaveApplication:
    def __init__(self, employee_id, from_date, to_date, leave_type, reason, status="Pending"):
        self.employee_id = employee_id
        self.from_date = from_date
        self.to_date = to_date
        self.leave_type = leave_type
        self.reason = reason
        self.status = status
        self.applied_at = datetime.now()

    def to_dict(self):
        return {
            'employee_id': self.employee_id,
            'from_date': self.from_date,
            'to_date': self.to_date,
            'leave_type': self.leave_type,
            'reason': self.reason,
            'status': self.status,
            'applied_at': self.applied_at
        }

# Routes
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        # MongoDB query
        user = db.employees.find_one({'email': email})
        
        # MySQL query (uncomment if using MySQL)
        # connection = get_mysql_connection()
        # if connection:
        #     cursor = connection.cursor(dictionary=True)
        #     cursor.execute("SELECT * FROM employees WHERE email = %s", (email,))
        #     user = cursor.fetchone()
        #     connection.close()
        
        if user and 'password' in user and check_password_hash(user['password'], password):
            session['user_id'] = str(user['_id'])  # MongoDB
            # session['user_id'] = user['id']  # MySQL
            session['user_name'] = user['name']
            session['user_role'] = user['role']
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials!', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        
        # Check if user already exists
        existing_user = db.employees.find_one({'email': email})
        if existing_user:
            flash('Email already registered!', 'error')
            return redirect(url_for('login'))
        
        # Create new employee
        new_employee = Employee(
            name=name,
            email=email,
            phone='',  # Default empty phone
            department='General',  # Default department
            role='employee',  # Default role
            password=generate_password_hash(password)
        )
        
        db.employees.insert_one(new_employee.to_dict())
        flash('Registration successful! Please login with your credentials.', 'success')
        return redirect(url_for('login'))
    
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully!', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Get dashboard statistics
    total_employees = db.employees.count_documents({})
    pending_leaves = db.leave_applications.count_documents({'status': 'Pending'})
    
    # Recent activities
    recent_leaves = list(db.leave_applications.find().sort('applied_at', -1).limit(5))
    
    # Get employee names for recent leaves
    for leave in recent_leaves:
        employee = db.employees.find_one({'_id': leave['employee_id']})
        leave['employee_name'] = employee['name'] if employee else 'Unknown'
    
    return render_template('dashboard.html', 
                         total_employees=total_employees,
                         pending_leaves=pending_leaves,
                         recent_leaves=recent_leaves)

@app.route('/employees')
@admin_required
def employees():
    employees = list(db.employees.find({}, {'password': 0}))
    log_audit_event('VIEW_EMPLOYEES', 'employee_list', session['user_id'])
    return render_template('employees.html', employees=employees)

@app.route('/leave_management')
@admin_required
def leave_management():
    # Get all leave applications with employee names
    leave_applications = list(db.leave_applications.find().sort('applied_at', -1))
    
    for leave in leave_applications:
        employee = db.employees.find_one({'_id': leave['employee_id']})
        leave['employee_name'] = employee['name'] if employee else 'Unknown'
        leave['employee_email'] = employee['email'] if employee else 'Unknown'
    
    log_audit_event('VIEW_LEAVE_MANAGEMENT', 'leave_applications', session['user_id'])
    return render_template('leave_management.html', leave_applications=leave_applications)

@app.route('/approve_leave/<leave_id>')
@admin_required
def approve_leave(leave_id):
    # Update leave status to approved
    result = db.leave_applications.update_one({'_id': leave_id}, {'$set': {'status': 'Approved'}})
    
    if result.modified_count > 0:
        flash('Leave application approved!', 'success')
        log_audit_event('APPROVE_LEAVE', f'leave_{leave_id}', session['user_id'], {'leave_id': leave_id})
    else:
        flash('Leave application not found!', 'error')
    
    return redirect(url_for('leave_management'))

@app.route('/reject_leave/<leave_id>')
@admin_required
def reject_leave(leave_id):
    # Update leave status to rejected
    result = db.leave_applications.update_one({'_id': leave_id}, {'$set': {'status': 'Rejected'}})
    
    if result.modified_count > 0:
        flash('Leave application rejected!', 'info')
        log_audit_event('REJECT_LEAVE', f'leave_{leave_id}', session['user_id'], {'leave_id': leave_id})
    else:
        flash('Leave application not found!', 'error')
    
    return redirect(url_for('leave_management'))

@app.route('/personal_info')
def personal_info():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Handle both real MongoDB ObjectIds and mock IDs
    try:
        # Try to use as ObjectId first (for real MongoDB)
        employee = db.employees.find_one({'_id': ObjectId(session['user_id'])}, {'password': 0})
    except:
        # If that fails, use as string (for mock database)
        employee = db.employees.find_one({'_id': session['user_id']}, {'password': 0})
    
    return render_template('personal_info.html', employee=employee)

@app.route('/attendance')
def attendance():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Get attendance records for current user
    attendance_records = list(db.attendance.find({'employee_id': session['user_id']}).sort('date', -1))
    return render_template('attendance.html', attendance_records=attendance_records)

@app.route('/finance')
def finance():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Sample finance data
    finance_data = [
        {'component': 'Base Salary', 'amount': 70000, 'effective_from': '2025-01-01'},
        {'component': 'Bonus', 'amount': 5000, 'effective_from': '2025-06-01'},
        {'component': 'Deductions', 'amount': -1200, 'effective_from': '2025-02-01'}
    ]
    
    return render_template('finance.html', finance_data=finance_data)

@app.route('/leave_application', methods=['GET', 'POST'])
def leave_application():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        from_date = request.form['from_date']
        to_date = request.form['to_date']
        leave_type = request.form['leave_type']
        reason = request.form['reason']
        
        leave_app = LeaveApplication(
            session['user_id'],
            from_date,
            to_date,
            leave_type,
            reason
        )
        
        db.leave_applications.insert_one(leave_app.to_dict())
        flash('Leave application submitted successfully!', 'success')
        return redirect(url_for('leave_application'))
    
    # Get user's leave applications
    user_leaves = list(db.leave_applications.find({'employee_id': session['user_id']}).sort('applied_at', -1))
    return render_template('leave_application.html', user_leaves=user_leaves)

@app.route('/projects')
def projects():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Sample projects data
    projects = [
        {'id': 'P-001', 'name': 'Website Redesign', 'owner': 'John Doe', 'status': 'Active'},
        {'id': 'P-002', 'name': 'Mobile App', 'owner': 'Jane Smith', 'status': 'Completed'},
        {'id': 'P-003', 'name': 'Database Migration', 'owner': 'Bob Johnson', 'status': 'Planning'}
    ]
    
    return render_template('projects.html', projects=projects)

@app.route('/add_attendance', methods=['POST'])
def add_attendance():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.get_json()
    attendance = Attendance(
        session['user_id'],
        data['date'],
        data['status'],
        data['check_in'],
        data['check_out']
    )
    
    db.attendance.insert_one(attendance.to_dict())
    return jsonify({'message': 'Attendance recorded successfully'})

@app.route('/add_employee', methods=['POST'])
@admin_required
def add_employee():
    data = request.get_json()
    
    # Check if email already exists
    existing_employee = db.employees.find_one({'email': data['email']})
    if existing_employee:
        return jsonify({'error': 'Email already exists'}), 400
    
    employee = Employee(
        data['name'],
        data['email'],
        data['phone'],
        data['department'],
        data['role'],
        generate_password_hash(data['password'])
    )
    
    result = db.employees.insert_one(employee.to_dict())
    
    # Log the action
    log_audit_event('ADD_EMPLOYEE', f'employee_{result.inserted_id}', session['user_id'], {
        'employee_name': data['name'],
        'employee_email': data['email'],
        'department': data['department'],
        'role': data['role']
    })
    
    return jsonify({'message': 'Employee added successfully'})

@app.route('/update_employee/<employee_id>', methods=['POST'])
@admin_required
def update_employee(employee_id):
    data = request.get_json()
    
    # Get current employee data for logging
    current_employee = db.employees.find_one({'_id': employee_id}, {'password': 0})
    if not current_employee:
        return jsonify({'error': 'Employee not found'}), 404
    
    # Check if email is being changed and if it already exists
    if data.get('email') != current_employee.get('email'):
        existing_employee = db.employees.find_one({'email': data['email']})
        if existing_employee:
            return jsonify({'error': 'Email already exists'}), 400
    
    # Prepare update data
    update_data = {
        'name': data['name'],
        'email': data['email'],
        'phone': data['phone'],
        'department': data['department'],
        'role': data['role']
    }
    
    # Add password if provided
    if data.get('password'):
        update_data['password'] = generate_password_hash(data['password'])
    
    # Update the employee
    result = db.employees.update_one({'_id': employee_id}, {'$set': update_data})
    
    if result.modified_count > 0:
        # Log the action
        log_audit_event('UPDATE_EMPLOYEE', f'employee_{employee_id}', session['user_id'], {
            'employee_name': data['name'],
            'employee_email': data['email'],
            'department': data['department'],
            'role': data['role'],
            'password_updated': bool(data.get('password')),
            'previous_data': current_employee
        })
        
        return jsonify({'message': 'Employee updated successfully'})
    else:
        return jsonify({'error': 'No changes made'}), 400

@app.route('/delete_employee/<employee_id>', methods=['POST'])
@admin_required
def delete_employee(employee_id):
    # Check if user can be deleted (not admin)
    if not can_delete_user(employee_id):
        return jsonify({'error': 'Cannot delete admin accounts'}), 403
    
    # Get employee data for logging
    employee = db.employees.find_one({'_id': employee_id}, {'password': 0})
    if not employee:
        return jsonify({'error': 'Employee not found'}), 404
    
    # Delete the employee
    result = db.employees.delete_one({'_id': employee_id})
    
    if result.deleted_count > 0:
        # Log the action
        log_audit_event('DELETE_EMPLOYEE', f'employee_{employee_id}', session['user_id'], {
            'deleted_employee_name': employee['name'],
            'deleted_employee_email': employee['email'],
            'deleted_employee_department': employee.get('department'),
            'deleted_employee_role': employee.get('role')
        })
        
        return jsonify({'message': 'Employee deleted successfully'})
    else:
        return jsonify({'error': 'Employee not found'}), 404

@app.route('/audit_logs')
@admin_required
def audit_logs():
    """View audit logs - admin only"""
    logs = list(db.audit_logs.find().sort('timestamp', -1).limit(100))
    log_audit_event('VIEW_AUDIT_LOGS', 'audit_logs', session['user_id'])
    return render_template('audit_logs.html', logs=logs)

if __name__ == '__main__':
    # Create sample data if database is empty
    if db.employees.count_documents({}) == 0:
        admin_employee = Employee(
            'Admin User',
            'admin@company.com',
            '1234567890',
            'IT',
            'admin',
            generate_password_hash('123456')
        )
        db.employees.insert_one(admin_employee.to_dict())
        
        regular_employee = Employee(
            'John Doe',
            'john@company.com',
            '0987654321',
            'HR',
            'employee',
            generate_password_hash('654321')
        )
        db.employees.insert_one(regular_employee.to_dict())
        print("Sample data created!")
        print("Admin: admin@company.com / 123456")
        print("Employee: john@company.com / 654321")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
