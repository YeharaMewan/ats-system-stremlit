from typing import Dict, Any, Optional, List
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from config.database import db_manager
from datetime import datetime

class CVService:
    def __init__(self):
        self.candidates_collection = db_manager.get_collection('candidates')
    
    def save_candidate_to_db(self, candidate_data: Dict[str, Any]) -> Dict[str, Any]:
        """Save candidate information to MongoDB with duplicate checking"""
        try:
            # Check if candidate already exists (by name + position)
            existing_candidate = self.candidates_collection.find_one({
                "candidate_name": candidate_data['candidate_name'],
                "position": candidate_data['position'],
                "status": "active"
            })
            
            if existing_candidate:
                return {
                    "success": False,
                    "message": f"Candidate {candidate_data['candidate_name']} for position {candidate_data['position']} already exists"
                }
            
            # Add metadata
            candidate_data['created_at'] = datetime.utcnow().isoformat()
            candidate_data['status'] = 'active'
            
            result = self.candidates_collection.insert_one(candidate_data)
            
            return {
                "success": True,
                "message": f"Candidate {candidate_data['candidate_name']} added successfully",
                "candidate_id": str(result.inserted_id)
            }
                
        except Exception as e:
            print(f"❌ Error saving candidate: {e}")
            return {"success": False, "message": f"Error saving candidate: {str(e)}"}
    
    def get_all_candidates(self) -> List[Dict[str, Any]]:
        """Get all unique candidates from database"""
        try:
            candidates = list(self.candidates_collection.find({"status": "active"}))
            
            # Convert ObjectId to string
            for candidate in candidates:
                candidate['_id'] = str(candidate['_id'])
            
            print(f"✅ Retrieved {len(candidates)} active candidates from database")
            return candidates
            
        except Exception as e:
            print(f"❌ Error getting candidates: {e}")
            return []
    
    def get_candidate_by_name(self, candidate_name: str) -> Optional[Dict[str, Any]]:
        """Get candidate by name"""
        try:
            candidate = self.candidates_collection.find_one({
                "candidate_name": candidate_name,
                "status": "active"
            })
            
            if candidate:
                candidate['_id'] = str(candidate['_id'])
            
            return candidate
            
        except Exception as e:
            print(f"❌ Error getting candidate: {e}")
            return None
    
    def delete_candidate_from_db(self, candidate_name: str) -> Dict[str, Any]:
        """Delete candidate from database"""
        try:
            result = self.candidates_collection.update_one(
                {"candidate_name": candidate_name},
                {"$set": {"status": "deleted", "deleted_at": datetime.utcnow().isoformat()}}
            )
            
            if result.modified_count > 0:
                return {"success": True, "message": f"Candidate {candidate_name} deleted successfully"}
            else:
                return {"success": False, "message": f"Candidate {candidate_name} not found"}
                
        except Exception as e:
            return {"success": False, "message": f"Error deleting candidate: {str(e)}"}
    
    def search_candidates_in_db(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search candidates in database with filters"""
        try:
            query = {"status": "active"}
            
            # Apply filters
            if "position" in filters:
                query["position"] = {"$regex": filters["position"], "$options": "i"}
            
            if "min_experience" in filters:
                query["experience_years"] = {"$gte": filters["min_experience"]}
            
            if "required_skills" in filters:
                # Search for any of the required skills
                query["skills"] = {"$in": filters["required_skills"]}
            
            candidates = list(self.candidates_collection.find(query))
            
            # Convert ObjectId to string
            for candidate in candidates:
                candidate['_id'] = str(candidate['_id'])
            
            print(f"🔍 Found {len(candidates)} candidates matching search criteria")
            return candidates
            
        except Exception as e:
            print(f"❌ Error searching candidates: {e}")
            return []
    
    def get_candidate_analytics(self) -> Dict[str, Any]:
        """Get candidate analytics from database"""
        try:
            total_candidates = self.candidates_collection.count_documents({"status": "active"})
            
            if total_candidates == 0:
                return {"total_candidates": 0}
            
            # Aggregation pipeline for analytics
            pipeline = [
                {"$match": {"status": "active"}},
                {"$group": {
                    "_id": "$position",
                    "count": {"$sum": 1},
                    "avg_experience": {"$avg": "$experience_years"}
                }}
            ]
            
            position_stats = list(self.candidates_collection.aggregate(pipeline))
            
            # Skills aggregation
            skills_pipeline = [
                {"$match": {"status": "active"}},
                {"$unwind": "$skills"},
                {"$group": {"_id": "$skills", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
                {"$limit": 10}
            ]
            
            top_skills = list(self.candidates_collection.aggregate(skills_pipeline))
            
            # Overall stats
            experience_pipeline = [
                {"$match": {"status": "active"}},
                {"$group": {
                    "_id": None,
                    "avg_experience": {"$avg": "$experience_years"},
                    "total_candidates": {"$sum": 1}
                }}
            ]
            
            overall_stats = list(self.candidates_collection.aggregate(experience_pipeline))
            
            return {
                "total_candidates": total_candidates,
                "position_distribution": {stat["_id"]: stat["count"] for stat in position_stats},
                "average_experience": overall_stats[0]["avg_experience"] if overall_stats else 0,
                "top_skills": [(skill["_id"], skill["count"]) for skill in top_skills],
                "position_stats": position_stats
            }
            
        except Exception as e:
            print(f"❌ Error getting analytics: {e}")
            return {"error": f"Analytics failed: {str(e)}"}
    
    def remove_duplicate_candidates(self) -> Dict[str, Any]:
        """Remove duplicate candidates based on name + position"""
        try:
            print("🧹 Checking for duplicate candidates...")
            
            # Find duplicates using aggregation
            pipeline = [
                {"$match": {"status": "active"}},
                {"$group": {
                    "_id": {
                        "candidate_name": "$candidate_name",
                        "position": "$position"
                    },
                    "docs": {"$push": "$ROOT"},
                    "count": {"$sum": 1}
                }},
                {"$match": {"count": {"$gt": 1}}}
            ]
            
            duplicates = list(self.candidates_collection.aggregate(pipeline))
            
            if not duplicates:
                print("✅ No duplicate candidates found")
                return {"success": True, "message": "No duplicates found", "removed_count": 0}
            
            removed_count = 0
            
            for duplicate_group in duplicates:
                docs = duplicate_group["docs"]
                # Keep the first document, mark others as deleted
                for doc in docs[1:]:  # Skip the first one
                    self.candidates_collection.update_one(
                        {"_id": doc["_id"]},
                        {"$set": {"status": "duplicate_removed", "removed_at": datetime.utcnow().isoformat()}}
                    )
                    removed_count += 1
                    print(f"🗑️ Marked duplicate as removed: {doc['candidate_name']} - {doc['position']}")
            
            print(f"✅ Removed {removed_count} duplicate candidates")
            return {
                "success": True,
                "message": f"Removed {removed_count} duplicate candidates",
                "removed_count": removed_count
            }
            
        except Exception as e:
            print(f"❌ Error removing duplicates: {e}")
            return {"success": False, "message": f"Error removing duplicates: {str(e)}"}