#!/usr/bin/env python3
"""
Automatic setup script for JSON data files
"""

import os
import json
from pathlib import Path

def create_directory_structure():
    """Create required directory structure"""
    directories = [
        "data",
        "config", 
        "services",
        "agents",
        "data/cv_uploads",
        "data/vector_store"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✅ Created directory: {directory}")

def check_json_files():
    """Check if JSON files exist"""
    users_file = "data/sample_users.json"
    employees_file = "data/sample_employees.json"
    
    files_exist = {
        "users": os.path.exists(users_file),
        "employees": os.path.exists(employees_file)
    }
    
    return files_exist

def create_sample_json_files():
    """Create sample JSON files if they don't exist"""
    files_exist = check_json_files()
    
    if not files_exist["users"]:
        print("❌ sample_users.json not found!")
        print("Please copy the JSON content from the documentation and save it as backend/data/sample_users.json")
    else:
        print("✅ sample_users.json exists")
    
    if not files_exist["employees"]:
        print("❌ sample_employees.json not found!")
        print("Please copy the JSON content from the documentation and save it as backend/data/sample_employees.json")
    else:
        print("✅ sample_employees.json exists")
    
    return all(files_exist.values())

def main():
    print("🚀 Setting up HR System Data Structure")
    print("="*50)
    
    # Create directories
    create_directory_structure()
    
    # Check JSON files
    if create_sample_json_files():
        print("\n✅ All JSON files are present!")
        print("You can now run: python app.py")
    else:
        print("\n❌ Missing JSON files!")
        print("Please create the missing JSON files with the provided sample data")

if __name__ == "__main__":
    main()