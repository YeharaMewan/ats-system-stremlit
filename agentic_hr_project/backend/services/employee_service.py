from typing import Dict, Any, Optional, List
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from config.database import db_manager
from datetime import datetime

class EmployeeService:
    def __init__(self):
        self.employees_collection = db_manager.get_collection('employees')
    
    def get_employee_by_id(self, employee_id: str) -> Optional[Dict[str, Any]]:
        """Get employee by ID"""
        try:
            print(f"🔍 Searching for employee: {employee_id}")
            employee = self.employees_collection.find_one({"employee_id": employee_id})
            
            if employee:
                print(f"✅ Found employee: {employee['name']}")
                employee['_id'] = str(employee['_id'])
                return employee
            else:
                print(f"❌ Employee {employee_id} not found in database")
                # Debug: Show available employee IDs
                available_employees = list(self.employees_collection.find(
                    {}, {"employee_id": 1, "name": 1, "_id": 0}
                ))
                print(f"📋 Available employees: {[emp['employee_id'] for emp in available_employees]}")
                return None
            
        except Exception as e:
            print(f"❌ Error getting employee: {e}")
            return None
    
    def get_all_employees(self) -> List[Dict[str, Any]]:
        """Get all employees"""
        try:
            employees = list(self.employees_collection.find({"status": "active"}))
            
            # Convert ObjectId to string
            for employee in employees:
                employee['_id'] = str(employee['_id'])
            
            print(f"✅ Retrieved {len(employees)} active employees")
            return employees
            
        except Exception as e:
            print(f"❌ Error getting all employees: {e}")
            return []
    
    def calculate_salary(self, employee_id: str) -> Dict[str, Any]:
        """Calculate employee salary"""
        try:
            employee = self.get_employee_by_id(employee_id)
            if not employee:
                return {"error": f"Employee {employee_id} not found"}
            
            base_salary = employee.get('salary', 0)
            bonus = employee.get('bonus', 0)
            tax_rate = employee.get('tax_rate', 0)
            deductions = employee.get('deductions', 0)
            
            gross_salary = base_salary + bonus
            tax_amount = gross_salary * tax_rate
            net_salary = gross_salary - tax_amount - deductions
            
            result = {
                "employee_id": employee['employee_id'],
                "name": employee['name'],
                "department": employee['department'],
                "position": employee['position'],
                "base_salary": base_salary,
                "bonus": bonus,
                "gross_salary": gross_salary,
                "tax_rate": tax_rate,
                "tax_amount": tax_amount,
                "deductions": deductions,
                "net_salary": net_salary,
                "calculation_date": datetime.utcnow().isoformat()
            }
            
            print(f"✅ Calculated salary for {employee['name']}: Rs. {net_salary:,.2f}")
            return result
            
        except Exception as e:
            print(f"❌ Error calculating salary: {e}")
            return {"error": f"Error calculating salary: {str(e)}"}
    
    def generate_payroll_report(self, department: str = None) -> Dict[str, Any]:
        """Generate payroll report"""
        try:
            if department and department.lower() != "all":
                employees = list(self.employees_collection.find({
                    "department": department,
                    "status": "active"
                }))
                report_title = f"{department} Department"
            else:
                employees = self.get_all_employees()
                report_title = "All Departments"
            
            if not employees:
                return {"error": "No employees found"}
            
            total_base_salary = 0
            total_bonus = 0
            total_gross_salary = 0
            total_tax = 0
            total_deductions = 0
            total_net_salary = 0
            employee_details = []
            
            for employee in employees:
                salary_calc = self.calculate_salary(employee['employee_id'])
                if "error" not in salary_calc:
                    total_base_salary += salary_calc['base_salary']
                    total_bonus += salary_calc['bonus']
                    total_gross_salary += salary_calc['gross_salary']
                    total_tax += salary_calc['tax_amount']
                    total_deductions += salary_calc['deductions']
                    total_net_salary += salary_calc['net_salary']
                    
                    employee_details.append({
                        "employee_id": salary_calc['employee_id'],
                        "name": salary_calc['name'],
                        "position": salary_calc['position'],
                        "net_salary": salary_calc['net_salary']
                    })
            
            return {
                "department": report_title,
                "total_employees": len(employees),
                "total_base_salary": total_base_salary,
                "total_bonus": total_bonus,
                "total_gross_salary": total_gross_salary,
                "total_tax": total_tax,
                "total_deductions": total_deductions,
                "total_net_salary": total_net_salary,
                "employees": employee_details,
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            print(f"❌ Error generating payroll report: {e}")
            return {"error": f"Error generating payroll report: {str(e)}"}