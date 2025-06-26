import streamlit as st
import json
from main_agent import run_agent # We will modify main_agent.py next

def check_login(username, password):
    """Loads users from JSON and checks credentials."""
    with open('users.json', 'r') as f:
        users = json.load(f)
    for user in users:
        if user['username'] == username and user['password'] == password:
            return user
    return None

# --- Main App Logic ---

st.set_page_config(page_title="Agentic HR System", page_icon="🤖", layout="wide")

# Initialize session state variables if they don't exist
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['username'] = ''
    st.session_state['role'] = ''
    st.session_state['employee_id'] = ''
    st.session_state['messages'] = []

# --- Login Interface ---
if not st.session_state['logged_in']:
    st.title("Welcome to the Agentic HR System")
    st.subheader("Please Log In")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

        if submitted:
            user_data = check_login(username, password)
            if user_data:
                st.session_state['logged_in'] = True
                st.session_state['username'] = user_data['username']
                st.session_state['role'] = user_data['role']
                st.session_state['employee_id'] = user_data['employee_id']
                st.rerun() # Rerun the app to show the main chat interface
            else:
                st.error("Invalid username or password")

# --- Main Chat Interface (shown after login) ---
else:
    st.sidebar.title(f"Welcome, {st.session_state['username']}!")
    st.sidebar.write(f"**Role:** {st.session_state['role'].replace('_', ' ').title()}")
    st.sidebar.write(f"**Employee ID:** {st.session_state['employee_id']}")
    if st.sidebar.button("Logout"):
        # Clear all session data on logout
        for key in st.session_state.keys():
            del st.session_state[key]
        st.rerun()

    st.title("🤖 Agentic HR System")
    st.caption("Your AI assistant for HR tasks.")

    # Initialize chat history for the main interface
    if not st.session_state['messages']:
         st.session_state['messages'] = [{"role": "assistant", "content": "How can I assist you today?"}]

    # Display chat messages
    for message in st.session_state['messages']:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Get user input
    if prompt := st.chat_input("Ask about candidates, your payroll, etc."):
        # Add user message to history and display it
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Get agent response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                # Pass user's role and ID to the agent runner
                response = run_agent(
                    user_input=prompt,
                    user_role=st.session_state['role'],
                    user_employee_id=st.session_state['employee_id']
                )
                st.markdown(response)
        
        # Add assistant response to history
        st.session_state.messages.append({"role": "assistant", "content": response})