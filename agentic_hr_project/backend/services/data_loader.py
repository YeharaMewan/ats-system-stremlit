import json
import os
from typing import Dict, List, Any
from datetime import datetime

class DataLoader:
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.users_file = os.path.join(data_dir, "sample_users.json")
        self.employees_file = os.path.join(data_dir, "sample_employees.json")
    
    def load_users_from_json(self) -> List[Dict[str, Any]]:
        """Load users data from JSON file"""
        try:
            if not os.path.exists(self.users_file):
                print(f"❌ Users file not found: {self.users_file}")
                return []
            
            with open(self.users_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            users = data.get('users', [])
            print(f"✅ Loaded {len(users)} users from JSON file")
            return users
            
        except Exception as e:
            print(f"❌ Error loading users from JSON: {e}")
            return []
    
    def load_employees_from_json(self) -> List[Dict[str, Any]]:
        """Load employees data from JSON file"""
        try:
            if not os.path.exists(self.employees_file):
                print(f"❌ Employees file not found: {self.employees_file}")
                return []
            
            with open(self.employees_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            employees = data.get('employees', [])
            print(f"✅ Loaded {len(employees)} employees from JSON file")
            return employees
            
        except Exception as e:
            print(f"❌ Error loading employees from JSON: {e}")
            return []
    
    def validate_json_files(self) -> Dict[str, bool]:
        """Validate if JSON files exist and are properly formatted"""
        validation = {
            "users_file_exists": False,
            "employees_file_exists": False,
            "users_valid_json": False,
            "employees_valid_json": False
        }
        
        # Check users file
        try:
            if os.path.exists(self.users_file):
                validation["users_file_exists"] = True
                with open(self.users_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if 'users' in data and isinstance(data['users'], list):
                        validation["users_valid_json"] = True
        except Exception as e:
            print(f"❌ Error validating users file: {e}")
        
        # Check employees file
        try:
            if os.path.exists(self.employees_file):
                validation["employees_file_exists"] = True
                with open(self.employees_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if 'employees' in data and isinstance(data['employees'], list):
                        validation["employees_valid_json"] = True
        except Exception as e:
            print(f"❌ Error validating employees file: {e}")
        
        return validation