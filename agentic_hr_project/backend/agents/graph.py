from typing import Dict, Any, List, TypedDict
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from agents.ats_tools import ATSTools
from agents.payroll_tools import PayrollTools

# State definition for LangGraph
class AgentState(TypedDict):
    messages: List[Dict[str, str]]
    user_query: str
    user_context: Dict[str, Any]
    intent: str
    tool_result: Dict[str, Any]
    final_response: str
    permission_granted: bool
    denied_reason: str

class HRAgent:
    def __init__(self, google_api_key: str, data_dir: str):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-pro",
            google_api_key=google_api_key,
            temperature=0.3
        )
        
        print("🤖 Initializing HR Agent...")
        
        # Initialize tools
        self.ats_tools = ATSTools(data_dir)
        self.payroll_tools = PayrollTools(data_dir)
        
        # Build the graph
        self.graph = self._build_graph()
        
        print("✅ HR Agent fully initialized with LangGraph workflow")
    
    def _build_graph(self) -> CompiledStateGraph:
        """Build the LangGraph workflow"""
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("check_permissions", self._check_permissions)
        workflow.add_node("classify_intent", self._classify_intent)
        workflow.add_node("handle_ats", self._handle_ats)
        workflow.add_node("handle_payroll", self._handle_payroll)
        workflow.add_node("generate_response", self._generate_response)
        workflow.add_node("access_denied", self._access_denied)
        
        # Add edges
        workflow.set_entry_point("check_permissions")
        workflow.add_conditional_edges(
            "check_permissions",
            self._permission_router,
            {
                "allowed": "classify_intent",
                "denied": "access_denied"
            }
        )
        workflow.add_conditional_edges(
            "classify_intent",
            self._route_based_on_intent,
            {
                "ats": "handle_ats",
                "payroll": "handle_payroll",
                "general": "generate_response"
            }
        )
        workflow.add_edge("handle_ats", "generate_response")
        workflow.add_edge("handle_payroll", "generate_response")
        workflow.add_edge("generate_response", END)
        workflow.add_edge("access_denied", END)
        
        return workflow.compile()
    
    def _extract_employee_id_or_name(self, query: str) -> str:
        """Extract employee ID or name from query - ENHANCED VERSION"""
        import re
        
        print(f"🔍 Extracting identifier from query: '{query}'")
        
        # First, try to extract employee ID patterns like EMP001, EMP014, ADM001
        emp_id_match = re.search(r'(EMP\d{3}|ADM\d{3})', query.upper())
        if emp_id_match:
            extracted_id = emp_id_match.group()
            print(f"✅ Extracted employee ID: {extracted_id}")
            return extracted_id
        
        # If no ID found, try to extract name with enhanced patterns
        name_patterns = [
            # Pattern 1: "salary for John Doe"
            r'(?:salary for|calculate salary for|payroll for|salary of)\s+([A-Za-z\s]+?)(?:\s*$|[?.!,])',
            # Pattern 2: "for John Doe Smith"  
            r'(?:for)\s+([A-Za-z]+(?:\s+[A-Za-z]+){1,2})(?:\s|$)',
            # Pattern 3: "John Doe" (2-3 words)
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})\b',
            # Pattern 4: Any sequence of 2+ capitalized words
            r'\b([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b'
        ]
        
        # Words to exclude from name extraction
        excluded_words = {
            'salary', 'for', 'calculate', 'payroll', 'employee', 'the', 'a', 'an', 
            'my', 'me', 'show', 'get', 'help', 'with', 'details', 'information',
            'smith', 'john', 'jane', 'doe'  # Common test names
        }
        
        for i, pattern in enumerate(name_patterns):
            matches = re.findall(pattern, query, re.IGNORECASE)
            print(f"🔍 Pattern {i+1} matches: {matches}")
            
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]  # Take first group if tuple
                
                extracted_name = match.strip()
                
                # Clean the extracted name
                name_words = extracted_name.lower().split()
                clean_words = [word for word in name_words if word not in excluded_words and len(word) > 1]
                
                if len(clean_words) >= 1:  # At least 1 valid word
                    clean_name = ' '.join(clean_words).title()
                    if len(clean_name) > 2:  # At least 3 characters
                        print(f"✅ Extracted employee name: '{clean_name}' (from pattern {i+1})")
                        return clean_name
        
        # If no good pattern match, look for any capitalized words that might be names
        words = query.split()
        potential_names = []
        
        for word in words:
            cleaned_word = re.sub(r'[^\w]', '', word)  # Remove punctuation
            if (len(cleaned_word) > 2 and 
                cleaned_word[0].isupper() and 
                cleaned_word.lower() not in excluded_words):
                potential_names.append(cleaned_word)
        
        if len(potential_names) >= 2:
            combined_name = ' '.join(potential_names[:3])  # Max 3 words
            print(f"✅ Extracted potential name from words: '{combined_name}'")
            return combined_name
        
        print(f"❌ No employee ID or name extracted from: '{query}'")
        return None
        
    def _check_permissions(self, state: AgentState) -> AgentState:
        """Check user permissions - FIXED VERSION"""
        user_role = state["user_context"].get('role', 'user')
        user_employee_id = state["user_context"].get('employee_id')
        query = state["user_query"].lower()
    
        print(f"🔐 Checking permissions for {user_role} (ID: {user_employee_id}): '{query}'")
    
        # Admin can do everything
        if user_role == 'admin':
            state["permission_granted"] = True
            print("✅ Admin access granted")
            return state
    
        # User role restrictions
        if user_role == 'user':
            # Check if trying to access ATS functions
            ats_keywords = ['search', 'candidate', 'cv', 'applicant', 'hire', 'recruit']
            if any(keyword in query for keyword in ats_keywords):
                state["permission_granted"] = False
                state["denied_reason"] = "ATS access is restricted to HR Admin users only."
                print("❌ ATS access denied for regular user")
                return state
        
            # Check payroll access - FIXED LOGIC
            payroll_keywords = ['salary', 'payroll', 'calculate']
            if any(keyword in query for keyword in payroll_keywords):
                # Extract employee identifier from query
                extracted_identifier = self._extract_employee_id_or_name(query)
            
                print(f"🔍 Extracted identifier: '{extracted_identifier}', User ID: '{user_employee_id}'")
            
                # Allow access if:
                # 1. No specific employee mentioned (general payroll query)
                # 2. User's own employee ID is mentioned
                # 3. User's own name is mentioned (partial match)
                if extracted_identifier:
                    user_name = state["user_context"].get('name', '')
                
                    # Check if it matches user's employee ID
                    if extracted_identifier.upper() == user_employee_id:
                        print("✅ User accessing own employee ID")
                        state["permission_granted"] = True
                        return state
                
                    # Check if it matches user's name (case insensitive)
                    if user_name and extracted_identifier.lower() in user_name.lower():
                        print("✅ User accessing own name")
                        state["permission_granted"] = True
                        return state
                
                    # Check if extracted name matches user name (reverse)
                    if user_name and user_name.lower() in extracted_identifier.lower():
                        print("✅ User name matches extracted identifier")
                        state["permission_granted"] = True
                        return state
                
                    # If none match, deny access
                    state["permission_granted"] = False
                    state["denied_reason"] = f"You can only access your own payroll information. Use your Employee ID '{user_employee_id}' or your name '{user_name}'."
                    print(f"❌ Payroll access denied - '{extracted_identifier}' doesn't match user '{user_employee_id}' or '{user_name}'")
                    return state
                else:
                    # No specific employee mentioned - allow general payroll queries
                    print("✅ General payroll query allowed")
                    state["permission_granted"] = True
                    return state
        
        # Check if trying to access other admin functions
        admin_keywords = ['all employees', 'list employees', 'payroll report', 'generate report']
        if any(keyword in query for keyword in admin_keywords):
            state["permission_granted"] = False
            state["denied_reason"] = "This function is available to HR Admin only."
            print("❌ Admin function access denied for regular user")
            return state
    
        # Allow all other queries
        state["permission_granted"] = True
        print("✅ Permission granted")
        return state
    
    def _permission_router(self, state: AgentState) -> str:
        """Route based on permission check"""
        return "allowed" if state["permission_granted"] else "denied"
    
    def _access_denied(self, state: AgentState) -> AgentState:
        """Handle access denied cases"""
        user_role = state["user_context"].get('role', 'user')
        user_name = state["user_context"].get('name', 'User')
        
        state["final_response"] = f"""
🚫 Access Denied

Hello {user_name}, {state["denied_reason"]}

As a regular user, you can:
• Check your own salary: "Calculate salary for {state["user_context"].get('employee_id')}"
• Ask general questions about HR policies
• Get help with the system

For candidate management and ATS functions, please contact your HR Admin.
"""
        return state
    
    def _classify_intent(self, state: AgentState) -> AgentState:
        """Classify user intent"""
        try:
            query = state["user_query"].lower()
            print(f"🧠 Classifying intent for: '{query}'")
            
            # Simple rule-based classification
            if any(keyword in query for keyword in ['search', 'candidate', 'cv', 'applicant', 'hire', 'recruit']):
                intent = "ats"
            elif any(keyword in query for keyword in ['salary', 'payroll', 'calculate', 'employee', 'report']):
                intent = "payroll"
            else:
                intent = "general"
            
            state["intent"] = intent
            print(f"🎯 Intent classified as: {intent}")
            return state
            
        except Exception as e:
            print(f"❌ Error classifying intent: {e}")
            state["intent"] = "general"
            return state
    
    def _route_based_on_intent(self, state: AgentState) -> str:
        """Route based on classified intent"""
        return state["intent"]
    
    def _handle_ats(self, state: AgentState) -> AgentState:
        """Handle ATS related tasks"""
        try:
            query = state["user_query"].lower()
            print(f"📋 Handling ATS request: '{query}'")
            
            if "search" in query or "find" in query:
                search_terms = self._extract_search_terms(state["user_query"])
                print(f"🔍 Searching for: '{search_terms}'")
                results = self.ats_tools.search_candidates(search_terms)
                state["tool_result"] = {"type": "candidate_search", "results": results}
                
            elif "all candidates" in query or "list candidates" in query:
                print("📋 Getting all candidates")
                results = self.ats_tools.get_all_candidates()
                state["tool_result"] = {"type": "all_candidates", "results": results}
                
            else:
                state["tool_result"] = {
                    "type": "ats_help",
                    "message": "I can help you with: searching candidates, viewing all candidates, or managing CV applications."
                }
            
        except Exception as e:
            print(f"❌ ATS error: {e}")
            state["tool_result"] = {"type": "error", "message": f"ATS error: {str(e)}"}
        
        return state
    
    def _handle_payroll(self, state: AgentState) -> AgentState:
        """Handle payroll related tasks - ENHANCED WITH BETTER ERROR HANDLING"""
        try:
            query = state["user_query"].lower()
            user_role = state["user_context"].get('role', 'user')
            user_employee_id = state["user_context"].get('employee_id')
            user_name = state["user_context"].get('name', '')
            
            print(f"💰 Handling payroll request: '{query}' for role: {user_role}")
            print(f"👤 User context: ID={user_employee_id}, Name={user_name}")
            
            if "calculate salary" in query or "salary for" in query or "salary" in query or "payroll" in query:
                emp_identifier = self._extract_employee_id_or_name(state["user_query"])
                print(f"💰 Extracted employee identifier: '{emp_identifier}'")
                
                # For non-admin users, enforce access control
                if user_role != 'admin':
                    print(f"🔒 Non-admin user access control check")
                    
                    # If no identifier extracted, use user's own data
                    if not emp_identifier:
                        emp_identifier = user_employee_id
                        print(f"🔒 No identifier specified, using user's own ID: {emp_identifier}")
                    else:
                        # Check if the identifier matches the user
                        identifier_matches_user = False
                        
                        # Check employee ID match
                        if emp_identifier.upper() == user_employee_id:
                            identifier_matches_user = True
                            print(f"✅ Identifier matches user employee ID")
                        
                        # Check name match (case insensitive, partial)
                        elif user_name:
                            user_name_lower = user_name.lower()
                            identifier_lower = emp_identifier.lower()
                            
                            if (identifier_lower in user_name_lower or 
                                user_name_lower in identifier_lower or
                                any(part in identifier_lower for part in user_name_lower.split()) or
                                any(part in user_name_lower for part in identifier_lower.split())):
                                identifier_matches_user = True
                                print(f"✅ Identifier matches user name")
                        
                        if not identifier_matches_user:
                            # Return access denied message instead of forcing
                            state["tool_result"] = {
                                "type": "error", 
                                "message": f"Access denied. You can only access your own payroll information. Use '{user_employee_id}' or '{user_name}'"
                            }
                            return state
                
                # Proceed with salary calculation
                if emp_identifier:
                    print(f"💰 Proceeding with salary calculation for: '{emp_identifier}'")
                    
                    # Try the calculation
                    try:
                        result = self.payroll_tools.calculate_salary(emp_identifier)
                        
                        # Check if it's an access denied error for non-admin users
                        if "error" in result and user_role != 'admin':
                            # For regular users, if their identifier doesn't work, try their employee ID
                            if emp_identifier != user_employee_id:
                                print(f"🔄 Retrying with user's employee ID: {user_employee_id}")
                                result = self.payroll_tools.calculate_salary(user_employee_id)
                        
                        state["tool_result"] = {"type": "salary_calculation", "result": result}
                        
                    except Exception as e:
                        print(f"❌ Salary calculation failed: {e}")
                        state["tool_result"] = {
                            "type": "error", 
                            "message": f"Error calculating salary: {str(e)}"
                        }
                else:
                    state["tool_result"] = {
                        "type": "error", 
                        "message": f"Please specify your employee ID '{user_employee_id}' or use your name '{user_name}'"
                    }
            
            elif "payroll report" in query or "generate report" in query or "report" in query:
                if user_role == 'admin':
                    department = self._extract_department(state["user_query"])
                    print(f"📊 Generating payroll report for: {department or 'all departments'}")
                    try:
                        result = self.payroll_tools.generate_payroll_report(department)
                        state["tool_result"] = {"type": "payroll_report", "result": result}
                    except Exception as e:
                        print(f"❌ Payroll report failed: {e}")
                        state["tool_result"] = {"type": "error", "message": f"Error generating report: {str(e)}"}
                else:
                    state["tool_result"] = {"type": "error", "message": "Payroll reports are available to HR Admin only"}
            
            elif "all employees" in query or "list employees" in query or "show employees" in query:
                if user_role == 'admin':
                    print("👥 Getting all employees")
                    try:
                        results = self.payroll_tools.get_all_employees()
                        if results and len(results) > 0 and "error" not in results[0]:
                            state["tool_result"] = {"type": "all_employees", "results": results}
                        else:
                            error_msg = results[0].get("error", "No employees found") if results else "No employees found"
                            state["tool_result"] = {"type": "error", "message": error_msg}
                    except Exception as e:
                        print(f"❌ Get all employees failed: {e}")
                        state["tool_result"] = {"type": "error", "message": f"Error getting employees: {str(e)}"}
                else:
                    state["tool_result"] = {"type": "error", "message": "Employee list is available to HR Admin only"}
            
            elif "debug" in query and user_role == 'admin':
                # Debug functionality for admin users
                print("🔧 Running debug for admin user")
                try:
                    debug_info = self.payroll_tools.debug_employee_data()
                    state["tool_result"] = {"type": "debug_info", "result": debug_info}
                except Exception as e:
                    state["tool_result"] = {"type": "error", "message": f"Debug failed: {str(e)}"}
            
            else:
                # General payroll help
                if user_role == 'admin':
                    help_message = """I can help you with:
    • "Calculate salary for [Employee ID or Name]"
    • "Generate payroll report"
    • "Show all employees"
    • "Generate payroll report for [Department]"
    """
                else:
                    help_message = f"""I can help you check your salary:
    • "Calculate salary for {user_employee_id}"
    • "Calculate salary for {user_name}"
    • "Show my payroll details"
    • "Calculate my salary"
    """
                
                state["tool_result"] = {
                    "type": "payroll_help",
                    "message": help_message
                }
                
        except Exception as e:
            print(f"❌ Payroll handler error: {e}")
            import traceback
            traceback.print_exc()
            state["tool_result"] = {"type": "error", "message": f"Payroll system error: {str(e)}"}
        
        return state
    
    def _generate_response(self, state: AgentState) -> AgentState:
        """Generate final response"""
        try:
            user_name = state["user_context"].get('name', 'User')
            user_role = state["user_context"].get('role', 'user')
            
            if state["intent"] == "general":
                state["final_response"] = self._generate_general_response(state["user_query"], user_name, user_role)
            else:
                state["final_response"] = self._format_tool_result(state["tool_result"], user_role)
        except Exception as e:
            print(f"❌ Error generating response: {e}")
            state["final_response"] = f"Error generating response: {str(e)}"
        
        return state
    
    def _generate_general_response(self, query: str, user_name: str, user_role: str) -> str:
        """Generate context-aware general responses based on user role and query"""
        query_lower = query.lower()
        
        if user_role == 'admin':
            capabilities = """
    🎯 As an HR Admin, you have full access to:

    **🔍 Candidate Management (ATS):**
    • "Search for Java developers"
    • "Show me all candidates"
    • "Find candidates with Python experience"

    **💰 Payroll Management:**
    • "Calculate salary for EMP001"
    • "Calculate salary for EMP014"
    • "Generate payroll report for IT department"
    • "Show all employees"

    **⚙️ System Administration:**
    • Upload candidate CVs
    • Manage employee data
    """
            return f"👋 Hello {user_name}!\n\n{capabilities}\n\nHow can I help you today?"
        
        else:
            # User-specific responses based on query context
            if any(keyword in query_lower for keyword in ['policy', 'policies', 'company policy']):
                return f"""
    📋 **Company HR Policies - {user_name}**

    **🏢 Work Policies:**
    • Working Hours: 9:00 AM - 6:00 PM (Monday to Friday)
    • Remote Work: Hybrid model available (3 days office, 2 days remote)
    • Break Time: 1 hour lunch break + 2x 15-minute tea breaks

    **🏖️ Leave Policies:**
    • Annual Leave: 21 days per year
    • Sick Leave: 7 days per year
    • Maternity/Paternity Leave: As per labor law
    • Emergency Leave: Subject to approval

    **💰 Payroll Policies:**
    • Salary Payment: Last working day of each month
    • Overtime: 1.5x rate for approved overtime hours
    • Bonus: Performance-based annual bonus

    **📞 HR Contact:**
    • HR Department: hr@company.com
    • Phone: +94-11-1234567
    • Office Hours: 9:00 AM - 5:00 PM

    Need specific policy details? Feel free to ask!
    """
            
            elif any(keyword in query_lower for keyword in ['help', 'procedure', 'procedures', 'process']):
                return f"""
    🛠️ **HR Procedures & Help - {user_name}**

    **💰 Payroll Procedures:**
    • Check Your Salary: "Calculate salary for {user_name}" or "Calculate salary for your employee ID"
    • Salary Queries: Contact HR for salary adjustments or tax queries
    • Payslip: Available through employee portal

    **📋 Leave Procedures:**
    1. Submit leave request through employee portal
    2. Get supervisor approval
    3. HR will process and confirm
    4. Update your calendar accordingly

    **🏥 Medical Claims:**
    1. Submit medical bills to HR within 30 days
    2. Fill out reimbursement form
    3. Processing time: 7-10 working days

    **📧 General Procedures:**
    • Email Support: hr@company.com
    • Phone Support: +94-11-1234567
    • IT Support: it@company.com
    • Emergency Contact: +94-77-9876543

    **🔧 Common Tasks:**
    • Password Reset: Contact IT department
    • Equipment Issues: Submit IT ticket
    • Document Requests: Contact HR

    Need help with a specific procedure? Just ask!
    """
            
            elif any(keyword in query_lower for keyword in ['benefit', 'benefits', 'allowance', 'allowances']):
                return f"""
    💎 **Employee Benefits & Allowances - {user_name}**

    **💰 Financial Benefits:**
    • Performance Bonus: Annual performance-based bonus
    • Transport Allowance: Rs. 15,000 per month
    • Meal Allowance: Rs. 10,000 per month
    • Mobile Allowance: Rs. 5,000 per month

    **🏥 Health Benefits:**
    • Medical Insurance: Full family coverage
    • Dental Coverage: Annual checkups covered
    • Eye Care: Annual eye tests + glasses allowance
    • Health Checkups: Annual health screening

    **🎓 Development Benefits:**
    • Training Budget: Rs. 50,000 per year
    • Conference Attendance: Subject to approval
    • Certification Support: Company sponsored
    • Online Courses: Udemy/Coursera access

    **🏖️ Time-Off Benefits:**
    • Flexible Working Hours
    • Work from Home Options
    • Birthday Leave: Extra day off on your birthday
    • Volunteer Leave: 2 days for community service

    **🎉 Additional Perks:**
    • Team Building Events
    • Annual Company Trip
    • Employee Recognition Awards
    • Free Parking

    Want details about any specific benefit? Just ask!
    """
            
            else:
                # Default user capabilities
                user_emp_id = user_name.split()[-1] if user_name else "your employee ID"
                return f"""
    👋 **Hello {user_name}! Welcome to HR Assistant**

    🎯 **What I can help you with:**

    **💰 Your Payroll Information:**
    • "Calculate salary for {user_name}"
    • "Show my payroll details"
    • "Calculate my salary"

    **📋 HR Information & Support:**
    • "Ask about company policies" - Get detailed policy information
    • "Get help with HR procedures" - Step-by-step procedure guides
    • "Tell me about employee benefits" - Complete benefits overview

    **❓ Example Questions:**
    • "What are the leave policies?"
    • "How do I submit a medical claim?"
    • "What benefits do I have?"
    • "What are the working hours?"

    **🚫 Note:** For candidate management and other employees' salary information, please contact HR Admin.

    How can I help you today?
    """
    
    def _format_tool_result(self, tool_result: Dict[str, Any], user_role: str) -> str:
        """Format tool results for display"""
        result_type = tool_result.get("type", "unknown")
        
        if result_type == "candidate_search":
            results = tool_result.get("results", [])
            if not results:
                return "❌ No candidates found matching your search criteria."
            
            response = f"🎯 Found {len(results)} candidates:\n\n"
            for i, candidate in enumerate(results, 1):
                response += f"**{i}. {candidate['candidate_name']}** - {candidate['position']}\n"
                response += f"   📧 Email: {candidate.get('contact_info', {}).get('email', 'N/A')}\n"
                response += f"   💼 Experience: {candidate['experience_years']} years\n"
                
                if candidate.get('skills'):
                    skills_display = ', '.join(candidate['skills'][:5])
                    if len(candidate['skills']) > 5:
                        skills_display += f" (+{len(candidate['skills'])-5} more)"
                    response += f"   🛠️ Skills: {skills_display}\n"
                
                if candidate.get('similarity_score'):
                    response += f"   📊 Match Score: {1/candidate['similarity_score']:.2f}\n"
                
                response += f"   📝 Summary: {candidate.get('summary', 'No summary available')[:100]}...\n\n"
            
            return response
        
        elif result_type == "all_candidates":
            results = tool_result.get("results", [])
            if not results:
                return "❌ No candidates in the database."
            
            response = f"📋 **All Candidates ({len(results)} total):**\n\n"
            for i, candidate in enumerate(results, 1):
                response += f"{i}. **{candidate['candidate_name']}** - {candidate['position']}\n"
                response += f"   💼 Experience: {candidate['experience_years']} years\n"
                if candidate.get('skills'):
                    response += f"   🛠️ Skills: {', '.join(candidate['skills'][:3])}\n"
                response += "\n"
            
            return response
        
        elif result_type == "salary_calculation":
            result = tool_result.get("result", {})
            if "error" in result:
                return f"❌ Error: {result['error']}"
            
            return f"""
💰 **Salary Calculation for {result['name']}**

👤 **Employee Details:**
• Employee ID: {result['employee_id']}
• Department: {result['department']}
• Position: {result['position']}

💵 **Salary Breakdown:**
• Base Salary: Rs. {result['base_salary']:,}
• Bonus: Rs. {result['bonus']:,}
• **Gross Salary: Rs. {result['gross_salary']:,}**

📊 **Deductions:**
• Tax Rate: {result['tax_rate']*100}%
• Tax Amount: Rs. {result['tax_amount']:,.2f}
• Other Deductions: Rs. {result['deductions']:,}

💳 **Net Salary: Rs. {result['net_salary']:,.2f}**

📅 Calculated on: {result.get('calculation_date', 'Unknown')}
"""
        
        elif result_type == "payroll_report":
            result = tool_result.get("result", {})
            if "error" in result:
                return f"❌ Error: {result['error']}"
            
            response = f"""
📊 **Payroll Report - {result['department']}**

📈 **Summary Statistics:**
• Total Employees: {result['total_employees']}
• Total Base Salary: Rs. {result['total_base_salary']:,}
• Total Bonus: Rs. {result['total_bonus']:,}
• Total Gross Salary: Rs. {result['total_gross_salary']:,}
• Total Tax: Rs. {result['total_tax']:,.2f}
• Total Deductions: Rs. {result['total_deductions']:,}
• **Total Net Salary: Rs. {result['total_net_salary']:,.2f}**

👥 **Employee Details:**
"""
            for emp in result['employees']:
                response += f"• {emp['name']} ({emp['employee_id']}): Rs. {emp['net_salary']:,.2f}\n"
            
            response += f"\n📅 Generated on: {result.get('generated_at', 'Unknown')}"
            return response
        
        elif result_type == "all_employees":
            results = tool_result.get("results", [])
            if not results:
                return "❌ No employees found."
            
            response = f"👥 **All Employees ({len(results)} total):**\n\n"
            for emp in results:
                response += f"• **{emp['name']}** ({emp['employee_id']}) - {emp['department']}\n"
                response += f"  📍 Position: {emp['position']}\n"
                response += f"  💰 Salary: Rs. {emp['salary']:,}\n\n"
            
            return response
        
        elif result_type == "error":
            return f"❌ **Error:** {tool_result.get('message', 'Unknown error occurred')}"
        
        else:
            return tool_result.get("message", "✅ Task completed successfully.")
    
    def _extract_search_terms(self, query: str) -> str:
        """Extract search terms from query"""
        stop_words = {"search", "for", "find", "candidates", "candidate", "who", "with", "have", "are"}
        words = query.lower().split()
        search_terms = [word for word in words if word not in stop_words]
        return " ".join(search_terms)
    
    def _extract_employee_id(self, query: str) -> str:
        """Extract employee ID from query"""
        import re
        # Look for patterns like EMP001, EMP014, ADM001
        match = re.search(r'(EMP\d{3}|ADM\d{3})', query.upper())
        extracted_id = match.group() if match else None
        print(f"🔍 Extracted employee ID from '{query}': {extracted_id}")
        return extracted_id
    
    def _extract_department(self, query: str) -> str:
        """Extract department name from query"""
        departments = ["IT", "HR", "Finance", "Marketing"]
        query_lower = query.lower()
        for dept in departments:
            if dept.lower() in query_lower:
                return dept
        return None
    
    def process_query(self, user_query: str, user_context: Dict[str, Any]) -> str:
        """Main method to process user queries with role-based access"""
        try:
            print(f"\n🚀 Processing query: '{user_query}' for user: {user_context.get('name')}")
            
            # Create initial state as a dictionary
            initial_state: AgentState = {
                "messages": [],
                "user_query": user_query,
                "user_context": user_context,
                "intent": "",
                "tool_result": {},
                "final_response": "",
                "permission_granted": False,
                "denied_reason": ""
            }
            
            # Run the graph
            final_state = self.graph.invoke(initial_state)
            
            print(f"✅ Query processed successfully")
            return final_state["final_response"]
            
        except Exception as e:
            print(f"❌ Error processing query: {e}")
            import traceback
            traceback.print_exc()
            return f"❌ Error processing query: {str(e)}"