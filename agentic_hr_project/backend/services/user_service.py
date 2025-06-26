from typing import Dict, Any, Optional
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from config.database import db_manager

class UserService:
    def __init__(self):
        self.users_collection = db_manager.get_collection('users')
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user credentials"""
        try:
            # Find user by username
            user = self.users_collection.find_one({
                "username": username,
                "is_active": True
            })
            
            if not user:
                print(f"❌ User {username} not found or inactive")
                return None
            
            # Simple password check (in production, use bcrypt)
            if user['password'] == password:
                # Remove password from returned user data
                user_data = {
                    "username": user['username'],
                    "role": user['role'],
                    "name": user['name'],
                    "employee_id": user['employee_id'],
                    "email": user['email'],
                    "department": user.get('department'),
                    "phone": user.get('phone')
                }
                print(f"✅ User {username} authenticated successfully")
                return user_data
            else:
                print(f"❌ Invalid password for user {username}")
                return None
            
        except Exception as e:
            print(f"❌ Error authenticating user: {e}")
            return None
    
    def get_all_users(self) -> list:
        """Get all active users"""
        try:
            users = list(self.users_collection.find(
                {"is_active": True},
                {"password": 0}  # Exclude passwords
            ))
            
            # Convert ObjectId to string
            for user in users:
                user['_id'] = str(user['_id'])
            
            return users
            
        except Exception as e:
            print(f"❌ Error getting all users: {e}")
            return []