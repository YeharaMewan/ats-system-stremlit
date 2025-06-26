#!/usr/bin/env python3
"""
Data Management CLI for HR System
Usage: python manage_data.py [command]
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from config.database import db_manager
from services.data_loader import DataLoader
import argparse
import json

def validate_files():
    """Validate JSON files"""
    data_loader = DataLoader(os.path.join(os.path.dirname(__file__), 'data'))
    validation = data_loader.validate_json_files()
    
    print("📋 JSON File Validation Results:")
    print(f"Users file exists: {'✅' if validation['users_file_exists'] else '❌'}")
    print(f"Users file valid: {'✅' if validation['users_valid_json'] else '❌'}")
    print(f"Employees file exists: {'✅' if validation['employees_file_exists'] else '❌'}")
    print(f"Employees file valid: {'✅' if validation['employees_valid_json'] else '❌'}")
    
    return all(validation.values())

def show_stats():
    """Show database and JSON statistics"""
    data_loader = DataLoader(os.path.join(os.path.dirname(__file__), 'data'))
    json_stats = data_loader.get_json_stats()
    
    print("\n📊 JSON FILES STATISTICS:")
    print(f"Users in JSON: {json_stats.get('users_count', 0)}")
    print(f"Active Users: {json_stats.get('active_users', 0)}")
    print(f"Employees in JSON: {json_stats.get('employees_count', 0)}")
    print(f"Active Employees: {json_stats.get('active_employees', 0)}")
    print(f"Departments: {', '.join(json_stats.get('departments', []))}")
    print(f"Roles: {', '.join(json_stats.get('roles', []))}")

def reload_data(force=False):
    """Reload data from JSON files"""
    if validate_files():
        db_manager.reload_from_json(force=force)
    else:
        print("❌ Cannot reload data - JSON files are invalid")

def sync_to_json():
    """Sync database data to JSON files"""
    db_manager.sync_data_to_json()

def main():
    parser = argparse.ArgumentParser(description='HR System Data Management CLI')
    parser.add_argument('command', choices=[
        'validate', 'stats', 'reload', 'force-reload', 'sync', 'help'
    ], help='Command to execute')
    
    args = parser.parse_args()
    
    if args.command == 'validate':
        validate_files()
    
    elif args.command == 'stats':
        show_stats()
    
    elif args.command == 'reload':
        reload_data(force=False)
    
    elif args.command == 'force-reload':
        print("⚠️ This will clear all existing database data!")
        confirm = input("Are you sure? (yes/no): ")
        if confirm.lower() == 'yes':
            reload_data(force=True)
        else:
            print("❌ Operation cancelled")
    
    elif args.command == 'sync':
        sync_to_json()
    
    elif args.command == 'help':
        print("""
HR System Data Management Commands:

validate     - Validate JSON data files
stats        - Show JSON file statistics
reload       - Reload data from JSON (only if DB is empty)
force-reload - Force reload data from JSON (clears existing data)
sync         - Sync database data back to JSON files
help         - Show this help message

Examples:
  python manage_data.py validate
  python manage_data.py stats
  python manage_data.py reload
""")

if __name__ == "__main__":
    main()