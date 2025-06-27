from typing import Dict, Any, Optional, List
import os
import sys
import re
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from config.database import db_manager
from datetime import datetime

class EmployeeService:
    def __init__(self):
        self.employees_collection = db_manager.get_collection('employees')
        print("✅ EmployeeService initialized with MongoDB connection")
    
    def get_employee_by_id(self, employee_id: str) -> Optional[Dict[str, Any]]:
        """Get employee by ID"""
        try:
            print(f"🔍 Searching for employee by ID: {employee_id}")
            employee = self.employees_collection.find_one({"employee_id": employee_id})
            
            if employee:
                print(f"✅ Found employee by ID: {employee['name']}")
                employee['_id'] = str(employee['_id'])
                return employee
            else:
                print(f"❌ Employee ID {employee_id} not found in database")
                return None
            
        except Exception as e:
            print(f"❌ Error getting employee by ID: {e}")
            return None
    
    def get_employee_by_name(self, employee_name: str) -> Optional[Dict[str, Any]]:
        """Get employee by name (case-insensitive partial matching)"""
        try:
            print(f"🔍 Searching for employee by name: '{employee_name}'")
            
            # Clean the input name
            clean_name = employee_name.strip()
            
            # Try exact match first (case-insensitive)
            employee = self.employees_collection.find_one({
                "name": {"$regex": f"^{re.escape(clean_name)}$", "$options": "i"}
            })
            
            if employee:
                print(f"✅ Found employee by exact name match: {employee['name']}")
                employee['_id'] = str(employee['_id'])
                return employee
            
            # Try partial match - name contains the search term
            employee = self.employees_collection.find_one({
                "name": {"$regex": re.escape(clean_name), "$options": "i"}
            })
            
            if employee:
                print(f"✅ Found employee by partial name match: {employee['name']}")
                employee['_id'] = str(employee['_id'])
                return employee
            
            # Try reverse partial match - search term contains the name
            all_employees = list(self.employees_collection.find(
                {"status": "active"}, 
                {"name": 1, "employee_id": 1}
            ))
            
            for emp in all_employees:
                emp_name_parts = emp['name'].lower().split()
                search_name_parts = clean_name.lower().split()
                
                # Check if any part of employee name matches any part of search name
                if any(emp_part in search_name_parts for emp_part in emp_name_parts):
                    full_employee = self.employees_collection.find_one({"_id": emp["_id"]})
                    if full_employee:
                        print(f"✅ Found employee by name part match: {full_employee['name']}")
                        full_employee['_id'] = str(full_employee['_id'])
                        return full_employee
            
            print(f"❌ Employee name '{employee_name}' not found in database")
            
            # Debug: Show available employee names
            available_employees = list(self.employees_collection.find(
                {"status": "active"}, {"name": 1, "employee_id": 1, "_id": 0}
            ).limit(10))
            available_names = [f"{emp['employee_id']}: {emp['name']}" for emp in available_employees]
            print(f"📋 Available employees: {available_names}")
            
            return None
            
        except Exception as e:
            print(f"❌ Error getting employee by name: {e}")
            return None
    
    def get_employee_by_identifier(self, identifier: str) -> Optional[Dict[str, Any]]:
        """Get employee by ID or name"""
        try:
            print(f"🔍 Searching for employee by identifier: '{identifier}'")
            
            # Clean the identifier
            clean_identifier = identifier.strip()
            
            # Try by ID first if it matches the pattern
            if re.match(r'^(EMP|ADM)\d{3}$', clean_identifier.upper()):
                employee = self.get_employee_by_id(clean_identifier.upper())
                if employee:
                    return employee
            
            # Try by name
            employee = self.get_employee_by_name(clean_identifier)
            if employee:
                return employee
            
            print(f"❌ No employee found with identifier: '{identifier}'")
            return None
            
        except Exception as e:
            print(f"❌ Error getting employee by identifier: {e}")
            return None
    
    def get_all_employees(self) -> List[Dict[str, Any]]:
        """Get all active employees"""
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
                # Show available employees for debugging
                available_employees = self.get_all_employees()
                available_list = [(emp['employee_id'], emp['name']) for emp in available_employees[:5]]
                
                return {
                    "error": f"Employee {employee_id} not found. Available employees: {available_list}"
                }
            
            # Get salary components with defaults
            base_salary = employee.get('salary', 0)
            bonus = employee.get('bonus', 0)
            tax_rate = employee.get('tax_rate', 0.1)  # Default 10%
            deductions = employee.get('deductions', 0)
            
            # Calculate salary
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
            import traceback
            traceback.print_exc()
            return {"error": f"Error calculating salary: {str(e)}"}
    
    def generate_payroll_report(self, department: str = None) -> Dict[str, Any]:
        """Generate payroll report for department or all employees"""
        try:
            if department and department.lower() != "all":
                # Filter by department
                employees = list(self.employees_collection.find({
                    "department": {"$regex": f"^{re.escape(department)}$", "$options": "i"},
                    "status": "active"
                }))
                report_title = f"{department} Department"
            else:
                employees = self.get_all_employees()
                report_title = "All Departments"
            
            if not employees:
                return {"error": f"No employees found for {report_title}"}
            
            # Initialize totals
            total_base_salary = 0
            total_bonus = 0
            total_gross_salary = 0
            total_tax = 0
            total_deductions = 0
            total_net_salary = 0
            employee_details = []
            
            # Calculate for each employee
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
                        "department": salary_calc['department'],
                        "base_salary": salary_calc['base_salary'],
                        "bonus": salary_calc['bonus'],
                        "gross_salary": salary_calc['gross_salary'],
                        "tax_amount": salary_calc['tax_amount'],
                        "deductions": salary_calc['deductions'],
                        "net_salary": salary_calc['net_salary']
                    })
                else:
                    print(f"⚠️ Failed to calculate salary for {employee.get('name', 'Unknown')}: {salary_calc.get('error')}")
            
            if not employee_details:
                return {"error": "No salary calculations could be completed"}
            
            result = {
                "department": report_title,
                "total_employees": len(employee_details),
                "total_base_salary": total_base_salary,
                "total_bonus": total_bonus,
                "total_gross_salary": total_gross_salary,
                "total_tax": total_tax,
                "total_deductions": total_deductions,
                "total_net_salary": total_net_salary,
                "employees": employee_details,
                "generated_at": datetime.utcnow().isoformat()
            }
            
            print(f"✅ Generated payroll report for {report_title}: {len(employee_details)} employees, Total: Rs. {total_net_salary:,.2f}")
            return result
            
        except Exception as e:
            print(f"❌ Error generating payroll report: {e}")
            import traceback
            traceback.print_exc()
            return {"error": f"Error generating payroll report: {str(e)}"}
    
    def search_employees(self, search_term: str) -> List[Dict[str, Any]]:
        """Search employees by name, ID, department, or position"""
        try:
            print(f"🔍 Searching employees with term: '{search_term}'")
            
            search_regex = {"$regex": re.escape(search_term), "$options": "i"}
            
            # Search in multiple fields
            query = {
                "$and": [
                    {"status": "active"},
                    {"$or": [
                        {"name": search_regex},
                        {"employee_id": search_regex},
                        {"department": search_regex},
                        {"position": search_regex}
                    ]}
                ]
            }
            
            employees = list(self.employees_collection.find(query))
            
            # Convert ObjectId to string
            for employee in employees:
                employee['_id'] = str(employee['_id'])
            
            print(f"✅ Found {len(employees)} employees matching '{search_term}'")
            return employees
            
        except Exception as e:
            print(f"❌ Error searching employees: {e}")
            return []
    
    def update_employee_salary(self, employee_id: str, salary_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update employee salary information"""
        try:
            employee = self.get_employee_by_id(employee_id)
            if not employee:
                return {"success": False, "error": f"Employee {employee_id} not found"}
            
            # Prepare update data
            update_data = {
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # Update allowed fields
            allowed_fields = ['salary', 'bonus', 'tax_rate', 'deductions']
            for field in allowed_fields:
                if field in salary_data:
                    update_data[field] = salary_data[field]
            
            # Update in database
            result = self.employees_collection.update_one(
                {"employee_id": employee_id},
                {"$set": update_data}
            )
            
            if result.modified_count > 0:
                print(f"✅ Updated salary for {employee['name']}")
                return {"success": True, "message": f"Salary updated for {employee['name']}"}
            else:
                return {"success": False, "error": "No changes made to salary"}
                
        except Exception as e:
            print(f"❌ Error updating salary: {e}")
            return {"success": False, "error": f"Error updating salary: {str(e)}"}
    
    def get_employee_analytics(self) -> Dict[str, Any]:
        """Get employee analytics"""
        try:
            total_employees = self.employees_collection.count_documents({"status": "active"})
            
            if total_employees == 0:
                return {"total_employees": 0}
            
            # Department distribution
            dept_pipeline = [
                {"$match": {"status": "active"}},
                {"$group": {"_id": "$department", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}}
            ]
            
            dept_stats = list(self.employees_collection.aggregate(dept_pipeline))
            
            # Salary statistics
            salary_pipeline = [
                {"$match": {"status": "active"}},
                {"$group": {
                    "_id": None,
                    "avg_salary": {"$avg": "$salary"},
                    "min_salary": {"$min": "$salary"},
                    "max_salary": {"$max": "$salary"},
                    "total_salary": {"$sum": "$salary"}
                }}
            ]
            
            salary_stats = list(self.employees_collection.aggregate(salary_pipeline))
            
            # Position distribution
            position_pipeline = [
                {"$match": {"status": "active"}},
                {"$group": {"_id": "$position", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}}
            ]
            
            position_stats = list(self.employees_collection.aggregate(position_pipeline))
            
            result = {
                "total_employees": total_employees,
                "department_distribution": {stat["_id"]: stat["count"] for stat in dept_stats},
                "position_distribution": {stat["_id"]: stat["count"] for stat in position_stats},
                "salary_statistics": salary_stats[0] if salary_stats else {},
                "generated_at": datetime.utcnow().isoformat()
            }
            
            print(f"✅ Generated employee analytics for {total_employees} employees")
            return result
            
        except Exception as e:
            print(f"❌ Error generating analytics: {e}")
            return {"error": f"Analytics failed: {str(e)}"}
    
    def validate_employee_data(self, employee_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate employee data before saving"""
        try:
            errors = []
            
            # Required fields
            required_fields = ['employee_id', 'name', 'department', 'position', 'salary']
            for field in required_fields:
                if field not in employee_data or not employee_data[field]:
                    errors.append(f"Missing required field: {field}")
            
            # Validate employee ID format
            if 'employee_id' in employee_data:
                if not re.match(r'^(EMP|ADM)\d{3}$', employee_data['employee_id']):
                    errors.append("Employee ID must be in format EMP### or ADM###")
            
            # Validate salary
            if 'salary' in employee_data:
                try:
                    salary = float(employee_data['salary'])
                    if salary < 0:
                        errors.append("Salary cannot be negative")
                except (ValueError, TypeError):
                    errors.append("Salary must be a valid number")
            
            # Check if employee ID already exists
            if 'employee_id' in employee_data:
                existing = self.get_employee_by_id(employee_data['employee_id'])
                if existing:
                    errors.append(f"Employee ID {employee_data['employee_id']} already exists")
            
            if errors:
                return {"valid": False, "errors": errors}
            else:
                return {"valid": True, "errors": []}
                
        except Exception as e:
            return {"valid": False, "errors": [f"Validation error: {str(e)}"]}
    
    def add_new_employee(self, employee_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add new employee to database"""
        try:
            # Validate data first
            validation = self.validate_employee_data(employee_data)
            if not validation["valid"]:
                return {"success": False, "errors": validation["errors"]}
            
            # Add metadata
            employee_data["created_at"] = datetime.utcnow().isoformat()
            employee_data["status"] = "active"
            
            # Set defaults for optional fields
            employee_data.setdefault("bonus", 0)
            employee_data.setdefault("tax_rate", 0.1)
            employee_data.setdefault("deductions", 0)
            
            # Insert into database
            result = self.employees_collection.insert_one(employee_data)
            
            print(f"✅ Added new employee: {employee_data['name']} ({employee_data['employee_id']})")
            return {
                "success": True,
                "message": f"Employee {employee_data['name']} added successfully",
                "employee_id": employee_data['employee_id']
            }
            
        except Exception as e:
            print(f"❌ Error adding employee: {e}")
            return {"success": False, "error": f"Error adding employee: {str(e)}"}