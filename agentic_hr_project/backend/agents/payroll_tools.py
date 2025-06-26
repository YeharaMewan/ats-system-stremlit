from typing import Dict, Any, List
import os
import sys
import re
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from services.employee_service import EmployeeService

class PayrollTools:
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.employee_service = EmployeeService()
        print("✅ PayrollTools initialized with EmployeeService")
    
    def calculate_salary(self, employee_identifier: str) -> Dict[str, Any]:
        """Calculate employee salary using employee ID or name"""
        try:
            print(f"💰 PayrollTools: Calculating salary for '{employee_identifier}'")
            
            # First try to find employee by ID
            employee = None
            
            # Check if it's an employee ID (EMP### or ADM###)
            if re.match(r'^(EMP|ADM)\d{3}$', employee_identifier.upper()):
                employee_id = employee_identifier.upper()
                employee = self.employee_service.get_employee_by_id(employee_id)
                print(f"🔍 Searched by Employee ID: {employee_id}")
            
            # If not found by ID, try to find by name
            if not employee:
                print(f"🔍 Searching by name: {employee_identifier}")
                employee = self.employee_service.get_employee_by_name(employee_identifier)
            
            # If still not found, return error
            if not employee:
                available_employees = self.employee_service.get_all_employees()
                available_ids = [emp['employee_id'] for emp in available_employees[:5]]
                available_names = [emp['name'] for emp in available_employees[:5]]
                
                return {
                    "error": f"Employee '{employee_identifier}' not found. Available Employee IDs: {available_ids}. Available Names: {available_names}"
                }
            
            # Calculate salary
            result = self.employee_service.calculate_salary(employee['employee_id'])
            
            if "error" in result:
                print(f"❌ PayrollTools: {result['error']}")
            else:
                print(f"✅ PayrollTools: Salary calculated successfully for {employee['name']}")
            
            return result
            
        except Exception as e:
            print(f"❌ PayrollTools error: {e}")
            return {"error": f"Error calculating salary: {str(e)}"}
    
    def generate_payroll_report(self, department: str = None) -> Dict[str, Any]:
        """Generate payroll report using database"""
        try:
            print(f"📊 PayrollTools: Generating payroll report for {department or 'all departments'}")
            result = self.employee_service.generate_payroll_report(department)
            
            if "error" in result:
                print(f"❌ PayrollTools: {result['error']}")
            else:
                print(f"✅ PayrollTools: Report generated successfully")
            
            return result
        except Exception as e:
            print(f"❌ PayrollTools error: {e}")
            return {"error": f"Error generating payroll report: {str(e)}"}
    
    def get_all_employees(self) -> List[Dict[str, Any]]:
        """Get all employees from database"""
        try:
            print("👥 PayrollTools: Getting all employees")
            result = self.employee_service.get_all_employees()
            print(f"✅ PayrollTools: Retrieved {len(result)} employees")
            return result
        except Exception as e:
            print(f"❌ PayrollTools error: {e}")
            return [{"error": f"Error getting employees: {str(e)}"}]
    
    def get_employee_by_identifier(self, identifier: str) -> Dict[str, Any]:
        """Get employee by ID or name"""
        try:
            print(f"🔍 PayrollTools: Getting employee by identifier: {identifier}")
            
            # Try by ID first
            if re.match(r'^(EMP|ADM)\d{3}$', identifier.upper()):
                employee = self.employee_service.get_employee_by_id(identifier.upper())
                if employee:
                    return employee
            
            # Try by name
            employee = self.employee_service.get_employee_by_name(identifier)
            if employee:
                return employee
            
            return {"error": f"Employee '{identifier}' not found"}
            
        except Exception as e:
            print(f"❌ PayrollTools error: {e}")
            return {"error": f"Error getting employee: {str(e)}"}