from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
from datetime import datetime, date
import json
import functools
import uuid


# Database imports - choose one
# For MongoDB:
from pymongo import MongoClient
from bson import ObjectId

# For MySQL (uncomment if using MySQL):
# import mysql.connector
# from mysql.connector import Error

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'

# File upload configuration
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Create uploads directory if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Helper functions for file handling
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_employee_photo(file, employee_id):
    """Save employee photo and return the filename"""
    if file and allowed_file(file.filename):
        # Generate unique filename
        file_extension = file.filename.rsplit('.', 1)[1].lower()
        filename = f"employee_{employee_id}_{uuid.uuid4().hex}.{file_extension}"
        
        # Save file
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        return filename
    return None

def delete_employee_photo(filename):
    """Delete employee photo file"""
    if filename:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(file_path):
            os.remove(file_path)

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
        self.performance_reviews = MockCollection()
        self.audit_logs = MockCollection()
        self.salary_components = MockCollection()
        self.salary_history = MockCollection()
        self.salary_requests = MockCollection()

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
    
    def delete_one(self, query):
        # Find and delete the document
        for i, doc in enumerate(self.data):
            if '_id' in query and doc.get('_id') == query['_id']:
                del self.data[i]
                return type('Result', (), {'deleted_count': 1})()
        return type('Result', (), {'deleted_count': 0})()

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
    
    # Add some sample performance reviews
    sample_reviews = [
        {
            'employee_id': employee_result.inserted_id,  # John Doe's actual ID
            'reviewer_id': admin_result.inserted_id,     # Admin's ID
            'rating': 4,
            'goals_achieved': 'Successfully completed Q3 project deliverables and improved team collaboration.',
            'strengths': 'Strong technical skills, good communication, reliable team player.',
            'areas_for_improvement': 'Could improve time management and take more initiative on complex tasks.',
            'comments': 'John has shown consistent performance and growth this quarter.',
            'review_period': 'Q3 2025',
            'created_at': datetime.now()
        },
        {
            'employee_id': employee_result.inserted_id,  # John Doe's actual ID
            'reviewer_id': admin_result.inserted_id,     # Admin's ID
            'rating': 5,
            'goals_achieved': 'Exceeded expectations on all assigned projects and mentored junior team members.',
            'strengths': 'Excellent leadership skills, innovative problem-solving, great attention to detail.',
            'areas_for_improvement': 'Continue developing advanced technical skills.',
            'comments': 'Outstanding performance this quarter. John is a valuable asset to the team.',
            'review_period': 'Q2 2025',
            'created_at': datetime.now()
        }
    ]
    
    for review in sample_reviews:
        db.performance_reviews.insert_one(review)
    
    # Add sample salary components
    sample_salary_components = [
        {
            'employee_id': admin_result.inserted_id,  # Admin's ID
            'component_type': 'base',
            'label': 'Base Salary',
            'amount': 80000,
            'effective_from': '2025-01-01',
            'effective_to': None,
            'created_by': admin_result.inserted_id,
            'created_at': datetime.now()
        },
        {
            'employee_id': admin_result.inserted_id,  # Admin's ID
            'component_type': 'allowance',
            'label': 'Transport Allowance',
            'amount': 5000,
            'effective_from': '2025-01-01',
            'effective_to': None,
            'created_by': admin_result.inserted_id,
            'created_at': datetime.now()
        },
        {
            'employee_id': employee_result.inserted_id,  # John Doe's ID
            'component_type': 'base',
            'label': 'Base Salary',
            'amount': 50000,
            'effective_from': '2025-01-01',
            'effective_to': None,
            'created_by': admin_result.inserted_id,
            'created_at': datetime.now()
        },
        {
            'employee_id': employee_result.inserted_id,  # John Doe's ID
            'component_type': 'allowance',
            'label': 'Transport Allowance',
            'amount': 3000,
            'effective_from': '2025-01-01',
            'effective_to': None,
            'created_by': admin_result.inserted_id,
            'created_at': datetime.now()
        },
        {
            'employee_id': employee_result.inserted_id,  # John Doe's ID
            'component_type': 'deduction',
            'label': 'Tax Deduction',
            'amount': 5000,
            'effective_from': '2025-01-01',
            'effective_to': None,
            'created_by': admin_result.inserted_id,
            'created_at': datetime.now()
        }
    ]
    
    for component in sample_salary_components:
        db.salary_components.insert_one(component)
    
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
    def __init__(self, name, email, phone, department, role, password=None, photo=None):
        self.name = name
        self.email = email
        self.phone = phone
        self.department = department
        self.role = role
        self.password = password
        self.photo = photo
        self.created_at = datetime.now()

    def to_dict(self):
        return {
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'department': self.department,
            'role': self.role,
            'password': self.password,
            'photo': self.photo,
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

class PerformanceReview:
    def __init__(self, employee_id, reviewer_id, rating, goals_achieved, strengths, areas_for_improvement, comments, review_period):
        self.employee_id = employee_id
        self.reviewer_id = reviewer_id
        self.rating = rating  # 1-5 scale
        self.goals_achieved = goals_achieved
        self.strengths = strengths
        self.areas_for_improvement = areas_for_improvement
        self.comments = comments
        self.review_period = review_period
        self.created_at = datetime.now()

    def to_dict(self):
        return {
            'employee_id': self.employee_id,
            'reviewer_id': self.reviewer_id,
            'rating': self.rating,
            'goals_achieved': self.goals_achieved,
            'strengths': self.strengths,
            'areas_for_improvement': self.areas_for_improvement,
            'comments': self.comments,
            'review_period': self.review_period,
            'created_at': self.created_at
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
    
    # Safety check - if employee not found, redirect with error message
    if not employee:
        flash('Employee record not found. Please contact administrator.', 'error')
        return redirect(url_for('dashboard'))
    
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
        {'component': 'Base Pay', 'amount': 70000, 'effective_from': '2025-01-01'},
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

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Serve uploaded files"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/upload_photo', methods=['POST'])
def upload_photo():
    """Upload employee photo"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    if 'photo' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['photo']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type. Allowed: PNG, JPG, JPEG, GIF, WEBP'}), 400
    
    try:
        # Save the photo
        filename = save_employee_photo(file, session['user_id'])
        if not filename:
            return jsonify({'error': 'Failed to save file'}), 500
        
        # Get current employee data
        employee = db.employees.find_one({'_id': session['user_id']})
        if not employee:
            return jsonify({'error': 'Employee not found'}), 404
        
        # Delete old photo if exists
        if employee.get('photo'):
            delete_employee_photo(employee['photo'])
        
        # Update employee record with new photo
        db.employees.update_one(
            {'_id': session['user_id']}, 
            {'$set': {'photo': filename}}
        )
        
        # Log the action
        log_audit_event('UPLOAD_PHOTO', f'employee_{session["user_id"]}', session['user_id'], {
            'filename': filename
        })
        
        return jsonify({
            'message': 'Photo uploaded successfully',
            'filename': filename,
            'url': url_for('uploaded_file', filename=filename)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/performance')
@admin_required
def performance():
    """Performance tracking dashboard - admin only"""
    try:
        # Get all employees with their performance data
        employees = list(db.employees.find({}, {'password': 0}))
        
        # Get performance reviews for each employee
        for employee in employees:
            if employee and employee.get('_id'):
                reviews = list(db.performance_reviews.find({'employee_id': employee['_id']}).sort('created_at', -1))
                employee['reviews'] = reviews
                
                # Calculate average rating
                if reviews:
                    total_rating = sum(review['rating'] for review in reviews)
                    employee['average_rating'] = round(total_rating / len(reviews), 1)
                else:
                    employee['average_rating'] = 0
            else:
                employee['reviews'] = []
                employee['average_rating'] = 0
        
        log_audit_event('VIEW_PERFORMANCE', 'performance_dashboard', session['user_id'])
        return render_template('performance.html', employees=employees)
        
    except Exception as e:
        print(f"Error in performance route: {e}")
        flash('Error loading performance data. Please try again.', 'error')
        return redirect(url_for('dashboard'))

@app.route('/add_performance_review', methods=['POST'])
@admin_required
def add_performance_review():
    """Add a new performance review"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['employee_id', 'rating', 'goals_achieved', 'strengths', 'areas_for_improvement', 'comments', 'review_period']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # Validate rating (1-5)
        if not (1 <= int(data['rating']) <= 5):
            return jsonify({'error': 'Rating must be between 1 and 5'}), 400
        
        # Create performance review
        review = PerformanceReview(
            employee_id=data['employee_id'],
            reviewer_id=session['user_id'],
            rating=int(data['rating']),
            goals_achieved=data['goals_achieved'],
            strengths=data['strengths'],
            areas_for_improvement=data['areas_for_improvement'],
            comments=data['comments'],
            review_period=data['review_period']
        )
        
        # Insert into database
        result = db.performance_reviews.insert_one(review.to_dict())
        
        # Log the action
        log_audit_event('ADD_PERFORMANCE_REVIEW', f'employee_{data["employee_id"]}', session['user_id'], {
            'employee_id': data['employee_id'],
            'rating': data['rating'],
            'review_period': data['review_period']
        })
        
        return jsonify({'message': 'Performance review added successfully'})
        
    except Exception as e:
        print(f"Error adding performance review: {e}")
        return jsonify({'error': 'Failed to add performance review'}), 500

@app.route('/get_performance_reviews/<employee_id>')
@admin_required
def get_performance_reviews(employee_id):
    """Get performance reviews for a specific employee"""
    try:
        reviews = list(db.performance_reviews.find({'employee_id': employee_id}).sort('created_at', -1))
        
        # Add reviewer names
        for review in reviews:
            reviewer = db.employees.find_one({'_id': review['reviewer_id']}, {'name': 1})
            review['reviewer_name'] = reviewer['name'] if reviewer else 'Unknown'
        
        return jsonify(reviews)
    except Exception as e:
        print(f"Error getting performance reviews: {e}")
        return jsonify({'error': 'Failed to load performance reviews'}), 500

@app.route('/analytics')
@admin_required
def analytics():
    """Department-wise analytics dashboard - admin only"""
    try:
        # Get all employees
        employees = list(db.employees.find({}, {'password': 0}))
        
        # Department statistics
        departments = {}
        for employee in employees:
            if not employee or not employee.get('_id'):
                continue
                
            dept = employee.get('department', 'Unknown')
            if dept not in departments:
                departments[dept] = {
                    'count': 0,
                    'employees': [],
                    'total_rating': 0,
                    'review_count': 0
                }
            
            departments[dept]['count'] += 1
            departments[dept]['employees'].append(employee)
            
            # Get performance data for this employee
            reviews = list(db.performance_reviews.find({'employee_id': employee['_id']}))
            if reviews:
                avg_rating = sum(review['rating'] for review in reviews) / len(reviews)
                departments[dept]['total_rating'] += avg_rating
                departments[dept]['review_count'] += len(reviews)
        
        # Calculate department averages
        for dept in departments:
            if departments[dept]['count'] > 0:
                departments[dept]['avg_rating'] = round(departments[dept]['total_rating'] / departments[dept]['count'], 1)
            else:
                departments[dept]['avg_rating'] = 0
        
        # Leave statistics by department
        leave_stats = {}
        for dept in departments:
            leave_stats[dept] = {
                'total_leaves': 0,
                'approved_leaves': 0,
                'pending_leaves': 0,
                'rejected_leaves': 0
            }
            
            for employee in departments[dept]['employees']:
                if employee and employee.get('_id'):
                    leaves = list(db.leave_applications.find({'employee_id': employee['_id']}))
                    leave_stats[dept]['total_leaves'] += len(leaves)
                    
                    for leave in leaves:
                        status = leave.get('status', 'Pending')
                        if status == 'Approved':
                            leave_stats[dept]['approved_leaves'] += 1
                        elif status == 'Pending':
                            leave_stats[dept]['pending_leaves'] += 1
                        elif status == 'Rejected':
                            leave_stats[dept]['rejected_leaves'] += 1
        
        # Attendance statistics by department
        attendance_stats = {}
        for dept in departments:
            attendance_stats[dept] = {
                'total_records': 0,
                'present_days': 0,
                'absent_days': 0
            }
            
            for employee in departments[dept]['employees']:
                if employee and employee.get('_id'):
                    attendance = list(db.attendance.find({'employee_id': employee['_id']}))
                    attendance_stats[dept]['total_records'] += len(attendance)
                    
                    for record in attendance:
                        if record.get('status') == 'Present':
                            attendance_stats[dept]['present_days'] += 1
                        else:
                            attendance_stats[dept]['absent_days'] += 1
        
        log_audit_event('VIEW_ANALYTICS', 'analytics_dashboard', session['user_id'])
        return render_template('analytics.html', 
                             departments=departments, 
                             leave_stats=leave_stats, 
                             attendance_stats=attendance_stats)
                             
    except Exception as e:
        print(f"Error in analytics route: {e}")
        flash('Error loading analytics data. Please try again.', 'error')
        return redirect(url_for('dashboard'))

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
        admin_result = db.employees.insert_one(admin_employee.to_dict())
        admin_id = admin_result.inserted_id
        
        regular_employee = Employee(
            'John Doe',
            'john@company.com',
            '0987654321',
            'HR',
            'employee',
            generate_password_hash('654321')
        )
        employee_result = db.employees.insert_one(regular_employee.to_dict())
        employee_id = employee_result.inserted_id
        
        # Create sample salary components
        from salary.models import SalaryComponent
        base_salary = SalaryComponent(
            employee_id=str(employee_id),
            component_type='base',
            label='Base Salary',
            amount=45000.0,
            effective_from='2024-01-01',
            created_by=str(admin_id)
        )
        db.salary_components.insert_one(base_salary.to_dict())
        
        # Create sample salary requests for testing
        from salary.models import SalaryRequest
        salary_request1 = SalaryRequest(
            employee_id=str(employee_id),
            request_type='hike',
            requested_amount=5000.0,
            reason='I have been working hard and contributing significantly to the team. I believe I deserve a salary increase based on my performance and dedication to the company.'
        )
        db.salary_requests.insert_one(salary_request1.to_dict())
        
        salary_request2 = SalaryRequest(
            employee_id=str(employee_id),
            request_type='bonus',
            requested_amount=10000.0,
            reason='I successfully completed the major project ahead of schedule and received excellent feedback from the client. I would like to request a performance bonus for this achievement.'
        )
        db.salary_requests.insert_one(salary_request2.to_dict())
        
        print("Sample data created!")
        print("Admin: admin@company.com / 123456")
        print("Employee: john@company.com / 654321")
        print("Created 2 pending salary requests for testing!")
    
    # Register salary blueprint after database initialization
    from salary.routes import salary_bp, init_salary_module
    init_salary_module(db, log_audit_event)
    app.register_blueprint(salary_bp, url_prefix='/salary')
    
    app.run(debug=True, host='0.0.0.0', port=5000)
