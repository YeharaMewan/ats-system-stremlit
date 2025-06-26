import streamlit as st
import requests
import json

# Page configuration
st.set_page_config(
    page_title="HR Chat System",
    page_icon="💬",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 2rem;
        text-align: center;
    }
    .user-info {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #28a745;
        margin-bottom: 1rem;
    }
    .admin-badge {
        background: #dc3545;
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 15px;
        font-size: 0.8rem;
        font-weight: bold;
    }
    .user-badge {
        background: #007bff;
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 15px;
        font-size: 0.8rem;
        font-weight: bold;
    }
    .login-container {
        max-width: 400px;
        margin: 2rem auto;
        padding: 2rem;
        background: #f8f9fa;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

# Backend URL
BACKEND_URL = "http://localhost:5000"

# Initialize session for persistent cookies
if 'requests_session' not in st.session_state:
    st.session_state.requests_session = requests.Session()

def check_backend_health():
    """Check if backend is running"""
    try:
        response = st.session_state.requests_session.get(f"{BACKEND_URL}/", timeout=5)
        return response.status_code == 200, response.json()
    except Exception as e:
        return False, {"error": str(e)}

def login_user(username, password):
    """Login user with session persistence"""
    try:
        response = st.session_state.requests_session.post(
            f"{BACKEND_URL}/login",
            json={"username": username, "password": password},
            timeout=10
        )
        
        return response.json(), response.status_code == 200
    except Exception as e:
        return {"error": str(e)}, False

def logout_user():
    """Logout user"""
    try:
        response = st.session_state.requests_session.post(f"{BACKEND_URL}/logout", timeout=10)
        return response.json(), response.status_code == 200
    except Exception as e:
        return {"error": str(e)}, False

def get_current_user():
    """Get current logged in user"""
    try:
        response = st.session_state.requests_session.get(f"{BACKEND_URL}/current-user", timeout=10)
        if response.status_code == 200:
            return response.json().get("user"), True
        return None, False
    except Exception as e:
        return None, False

def send_chat_message(message):
    """Send chat message to backend with session"""
    try:
        response = st.session_state.requests_session.post(
            f"{BACKEND_URL}/chat",
            json={"message": message},
            timeout=30
        )
        
        return response.json(), response.status_code == 200
    except Exception as e:
        return {"error": str(e)}, False

def main():
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🚀 HR Chat System</h1>
        <p>AI-Powered Human Resource Management with MongoDB Integration</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Check backend health
    backend_healthy, health_data = check_backend_health()
    
    if not backend_healthy:
        st.error("""
        ❌ **Backend Server Connection Failed!**
        
        Please ensure the backend server is running:
        1. `cd backend`
        2. `python app.py`
        
        Also ensure MongoDB is running on localhost:27017
        """)
        
        with st.expander("🔍 Debug Information"):
            st.json(health_data)
        return
    
    # Show backend status
    with st.sidebar:
        st.success("✅ Backend Connected")
        with st.expander("🔍 System Status"):
            st.json(health_data)
    
    # Check if user is logged in by calling backend
    current_user, is_logged_in = get_current_user()
    
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    
    # Update session state based on backend response
    if is_logged_in and current_user:
        st.session_state.logged_in = True
        st.session_state.user = current_user
    elif not is_logged_in:
        st.session_state.logged_in = False
        if 'user' in st.session_state:
            del st.session_state.user
    
    if not st.session_state.logged_in:
        show_login_page()
    else:
        show_chat_interface()

def show_login_page():
    """Display login page"""
    st.markdown("""
    <div class="login-container">
        <h2 style="text-align: center; margin-bottom: 2rem;">🔐 Login to HR System</h2>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.form("login_form"):
            username = st.text_input("👤 Username")
            password = st.text_input("🔒 Password", type="password")
            submit = st.form_submit_button("🚀 Login", use_container_width=True)
            
            if submit:
                if username and password:
                    with st.spinner("🔐 Logging in..."):
                        result, success = login_user(username, password)
                        
                        if success:
                            st.session_state.logged_in = True
                            st.session_state.user = result['user']
                            st.success(f"✅ {result['message']}")
                            st.rerun()
                        else:
                            st.error(f"❌ {result.get('error', 'Login failed')}")
                else:
                    st.error("❌ Please enter both username and password")
        
        # Demo credentials
        st.markdown("---")
        st.markdown("### 🧪 Demo Credentials")
        
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("""
            **👑 Admin Access:**
            ```
            Username: admin
            Password: admin123
            ```
            """)
        
        with col_b:
            st.markdown("""
            **👤 User Access:**
            ```
            Username: kasun
            Password: user123
            ```
            """)

def show_chat_interface():
    """Display main chat interface"""
    user = st.session_state.get('user', {})
    
    # User info and logout
    col1, col2, col3 = st.columns([3, 1, 1])
    
    with col1:
        role_badge = "admin-badge" if user.get('role') == 'admin' else "user-badge"
        role_text = "👑 HR Admin" if user.get('role') == 'admin' else "👤 User"
        
        st.markdown(f"""
        <div class="user-info">
            <strong>Welcome, {user.get('name', 'User')}</strong>
            <span class="{role_badge}">{role_text}</span>
            <br>
            <small>📧 {user.get('email', 'N/A')} • 🆔 {user.get('employee_id', 'N/A')}</small>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        if st.button("🚪 Logout", use_container_width=True):
            logout_user()
            st.session_state.logged_in = False
            if 'user' in st.session_state:
                del st.session_state.user
            if 'messages' in st.session_state:
                del st.session_state.messages
            st.rerun()
    
    # Initialize chat history
    if 'messages' not in st.session_state:
        role = user.get('role', 'user')
        name = user.get('name', 'User')
        emp_id = user.get('employee_id', 'EMP001')
        
        if role == 'admin':
            welcome_msg = f"""👋 **Hello {name}! Welcome to the HR Chat System.**

🎯 **As an HR Admin, you have access to:**

🔍 **Candidate Management (ATS):**
- "Search for Java developers"
- "Show me all candidates"
- "Find candidates with Python experience"

💰 **Payroll Management:**
- "Calculate salary for EMP001"
- "Calculate salary for EMP014"
- "Generate payroll report for IT department"
- "Show all employees"

What would you like to do today?"""
        else:
            welcome_msg = f"""👋 **Hello {name}! Welcome to the HR Chat System.**

🎯 **As a regular user, you can:**

💰 **Your Payroll Information:**
- "Calculate salary for {emp_id}"
- "Show my payroll details"

📋 **General HR Inquiries:**
- Ask about company policies
- Get help with HR procedures

📝 **Note:** For candidate management and other employees' information, please contact HR Admin.

How can I help you today?"""
        
        st.session_state.messages = [
            {"role": "assistant", "content": welcome_msg}
        ]
    
    # Chat interface
    st.markdown("### 💬 Chat with HR Assistant")
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Type your message here... (e.g., 'Calculate salary for EMP014')"):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get AI response
        with st.chat_message("assistant"):
            with st.spinner("🤔 Processing your request..."):
                response_data, success = send_chat_message(prompt)
                
                if success:
                    response = response_data.get("response", "Sorry, I couldn't process your request.")
                else:
                    error_msg = response_data.get('error', 'Unknown error occurred')
                    if "login" in error_msg.lower():
                        st.error("🔒 Session expired. Please refresh the page and login again.")
                        st.session_state.logged_in = False
                        st.rerun()
                    response = f"❌ **Error:** {error_msg}"
                
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
    
    # Quick action buttons based on role
    st.markdown("### ⚡ Quick Actions")
    
    if user.get('role') == 'admin':
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("🔍 Search Java Developers", use_container_width=True):
                st.session_state.messages.append({"role": "user", "content": "Search for Java developers"})
                st.rerun()
        
        with col2:
            if st.button("📋 Show All Candidates", use_container_width=True):
                st.session_state.messages.append({"role": "user", "content": "Show me all candidates"})
                st.rerun()
        
        with col3:
            if st.button("💰 Calculate EMP014 Salary", use_container_width=True):
                st.session_state.messages.append({"role": "user", "content": "Calculate salary for EMP014"})
                st.rerun()
        
        with col4:
            if st.button("📊 Payroll Report", use_container_width=True):
                st.session_state.messages.append({"role": "user", "content": "Generate payroll report"})
                st.rerun()
    
    else:
        col1, col2, col3 = st.columns(3)
        emp_id = user.get('employee_id', 'EMP001')
        
        with col1:
            if st.button(f"💰 My Salary ({emp_id})", use_container_width=True):
                st.session_state.messages.append({"role": "user", "content": f"Calculate salary for {emp_id}"})
                st.rerun()
        
        with col2:
            if st.button("❓ Help", use_container_width=True):
                st.session_state.messages.append({"role": "user", "content": "What can you help me with?"})
                st.rerun()
        
        with col3:
            if st.button("📋 HR Policies", use_container_width=True):
                st.session_state.messages.append({"role": "user", "content": "Tell me about HR policies"})
                st.rerun()

if __name__ == "__main__":
    main()