from typing import Dict, Any, List
import os
import sys
import re
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from services.employee_service import EmployeeService

class PayrollTools:
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        try:
            self.employee_service = EmployeeService()
            print("✅ PayrollTools initialized with EmployeeService")
        except Exception as e:
            print(f"❌ Error initializing PayrollTools: {e}")
            self.employee_service = None
    
    def calculate_salary(self, employee_identifier: str) -> Dict[str, Any]:
        """Calculate employee salary using employee ID or name"""
        try:
            if not self.employee_service:
                return {"error": "Employee service not available"}
            
            print(f"💰 PayrollTools: Calculating salary for '{employee_identifier}'")
            
            # Clean the identifier
            clean_identifier = employee_identifier.strip() if employee_identifier else ""
            
            if not clean_identifier:
                return {"error": "Please provide employee ID or name"}
            
            # First try to find employee by ID
            employee = None
            
            # Check if it's an employee ID (EMP### or ADM###)
            if re.match(r'^(EMP|ADM)\d{3}$', clean_identifier.upper()):
                employee_id = clean_identifier.upper()
                employee = self.employee_service.get_employee_by_id(employee_id)
                print(f"🔍 Searched by Employee ID: {employee_id}")
            
            # If not found by ID, try to find by name
            if not employee:
                print(f"🔍 Searching by name: {clean_identifier}")
                employee = self.employee_service.get_employee_by_name(clean_identifier)
            
            # If still not found, try using the general identifier method
            if not employee:
                print(f"🔍 Searching by general identifier: {clean_identifier}")
                employee = self.employee_service.get_employee_by_identifier(clean_identifier)
            
            # If still not found, provide helpful error message
            if not employee:
                available_employees = self.employee_service.get_all_employees()
                if available_employees:
                    # Show first 5 employees as examples
                    examples = []
                    for emp in available_employees[:5]:
                        examples.append(f"{emp['employee_id']}: {emp['name']}")
                    
                    return {
                        "error": f"Employee '{clean_identifier}' not found. Available employees include: {', '.join(examples)}"
                    }
                else:
                    return {"error": "No employees found in the database"}
            
            # Calculate salary using the employee's ID
            result = self.employee_service.calculate_salary(employee['employee_id'])
            
            if "error" in result:
                print(f"❌ PayrollTools calculation error: {result['error']}")
            else:
                print(f"✅ PayrollTools: Salary calculated successfully for {employee['name']}")
            
            return result
            
        except Exception as e:
            print(f"❌ PayrollTools error: {e}")
            import traceback
            traceback.print_exc()
            return {"error": f"Error calculating salary: {str(e)}"}
    
    def generate_payroll_report(self, department: str = None) -> Dict[str, Any]:
        """Generate payroll report using database"""
        try:
            if not self.employee_service:
                return {"error": "Employee service not available"}
            
            print(f"📊 PayrollTools: Generating payroll report for {department or 'all departments'}")
            result = self.employee_service.generate_payroll_report(department)
            
            if "error" in result:
                print(f"❌ PayrollTools report error: {result['error']}")
            else:
                total_employees = result.get('total_employees', 0)
                total_net = result.get('total_net_salary', 0)
                print(f"✅ PayrollTools: Report generated successfully - {total_employees} employees, Total: Rs. {total_net:,.2f}")
            
            return result
            
        except Exception as e:
            print(f"❌ PayrollTools error: {e}")
            import traceback
            traceback.print_exc()
            return {"error": f"Error generating payroll report: {str(e)}"}
    
    def get_all_employees(self) -> List[Dict[str, Any]]:
        """Get all employees from database"""
        try:
            if not self.employee_service:
                return [{"error": "Employee service not available"}]
            
            print("👥 PayrollTools: Getting all employees")
            result = self.employee_service.get_all_employees()
            
            if result:
                print(f"✅ PayrollTools: Retrieved {len(result)} employees")
            else:
                print("⚠️ PayrollTools: No employees found")
                return [{"error": "No employees found in database"}]
            
            return result
            
        except Exception as e:
            print(f"❌ PayrollTools error: {e}")
            import traceback
            traceback.print_exc()
            return [{"error": f"Error getting employees: {str(e)}"}]
    
    def get_employee_by_identifier(self, identifier: str) -> Dict[str, Any]:
        """Get employee by ID or name"""
        try:
            if not self.employee_service:
                return {"error": "Employee service not available"}
            
            print(f"🔍 PayrollTools: Getting employee by identifier: {identifier}")
            
            clean_identifier = identifier.strip() if identifier else ""
            if not clean_identifier:
                return {"error": "Please provide employee ID or name"}
            
            # Try by ID first
            if re.match(r'^(EMP|ADM)\d{3}$', clean_identifier.upper()):
                employee = self.employee_service.get_employee_by_id(clean_identifier.upper())
                if employee:
                    print(f"✅ Found employee by ID: {employee['name']}")
                    return employee
            
            # Try by name
            employee = self.employee_service.get_employee_by_name(clean_identifier)
            if employee:
                print(f"✅ Found employee by name: {employee['name']}")
                return employee
            
            # Try general identifier search
            employee = self.employee_service.get_employee_by_identifier(clean_identifier)
            if employee:
                print(f"✅ Found employee by identifier: {employee['name']}")
                return employee
            
            return {"error": f"Employee '{identifier}' not found"}
            
        except Exception as e:
            print(f"❌ PayrollTools error: {e}")
            import traceback
            traceback.print_exc()
            return {"error": f"Error getting employee: {str(e)}"}
    
    def search_employees(self, search_term: str) -> List[Dict[str, Any]]:
        """Search employees by various criteria"""
        try:
            if not self.employee_service:
                return [{"error": "Employee service not available"}]
            
            print(f"🔍 PayrollTools: Searching employees with term: {search_term}")
            
            if not search_term or not search_term.strip():
                return [{"error": "Please provide search term"}]
            
            result = self.employee_service.search_employees(search_term.strip())
            
            if result:
                print(f"✅ PayrollTools: Found {len(result)} employees matching '{search_term}'")
            else:
                print(f"⚠️ PayrollTools: No employees found matching '{search_term}'")
            
            return result
            
        except Exception as e:
            print(f"❌ PayrollTools error: {e}")
            return [{"error": f"Error searching employees: {str(e)}"}]
    
    def get_employee_analytics(self) -> Dict[str, Any]:
        """Get employee analytics"""
        try:
            if not self.employee_service:
                return {"error": "Employee service not available"}
            
            print("📊 PayrollTools: Getting employee analytics")
            result = self.employee_service.get_employee_analytics()
            
            if "error" not in result:
                total = result.get('total_employees', 0)
                print(f"✅ PayrollTools: Analytics generated for {total} employees")
            
            return result
            
        except Exception as e:
            print(f"❌ PayrollTools error: {e}")
            return {"error": f"Error getting analytics: {str(e)}"}
    
    def validate_employee_identifier(self, identifier: str) -> Dict[str, Any]:
        """Validate if an employee identifier exists"""
        try:
            if not self.employee_service:
                return {"valid": False, "error": "Employee service not available"}
            
            if not identifier or not identifier.strip():
                return {"valid": False, "error": "Empty identifier provided"}
            
            clean_identifier = identifier.strip()
            
            # Check by ID
            if re.match(r'^(EMP|ADM)\d{3}$', clean_identifier.upper()):
                employee = self.employee_service.get_employee_by_id(clean_identifier.upper())
                if employee:
                    return {
                        "valid": True, 
                        "employee": employee,
                        "matched_by": "employee_id"
                    }
            
            # Check by name
            employee = self.employee_service.get_employee_by_name(clean_identifier)
            if employee:
                return {
                    "valid": True, 
                    "employee": employee,
                    "matched_by": "name"
                }
            
            return {
                "valid": False, 
                "error": f"No employee found with identifier '{identifier}'"
            }
            
        except Exception as e:
            print(f"❌ PayrollTools validation error: {e}")
            return {"valid": False, "error": f"Validation error: {str(e)}"}
    
    def get_salary_summary(self, employee_identifier: str) -> Dict[str, Any]:
        """Get a quick salary summary for an employee"""
        try:
            validation = self.validate_employee_identifier(employee_identifier)
            
            if not validation["valid"]:
                return {"error": validation["error"]}
            
            employee = validation["employee"]
            salary_calc = self.calculate_salary(employee_identifier)
            
            if "error" in salary_calc:
                return salary_calc
            
            # Create summary
            summary = {
                "employee_name": employee["name"],
                "employee_id": employee["employee_id"],
                "department": employee["department"],
                "position": employee["position"],
                "net_salary": salary_calc["net_salary"],
                "gross_salary": salary_calc["gross_salary"],
                "tax_amount": salary_calc["tax_amount"],
                "summary_generated": salary_calc["calculation_date"]
            }
            
            return summary
            
        except Exception as e:
            print(f"❌ PayrollTools summary error: {e}")
            return {"error": f"Error generating salary summary: {str(e)}"}
    
    def get_department_list(self) -> List[str]:
        """Get list of all departments"""
        try:
            if not self.employee_service:
                return []
            
            employees = self.employee_service.get_all_employees()
            departments = list(set(emp.get('department', 'Unknown') for emp in employees))
            departments.sort()
            
            print(f"✅ PayrollTools: Found {len(departments)} departments")
            return departments
            
        except Exception as e:
            print(f"❌ PayrollTools error getting departments: {e}")
            return []
    
    def debug_employee_data(self) -> Dict[str, Any]:
        """Debug method to check employee data"""
        try:
            if not self.employee_service:
                return {"error": "Employee service not available"}
            
            print("🔧 PayrollTools: Running employee data debug...")
            
            # Get all employees
            all_employees = self.employee_service.get_all_employees()
            
            debug_info = {
                "total_employees": len(all_employees),
                "employees": [],
                "departments": set(),
                "employee_ids": [],
                "names": []
            }
            
            for emp in all_employees:
                debug_info["employees"].append({
                    "employee_id": emp.get("employee_id"),
                    "name": emp.get("name"),
                    "department": emp.get("department"),
                    "position": emp.get("position"),
                    "salary": emp.get("salary", 0)
                })
                debug_info["departments"].add(emp.get("department", "Unknown"))
                debug_info["employee_ids"].append(emp.get("employee_id"))
                debug_info["names"].append(emp.get("name"))
            
            debug_info["departments"] = list(debug_info["departments"])
            
            print(f"✅ Debug complete: {len(all_employees)} employees found")
            return debug_info
            
        except Exception as e:
            print(f"❌ PayrollTools debug error: {e}")
            return {"error": f"Debug failed: {str(e)}"}