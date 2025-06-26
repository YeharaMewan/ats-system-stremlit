from flask import Flask, request, jsonify, session
from flask_cors import CORS
import os
from dotenv import load_dotenv
import sys

# Add current directory to Python path
sys.path.append(os.path.dirname(__file__))

from agents.graph import HRAgent
from services.user_service import UserService
import traceback
from datetime import datetime

# Load environment variables
load_dotenv()

app = Flask(__name__)

# CORS configuration
CORS(app, 
     supports_credentials=True,
     origins=["http://localhost:8501", "http://127.0.0.1:8501"],
     allow_headers=["Content-Type", "Authorization"],
     methods=["GET", "POST", "OPTIONS"])

app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

print("🚀 Starting HR System Backend...")

# Initialize services
try:
    user_service = UserService()
    print("✅ UserService initialized")
except Exception as e:
    print(f"❌ Error initializing UserService: {e}")
    user_service = None

# Initialize the HR Agent
try:
    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
    if not GOOGLE_API_KEY:
        print("❌ GOOGLE_API_KEY not found in environment variables")
        print("Please set your Google API key in the .env file")
        hr_agent = None
    else:
        DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
        hr_agent = HRAgent(GOOGLE_API_KEY, DATA_DIR)
        print("✅ HR Agent initialized successfully!")
    
except Exception as e:
    print(f"❌ Error initializing HR Agent: {e}")
    print(traceback.format_exc())
    hr_agent = None

@app.route('/', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "message": "🚀 Agentic HR System Backend is running!",
        "agent_status": "✅ initialized" if hr_agent else "❌ failed",
        "user_service": "✅ initialized" if user_service else "❌ failed",
        "session_id": session.get('_id', 'no-session'),
        "database": "📊 MongoDB Connected"
    })

@app.route('/login', methods=['POST'])
def login():
    """User login endpoint using MongoDB"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        print(f"🔐 Login attempt for user: {username}")
        
        if not username or not password:
            return jsonify({"error": "Username and password required"}), 400
        
        if not user_service:
            return jsonify({"error": "User service not available"}), 500
        
        # Authenticate using UserService
        user = user_service.authenticate_user(username, password)
        
        if user:
            session['user'] = user
            session.permanent = True
            
            print(f"✅ Login successful for {username} - Role: {user['role']}")
            
            return jsonify({
                "success": True,
                "user": user,
                "message": f"Welcome {user['name']}!"
            })
        else:
            print(f"❌ Login failed for {username}")
            return jsonify({"error": "Invalid credentials"}), 401
            
    except Exception as e:
        print(f"❌ Login error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/logout', methods=['POST'])
def logout():
    """User logout endpoint"""
    user = session.get('user', {})
    print(f"👋 Logout request for: {user.get('name', 'Unknown')}")
    session.clear()
    return jsonify({"success": True, "message": "Logged out successfully"})

@app.route('/current-user', methods=['GET'])
def current_user():
    """Get current logged in user"""
    user = session.get('user')
    
    if user:
        print(f"👤 Current user check: {user['name']} ({user['role']})")
        return jsonify({"user": user})
    else:
        print("❌ No user in session")
        return jsonify({"error": "Not logged in"}), 401

@app.route('/chat', methods=['POST'])
def chat():
    """Main chat endpoint with role-based access control"""
    try:
        # Check if user is logged in
        user = session.get('user')
        if not user:
            print("❌ No user in session - authentication required")
            return jsonify({"error": "Please login to access the system"}), 401
        
        print(f"💬 Chat request from: {user['name']} ({user['role']})")
        
        if not hr_agent:
            return jsonify({
                "error": "HR Agent not initialized. Please check your GOOGLE_API_KEY."
            }), 500
        
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({"error": "Message is required"}), 400
        
        user_message = data['message']
        print(f"📝 Processing message: '{user_message}'")
        
        # Process the query using the HR Agent with user context
        response = hr_agent.process_query(user_message, user)
        
        print(f"✅ Response generated successfully")
        return jsonify({
            "response": response,
            "status": "success"
        })
    
    except Exception as e:
        print(f"❌ Error in chat endpoint: {e}")
        print(traceback.format_exc())
        return jsonify({
            "error": f"Internal server error: {str(e)}"
        }), 500

@app.route('/upload-cv', methods=['POST'])
def upload_cv():
    """CV upload endpoint - Admin only"""
    try:
        user = session.get('user')
        if not user:
            return jsonify({"error": "Please login to access the system"}), 401
        
        if user['role'] != 'admin':
            return jsonify({"error": "Access denied. Admin privileges required."}), 403
        
        if not hr_agent:
            return jsonify({"error": "HR Agent not initialized"}), 500
        
        if 'file' not in request.files:
            return jsonify({"error": "No file uploaded"}), 400
        
        file = request.files['file']
        candidate_name = request.form.get('candidate_name', 'Unknown')
        position = request.form.get('position', 'Unknown')
        
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        # Check supported file formats
        allowed_extensions = {'.pdf', '.docx', '.doc', '.txt'}
        file_extension = os.path.splitext(file.filename)[1].lower()
        
        if file_extension not in allowed_extensions:
            return jsonify({
                "error": f"Unsupported file format. Supported formats: {', '.join(allowed_extensions)}"
            }), 400
        
        # Create unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{candidate_name.replace(' ', '_')}_{position.replace(' ', '_')}_{timestamp}{file_extension}"
        file_path = os.path.join(hr_agent.ats_tools.cv_dir, filename)
        
        # Save the file
        file.save(file_path)
        print(f"📄 File saved: {filename}")
        
        # Add to database
        result = hr_agent.ats_tools.add_cv_to_database(file_path, candidate_name, position)
        
        return jsonify(result)
    
    except Exception as e:
        print(f"❌ Error in upload_cv endpoint: {e}")
        return jsonify({"error": f"Upload failed: {str(e)}"}), 500

if __name__ == '__main__':
    port = int(os.getenv('FLASK_PORT', 5000))
    print(f"\n🌐 Starting Flask server on port {port}")
    print("🔗 Backend will be available at: http://localhost:5000")
    print("🚀 Ready to receive requests!\n")
    app.run(debug=True, host='0.0.0.0', port=port)