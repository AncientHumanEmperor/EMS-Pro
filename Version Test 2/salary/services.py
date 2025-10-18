"""
Salary Management Services
Pure functions for salary calculations and business logic
"""

from typing import List, Dict, Optional
from .models import get_effective_components, calculate_earnings, calculate_deductions, get_employee_monthly_work_hours


def calculate_net_salary(components: List[Dict], as_of_date: str = None) -> float:
    """
    Calculate net salary from components
    
    Args:
        components: List of salary component dictionaries
        as_of_date: Date to calculate salary for (ISO format), defaults to today
    
    Returns:
        Net salary amount (earnings - deductions)
    """
    effective_components = get_effective_components(components, as_of_date)
    
    total_earnings = calculate_earnings(effective_components)
    total_deductions = calculate_deductions(effective_components)
    
    return total_earnings - total_deductions


def calculate_hourly_rate(net_salary: float, monthly_work_hours: int = 160) -> float:
    """
    Calculate hourly rate from net salary
    
    Args:
        net_salary: Monthly net salary amount
        monthly_work_hours: Hours worked per month, defaults to 160
    
    Returns:
        Hourly rate (net_salary / monthly_work_hours)
    """
    if monthly_work_hours <= 0:
        return 0.0
    
    return net_salary / monthly_work_hours


def calculate_value_per_rupee(performance_score: Optional[float], hourly_rate: float) -> Optional[float]:
    """
    Calculate value per rupee efficiency metric
    
    Args:
        performance_score: Performance score (0-100 scale)
        hourly_rate: Hourly rate in rupees
    
    Returns:
        Value per rupee metric, or None if calculation not possible
    """
    if performance_score is None:
        return None
    
    if hourly_rate <= 0:
        return None
    
    # Normalize performance score to 0-1 scale, then divide by hourly rate
    normalized_performance = performance_score / 100.0
    return normalized_performance / hourly_rate


def get_employee_performance_score(employee_id: str, db) -> Optional[float]:
    """
    Get the latest performance score for an employee
    
    Args:
        employee_id: Employee ID
        db: Database connection
    
    Returns:
        Latest performance score (0-100) or None if not available
    """
    try:
        # Get the latest performance review
        latest_review = db.performance_reviews.find({'employee_id': employee_id}).sort('created_at', -1).limit(1)
        reviews = list(latest_review)
        
        if reviews:
            # Convert rating (1-5) to percentage (0-100)
            rating = reviews[0].get('rating', 0)
            return (rating / 5.0) * 100
        
        return None
    except Exception:
        return None


def validate_salary_component(data: Dict) -> List[str]:
    """
    Validate salary component data
    
    Args:
        data: Component data dictionary
    
    Returns:
        List of validation errors (empty if valid)
    """
    errors = []
    
    # Required fields
    required_fields = ['component_type', 'label', 'amount', 'effective_from']
    for field in required_fields:
        if not data.get(field):
            errors.append(f"{field} is required")
    
    # Validate component type
    valid_types = ['base', 'allowance', 'bonus', 'deduction']
    if data.get('component_type') not in valid_types:
        errors.append(f"component_type must be one of: {', '.join(valid_types)}")
    
    # Validate amount
    try:
        amount = float(data.get('amount', 0))
        if amount <= 0:
            errors.append("amount must be greater than 0")
    except (ValueError, TypeError):
        errors.append("amount must be a valid number")
    
    # Validate dates
    try:
        from datetime import datetime
        effective_from = datetime.fromisoformat(data.get('effective_from', ''))
        if data.get('effective_to'):
            effective_to = datetime.fromisoformat(data.get('effective_to'))
            if effective_to < effective_from:
                errors.append("effective_to must be after effective_from")
    except ValueError:
        errors.append("Invalid date format. Use YYYY-MM-DD")
    
    return errors


def validate_salary_request(data: Dict) -> List[str]:
    """
    Validate salary request data
    
    Args:
        data: Request data dictionary
    
    Returns:
        List of validation errors (empty if valid)
    """
    errors = []
    
    # Required fields
    required_fields = ['request_type', 'requested_amount', 'reason']
    for field in required_fields:
        if not data.get(field):
            errors.append(f"{field} is required")
    
    # Validate request type
    valid_types = ['hike', 'bonus']
    if data.get('request_type') not in valid_types:
        errors.append(f"request_type must be one of: {', '.join(valid_types)}")
    
    # Validate amount
    try:
        amount = float(data.get('requested_amount', 0))
        if amount <= 0:
            errors.append("requested_amount must be greater than 0")
    except (ValueError, TypeError):
        errors.append("requested_amount must be a valid number")
    
    # Validate reason length
    reason = data.get('reason', '')
    if len(reason.strip()) < 25:
        errors.append("reason must be at least 25 characters long")
    
    return errors


def format_currency(amount: float) -> str:
    """
    Format amount as Indian currency
    
    Args:
        amount: Amount to format
    
    Returns:
        Formatted currency string
    """
    return f"₹{amount:,.2f}"


def get_salary_summary(employee_id: str, db) -> Dict:
    """
    Get comprehensive salary summary for an employee
    
    Args:
        employee_id: Employee ID
        db: Database connection
    
    Returns:
        Dictionary with salary summary data
    """
    try:
        # Get employee data - try both string and ObjectId formats
        employee = db.employees.find_one({'_id': employee_id})
        if not employee:
            # Try with ObjectId if it's a string that looks like an ObjectId
            try:
                from bson import ObjectId
                if isinstance(employee_id, str) and len(employee_id) == 24:
                    employee = db.employees.find_one({'_id': ObjectId(employee_id)})
            except:
                pass
        
        if not employee:
            return {'error': 'Employee not found'}
        
        # Get salary components
        components = list(db.salary_components.find({'employee_id': employee_id}))
        
        # Calculate net salary
        net_salary = calculate_net_salary(components)
        
        # Get monthly work hours
        monthly_work_hours = get_employee_monthly_work_hours(employee)
        
        # Calculate hourly rate
        hourly_rate = calculate_hourly_rate(net_salary, monthly_work_hours)
        
        # Get performance score
        performance_score = get_employee_performance_score(employee_id, db)
        
        # Calculate value per rupee
        value_per_rupee = calculate_value_per_rupee(performance_score, hourly_rate)
        
        # Get effective components breakdown
        effective_components = get_effective_components(components)
        earnings = calculate_earnings(effective_components)
        deductions = calculate_deductions(effective_components)
        
        return {
            'employee': employee,
            'components': effective_components,
            'net_salary': net_salary or 0,
            'earnings': earnings or 0,
            'deductions': deductions or 0,
            'hourly_rate': hourly_rate or 0,
            'performance_score': performance_score or 0,
            'value_per_rupee': value_per_rupee or 0,
            'monthly_work_hours': monthly_work_hours or 160
        }
        
    except Exception as e:
        return {'error': str(e)}
