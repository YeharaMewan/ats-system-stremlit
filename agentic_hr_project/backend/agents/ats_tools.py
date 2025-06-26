import os
import faiss
import numpy as np
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer
from pypdf import PdfReader
import pickle
import docx2txt
import re
from datetime import datetime
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from services.cv_service import CVService

class ATSTools:
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.cv_dir = os.path.join(data_dir, "cv_uploads")
        self.vector_store_dir = os.path.join(data_dir, "vector_store")
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.index = None
        self.cv_metadata = []
        self.cv_service = CVService()
        
        # Ensure directories exist
        os.makedirs(self.cv_dir, exist_ok=True)
        os.makedirs(self.vector_store_dir, exist_ok=True)
        
        print("✅ ATSTools initialized")
        print(f"📁 CV directory: {self.cv_dir}")
        print(f"🗂️ Vector store directory: {self.vector_store_dir}")
        
        # Load existing index if available
        self._load_index()
        
        # Process existing CV files in the directory
        self._process_existing_cv_files()
        
        # Build vector index from database (no hardcoded samples)
        self._build_vector_index_from_database()
    
    def _build_vector_index_from_database(self):
        """Build vector index from existing database candidates only"""
        try:
            # Get all candidates from database
            db_candidates = self.cv_service.get_all_candidates()
            
            if not db_candidates:
                print("📋 No candidates found in database - vector index will be empty")
                return
            
            print(f"🔧 Building vector index from {len(db_candidates)} database candidates...")
            
            # Check if we already have these candidates in vector index
            existing_candidate_names = set()
            if self.cv_metadata:
                existing_candidate_names = {meta['candidate_name'] for meta in self.cv_metadata}
            
            new_candidates = []
            new_metadata = []
            
            for candidate in db_candidates:
                candidate_name = candidate['candidate_name']
                
                # Skip if already in vector index
                if candidate_name in existing_candidate_names:
                    continue
                
                cv_text = candidate.get('cv_text', '')
                if cv_text:
                    new_candidates.append(cv_text)
                    
                    metadata = {
                        "candidate_name": candidate["candidate_name"],
                        "position": candidate["position"],
                        "cv_text": cv_text,
                        "skills": candidate.get("skills", []),
                        "experience_years": candidate.get("experience_years", 0),
                        "education": candidate.get("education", []),
                        "contact_info": candidate.get("contact_info", {}),
                        "summary": candidate.get("summary", "")
                    }
                    new_metadata.append(metadata)
            
            if new_candidates:
                print(f"🆕 Adding {len(new_candidates)} new candidates to vector index")
                
                # Generate embeddings for new candidates
                embeddings = self.model.encode(new_candidates)
                
                # Initialize or expand index
                if self.index is None:
                    self.index = faiss.IndexFlatL2(embeddings.shape[1])
                
                # Add new embeddings
                self.index.add(embeddings)
                
                # Add new metadata
                self.cv_metadata.extend(new_metadata)
                
                # Save updated index
                self._save_index()
                
                print(f"✅ Vector index updated. Total candidates: {len(self.cv_metadata)}")
            else:
                print("📋 No new candidates to add to vector index")
                
        except Exception as e:
            print(f"❌ Error building vector index from database: {e}")
    
    def _process_existing_cv_files(self):
        """Process CV files in cv_uploads directory"""
        try:
            cv_files = []
            supported_extensions = {'.pdf', '.docx', '.doc', '.txt'}
            
            if os.path.exists(self.cv_dir):
                for filename in os.listdir(self.cv_dir):
                    file_path = os.path.join(self.cv_dir, filename)
                    if os.path.isfile(file_path):
                        file_extension = os.path.splitext(filename)[1].lower()
                        if file_extension in supported_extensions:
                            cv_files.append(file_path)
            
            if cv_files:
                print(f"📁 Found {len(cv_files)} CV files to process...")
                
                for file_path in cv_files:
                    try:
                        filename = os.path.basename(file_path)
                        name_parts = os.path.splitext(filename)[0].split('_')
                        
                        if len(name_parts) >= 2:
                            candidate_name = ' '.join(name_parts[:-1])
                            position = name_parts[-1].replace('_', ' ')
                        else:
                            candidate_name = name_parts[0].replace('_', ' ')
                            position = "Unknown Position"
                        
                        # Check if candidate already exists in database
                        existing_candidate = self.cv_service.get_candidate_by_name(candidate_name)
                        if not existing_candidate:
                            result = self.add_cv_to_database(file_path, candidate_name, position)
                            if result.get("success"):
                                print(f"✅ Processed new CV: {candidate_name}")
                        else:
                            print(f"⏭️ CV for {candidate_name} already exists, skipping...")
                            
                    except Exception as e:
                        print(f"❌ Error processing {file_path}: {e}")
            else:
                print("📁 No CV files found in cv_uploads directory")
                
        except Exception as e:
            print(f"❌ Error processing CV files: {e}")
    
    def search_candidates(self, query: str, top_k: int = 5, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Search candidates with deduplication"""
        try:
            print(f"🔍 Searching candidates for: '{query}'")
            
            # Get unique candidates from database first
            db_candidates = self.cv_service.get_all_candidates()
            
            if not db_candidates:
                print("❌ No candidates found in database")
                return []
            
            # Remove duplicates by candidate name + position
            unique_candidates = {}
            for candidate in db_candidates:
                key = f"{candidate['candidate_name']}_{candidate['position']}"
                if key not in unique_candidates:
                    unique_candidates[key] = candidate
            
            db_candidates = list(unique_candidates.values())
            print(f"📋 Found {len(db_candidates)} unique candidates in database")
            
            # If we have vector index, use semantic search
            if self.index is not None and len(self.cv_metadata) > 0:
                print("🔍 Using vector similarity search")
                
                # Generate query embedding
                query_embedding = self.model.encode([query])
                
                # Search in vector index
                scores, indices = self.index.search(query_embedding, min(len(self.cv_metadata), top_k * 2))
                
                # Get unique results based on candidate name
                seen_candidates = set()
                results = []
                
                for score, idx in zip(scores[0], indices[0]):
                    if idx != -1 and idx < len(self.cv_metadata):
                        vector_candidate = self.cv_metadata[idx]
                        candidate_name = vector_candidate["candidate_name"]
                        
                        # Skip if we've already seen this candidate
                        if candidate_name in seen_candidates:
                            continue
                        
                        seen_candidates.add(candidate_name)
                        
                        # Find corresponding database candidate
                        for db_candidate in db_candidates:
                            if db_candidate["candidate_name"] == candidate_name:
                                db_candidate["similarity_score"] = float(score)
                                results.append(db_candidate)
                                break
                        
                        # Stop when we have enough unique results
                        if len(results) >= top_k:
                            break
                
                # Sort by similarity and return top results
                results = sorted(results, key=lambda x: x.get("similarity_score", float('inf')))[:top_k]
                
            else:
                print("🔍 Using basic text search (no vector index)")
                # Fallback to simple text matching
                results = []
                query_lower = query.lower()
                
                for candidate in db_candidates:
                    cv_text = candidate.get('cv_text', '').lower()
                    skills = [skill.lower() for skill in candidate.get('skills', [])]
                    position = candidate.get('position', '').lower()
                    
                    # Simple matching
                    if (query_lower in cv_text or 
                        any(query_lower in skill for skill in skills) or
                        query_lower in position):
                        results.append(candidate)
                
                results = results[:top_k]
            
            print(f"✅ Search completed. Found {len(results)} unique matching candidates")
            return results
            
        except Exception as e:
            print(f"❌ Error in candidate search: {e}")
            return []
    
    def get_all_candidates(self) -> List[Dict[str, Any]]:
        """Get all unique candidates from database"""
        try:
            db_candidates = self.cv_service.get_all_candidates()
            
            # Remove duplicates by candidate name + position
            unique_candidates = {}
            for candidate in db_candidates:
                key = f"{candidate['candidate_name']}_{candidate['position']}"
                if key not in unique_candidates:
                    unique_candidates[key] = candidate
            
            results = list(unique_candidates.values())
            print(f"📋 Retrieved {len(results)} unique candidates")
            return results
            
        except Exception as e:
            print(f"❌ Error retrieving candidates: {e}")
            return []
    
    def get_candidate_by_name(self, candidate_name: str) -> Dict[str, Any]:
        """Get candidate details by name"""
        try:
            candidate = self.cv_service.get_candidate_by_name(candidate_name)
            if candidate:
                return candidate
            else:
                return {"error": f"Candidate {candidate_name} not found"}
        except Exception as e:
            return {"error": f"Error retrieving candidate: {str(e)}"}
    
    def delete_candidate(self, candidate_name: str) -> Dict[str, Any]:
        """Delete candidate and rebuild vector index"""
        try:
            # Delete from database
            db_result = self.cv_service.delete_candidate_from_db(candidate_name)
            
            if db_result.get("success"):
                # Rebuild vector index to remove the candidate
                self._rebuild_vector_index_from_database()
                return db_result
            else:
                return db_result
                
        except Exception as e:
            return {
                "success": False,
                "message": f"Error deleting candidate: {str(e)}"
            }
    
    def _rebuild_vector_index_from_database(self):
        """Rebuild vector index completely from database"""
        try:
            print("🔄 Rebuilding vector index from database...")
            
            # Clear existing index and metadata
            self.index = None
            self.cv_metadata = []
            
            # Get all unique candidates from database
            db_candidates = self.cv_service.get_all_candidates()
            
            if not db_candidates:
                print("📋 No candidates in database - vector index cleared")
                self._save_index()
                return
            
            # Remove duplicates
            unique_candidates = {}
            for candidate in db_candidates:
                key = f"{candidate['candidate_name']}_{candidate['position']}"
                if key not in unique_candidates:
                    unique_candidates[key] = candidate
            
            db_candidates = list(unique_candidates.values())
            
            # Build new index
            cv_texts = []
            new_metadata = []
            
            for candidate in db_candidates:
                cv_text = candidate.get('cv_text', '')
                if cv_text:
                    cv_texts.append(cv_text)
                    
                    metadata = {
                        "candidate_name": candidate["candidate_name"],
                        "position": candidate["position"],
                        "cv_text": cv_text,
                        "skills": candidate.get("skills", []),
                        "experience_years": candidate.get("experience_years", 0),
                        "education": candidate.get("education", []),
                        "contact_info": candidate.get("contact_info", {}),
                        "summary": candidate.get("summary", "")
                    }
                    new_metadata.append(metadata)
            
            if cv_texts:
                # Generate embeddings
                embeddings = self.model.encode(cv_texts)
                
                # Create new index
                self.index = faiss.IndexFlatL2(embeddings.shape[1])
                self.index.add(embeddings)
                self.cv_metadata = new_metadata
                
                print(f"✅ Vector index rebuilt with {len(self.cv_metadata)} unique candidates")
            
            # Save updated index
            self._save_index()
            
        except Exception as e:
            print(f"❌ Error rebuilding vector index: {e}")
    
    def add_cv_to_database(self, cv_file_path: str, candidate_name: str, position: str) -> Dict[str, Any]:
        """Add CV to database and update vector index"""
        try:
            # Check if candidate already exists
            existing_candidate = self.cv_service.get_candidate_by_name(candidate_name)
            if existing_candidate:
                return {
                    "success": False,
                    "message": f"Candidate {candidate_name} already exists in database"
                }
            
            # Extract text from CV file
            cv_text = self.extract_text_from_file(cv_file_path)
            
            if cv_text.startswith("Error"):
                return {"success": False, "message": cv_text}
            
            # Extract information
            extracted_info = self._extract_cv_information(cv_text)
            
            # Prepare candidate data
            candidate_data = {
                "candidate_name": candidate_name,
                "position": position,
                "cv_file_path": cv_file_path,
                "cv_text": cv_text,
                "skills": extracted_info["skills"],
                "experience_years": extracted_info["experience_years"],
                "education": extracted_info["education"],
                "contact_info": extracted_info["contact_info"],
                "summary": cv_text[:500]
            }
            
            # Save to database
            db_result = self.cv_service.save_candidate_to_db(candidate_data)
            
            if db_result.get("success"):
                # Add to vector index
                embedding = self.model.encode([cv_text])
                
                if self.index is None:
                    self.index = faiss.IndexFlatL2(embedding.shape[1])
                
                self.index.add(embedding)
                
                metadata = {
                    "candidate_name": candidate_name,
                    "position": position,
                    "cv_text": cv_text,
                    "skills": extracted_info["skills"],
                    "experience_years": extracted_info["experience_years"],
                    "education": extracted_info["education"],
                    "contact_info": extracted_info["contact_info"],
                    "summary": cv_text[:500]
                }
                self.cv_metadata.append(metadata)
                
                self._save_index()
                
                print(f"✅ Added {candidate_name} to database and vector index")
            
            return db_result
            
        except Exception as e:
            return {"success": False, "message": f"Error processing CV: {str(e)}"}
    
    def extract_text_from_file(self, file_path: str) -> str:
        """Extract text from various file formats"""
        try:
            file_extension = os.path.splitext(file_path)[1].lower()
            
            if file_extension == '.pdf':
                return self._extract_from_pdf(file_path)
            elif file_extension == '.docx':
                return self._extract_from_docx(file_path)
            elif file_extension == '.txt':
                return self._extract_from_txt(file_path)
            else:
                return f"Unsupported file format: {file_extension}"
                
        except Exception as e:
            return f"Error reading file: {str(e)}"
    
    def _extract_from_pdf(self, pdf_path: str) -> str:
        """Extract text from PDF file"""
        try:
            reader = PdfReader(pdf_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
            return text
        except Exception as e:
            return f"Error reading PDF: {str(e)}"
    
    def _extract_from_docx(self, docx_path: str) -> str:
        """Extract text from DOCX file"""
        try:
            text = docx2txt.process(docx_path)
            return text
        except Exception as e:
            return f"Error reading DOCX: {str(e)}"
    
    def _extract_from_txt(self, txt_path: str) -> str:
        """Extract text from TXT file"""
        try:
            with open(txt_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            return f"Error reading TXT: {str(e)}"
    
    def _extract_cv_information(self, cv_text: str) -> Dict[str, Any]:
        """Extract key information from CV text"""
        try:
            info = {
                "skills": [],
                "experience_years": 0,
                "education": [],
                "contact_info": {}
            }
            
            # Extract skills
            skill_patterns = [
                r'\b(?:Java|Python|JavaScript|React|Angular|Vue|Node\.js|Spring|Django|Flask)\b',
                r'\b(?:AWS|Azure|Docker|Kubernetes|Git|Jenkins|MySQL|PostgreSQL|MongoDB)\b',
                r'\b(?:HTML|CSS|TypeScript|jQuery|Bootstrap)\b'
            ]
            
            for pattern in skill_patterns:
                matches = re.findall(pattern, cv_text, re.IGNORECASE)
                info["skills"].extend([match.lower() for match in matches])
            
            info["skills"] = list(set(info["skills"]))
            
            # Extract experience years
            exp_patterns = [
                r'(\d+)\+?\s*years?\s*(?:of\s*)?experience',
                r'experience[:\s]*(\d+)\+?\s*years?'
            ]
            
            for pattern in exp_patterns:
                matches = re.findall(pattern, cv_text, re.IGNORECASE)
                if matches:
                    years = [int(match) for match in matches if match.isdigit()]
                    if years:
                        info["experience_years"] = max(years)
                        break
            
            # Extract education
            edu_patterns = [
                r'(?:Bachelor|Master|PhD|BSc|MSc)[^.]*',
                r'University[^.]*'
            ]
            
            for pattern in edu_patterns:
                matches = re.findall(pattern, cv_text, re.IGNORECASE)
                info["education"].extend(matches)
            
            # Extract contact info
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            phone_pattern = r'\+?[\d\s\-\(\)]{10,}'
            
            emails = re.findall(email_pattern, cv_text)
            phones = re.findall(phone_pattern, cv_text)
            
            if emails:
                info["contact_info"]["email"] = emails[0]
            if phones:
                info["contact_info"]["phone"] = phones[0].strip()
            
            return info
            
        except Exception as e:
            print(f"❌ Error extracting CV information: {e}")
            return {
                "skills": [],
                "experience_years": 0,
                "education": [],
                "contact_info": {}
            }
    
    def _save_index(self):
        """Save vector index and metadata"""
        try:
            if self.index is not None:
                faiss.write_index(self.index, os.path.join(self.vector_store_dir, "cv_index.faiss"))
                with open(os.path.join(self.vector_store_dir, "metadata.pkl"), "wb") as f:
                    pickle.dump(self.cv_metadata, f)
                print("💾 Vector index saved")
        except Exception as e:
            print(f"❌ Error saving index: {e}")
    
    def _load_index(self):
        """Load existing vector index and metadata"""
        try:
            index_path = os.path.join(self.vector_store_dir, "cv_index.faiss")
            metadata_path = os.path.join(self.vector_store_dir, "metadata.pkl")
            
            if os.path.exists(index_path) and os.path.exists(metadata_path):
                self.index = faiss.read_index(index_path)
                with open(metadata_path, "rb") as f:
                    self.cv_metadata = pickle.load(f)
                print(f"💾 Loaded vector index with {len(self.cv_metadata)} candidates")
        except Exception as e:
            print(f"❌ Error loading index: {e}")
            self.index = None
            self.cv_metadata = []