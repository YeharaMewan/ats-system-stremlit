from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
import os
from dotenv import load_dotenv
from typing import Optional
import sys

# Add parent directory to path to import services
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

load_dotenv()

class DatabaseManager:
    def __init__(self):
        self.client: Optional[MongoClient] = None
        self.db: Optional[Database] = None
        self.data_loader = None
        self.connect()
    
    def connect(self):
        """Connect to MongoDB"""
        try:
            # MongoDB connection string from environment variable
            mongodb_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
            database_name = os.getenv('DATABASE_NAME', 'hr_system_complete')
            
            self.client = MongoClient(mongodb_uri)
            self.db = self.client[database_name]
            
            # Test connection
            self.client.admin.command('ping')
            print(f"✅ Connected to MongoDB database: {database_name}")
            
            # Initialize data loader
            data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
            from services.data_loader import DataLoader
            self.data_loader = DataLoader(data_dir)
            
            # Initialize collections if they don't exist
            self._initialize_collections()
            
        except Exception as e:
            print(f"❌ Error connecting to MongoDB: {e}")
            print("Please ensure MongoDB is running on localhost:27017")
            raise
    
    def _initialize_collections(self):
        """Initialize collections with data from JSON files"""
        try:
            # Check if JSON files exist and are valid
            validation = self.data_loader.validate_json_files()
            
            print("\n📋 JSON File Validation:")
            for key, value in validation.items():
                status = "✅" if value else "❌"
                print(f"{status} {key}: {value}")
            
            if not validation["users_file_exists"] or not validation["users_valid_json"]:
                print("❌ Users JSON file is missing or invalid!")
                return
            
            if not validation["employees_file_exists"] or not validation["employees_valid_json"]:
                print("❌ Employees JSON file is missing or invalid!")
                return
            
            # Initialize users collection
            if self.db.users.count_documents({}) == 0:
                self._load_users_from_json()
            else:
                user_count = self.db.users.count_documents({"is_active": True})
                print(f"📋 Users collection already has {user_count} active users")
            
            # Initialize employees collection  
            if self.db.employees.count_documents({}) == 0:
                self._load_employees_from_json()
            else:
                emp_count = self.db.employees.count_documents({"status": "active"})
                print(f"📋 Employees collection already has {emp_count} active employees")
            
            # Print final statistics
            self._print_database_stats()
            
        except Exception as e:
            print(f"❌ Error initializing collections: {e}")
    
    def _load_users_from_json(self):
        """Load users from JSON file into MongoDB"""
        try:
            users_data = self.data_loader.load_users_from_json()
            
            if users_data:
                self.db.users.insert_many(users_data)
                print(f"✅ Loaded {len(users_data)} users from JSON into MongoDB")
            else:
                print("❌ No users data found in JSON file")
                
        except Exception as e:
            print(f"❌ Error loading users from JSON: {e}")
    
    def _load_employees_from_json(self):
        """Load employees from JSON file into MongoDB"""
        try:
            employees_data = self.data_loader.load_employees_from_json()
            
            if employees_data:
                self.db.employees.insert_many(employees_data)
                print(f"✅ Loaded {len(employees_data)} employees from JSON into MongoDB")
            else:
                print("❌ No employees data found in JSON file")
                
        except Exception as e:
            print(f"❌ Error loading employees from JSON: {e}")
    
    def _print_database_stats(self):
        """Print database statistics"""
        try:
            user_count = self.db.users.count_documents({"is_active": True})
            employee_count = self.db.employees.count_documents({"status": "active"})
            candidate_count = self.db.candidates.count_documents({"status": "active"})
            
            print("\n" + "="*50)
            print("📊 DATABASE STATISTICS")
            print("="*50)
            print(f"👥 Active Users: {user_count}")
            print(f"💼 Active Employees: {employee_count}")
            print(f"📋 Active Candidates: {candidate_count}")
            
            # Show some sample employee IDs for testing
            sample_employees = list(self.db.employees.find(
                {"status": "active"}, 
                {"employee_id": 1, "name": 1, "_id": 0}
            ).limit(5))
            
            if sample_employees:
                print(f"\n🔍 Sample Employee IDs for testing:")
                for emp in sample_employees:
                    print(f"   - {emp['employee_id']}: {emp['name']}")
            
            print("="*50)
            
        except Exception as e:
            print(f"❌ Error printing database stats: {e}")
    
    def get_collection(self, collection_name: str) -> Collection:
        """Get a specific collection"""
        return self.db[collection_name]
    
    def close_connection(self):
        """Close database connection"""
        if self.client:
            self.client.close()
            print("✅ Database connection closed")

# Global database instance
db_manager = DatabaseManager()