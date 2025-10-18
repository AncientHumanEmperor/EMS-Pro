"""
Salary Management Data Models
Adapted to work with existing MongoDB/MockDB structure
"""

from datetime import datetime, date
from typing import Dict, List, Optional, Any
import json


class SalaryComponent:
    """Represents a salary component (base, allowance, bonus, deduction)"""
    
    def __init__(self, employee_id: str, component_type: str, label: str, 
                 amount: float, effective_from: str, effective_to: Optional[str] = None,
                 created_by: str = None):
        self.employee_id = employee_id
        self.component_type = component_type  # 'base', 'allowance', 'bonus', 'deduction'
        self.label = label
        self.amount = amount  # Always positive, deductions handled by type
        self.effective_from = effective_from
        self.effective_to = effective_to
        self.created_by = created_by
        self.created_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'employee_id': self.employee_id,
            'component_type': self.component_type,
            'label': self.label,
            'amount': self.amount,
            'effective_from': self.effective_from,
            'effective_to': self.effective_to,
            'created_by': self.created_by,
            'created_at': self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SalaryComponent':
        component = cls(
            employee_id=data['employee_id'],
            component_type=data['component_type'],
            label=data['label'],
            amount=data['amount'],
            effective_from=data['effective_from'],
            effective_to=data.get('effective_to'),
            created_by=data.get('created_by')
        )
        component.created_at = data.get('created_at', datetime.now())
        return component


class SalaryHistory:
    """Represents a salary history snapshot"""
    
    def __init__(self, employee_id: str, components_snapshot: List[Dict], 
                 net_amount: float, period_start: str, period_end: str):
        self.employee_id = employee_id
        self.components_snapshot = components_snapshot
        self.net_amount = net_amount
        self.period_start = period_start
        self.period_end = period_end
        self.generated_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'employee_id': self.employee_id,
            'components_snapshot': self.components_snapshot,
            'net_amount': self.net_amount,
            'period_start': self.period_start,
            'period_end': self.period_end,
            'generated_at': self.generated_at
        }


class SalaryRequest:
    """Represents a salary/bonus request from employee"""
    
    def __init__(self, employee_id: str, request_type: str, requested_amount: float, 
                 reason: str, attachment_filename: Optional[str] = None):
        self.employee_id = employee_id
        self.request_type = request_type  # 'hike', 'bonus'
        self.requested_amount = requested_amount
        self.reason = reason
        self.attachment_filename = attachment_filename
        self.status = 'pending'  # 'pending', 'approved', 'rejected'
        self.admin_response = None
        self.created_at = datetime.now()
        self.resolved_at = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'employee_id': self.employee_id,
            'request_type': self.request_type,
            'requested_amount': self.requested_amount,
            'reason': self.reason,
            'attachment_filename': self.attachment_filename,
            'status': self.status,
            'admin_response': self.admin_response,
            'created_at': self.created_at,
            'resolved_at': self.resolved_at
        }
    
    def approve(self, admin_response: str = None):
        """Approve the request"""
        self.status = 'approved'
        self.admin_response = admin_response
        self.resolved_at = datetime.now()
    
    def reject(self, admin_response: str = None):
        """Reject the request"""
        self.status = 'rejected'
        self.admin_response = admin_response
        self.resolved_at = datetime.now()


def get_effective_components(components: List[Dict], as_of_date: str = None) -> List[Dict]:
    """
    Filter components that are effective as of the given date
    If no date provided, use today's date
    """
    if as_of_date is None:
        as_of_date = date.today().isoformat()
    
    effective = []
    for comp in components:
        # Check if component is effective as of the given date
        if comp['effective_from'] <= as_of_date:
            if comp.get('effective_to') is None or comp['effective_to'] >= as_of_date:
                effective.append(comp)
    
    return effective


def calculate_earnings(components: List[Dict]) -> float:
    """Calculate total earnings from components"""
    earnings = 0.0
    for comp in components:
        if comp['component_type'] in ['base', 'allowance', 'bonus']:
            earnings += comp['amount']
    return earnings


def calculate_deductions(components: List[Dict]) -> float:
    """Calculate total deductions from components"""
    deductions = 0.0
    for comp in components:
        if comp['component_type'] == 'deduction':
            deductions += comp['amount']
    return deductions


def get_employee_monthly_work_hours(employee: Dict) -> int:
    """Get monthly work hours for employee, default to 160"""
    return employee.get('monthly_work_hours', 160)
