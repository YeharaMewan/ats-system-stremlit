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
    
    def _check_permissions(self, state: AgentState) -> AgentState:
        """Check user permissions"""
        user_role = state["user_context"].get('role', 'user')
        query = state["user_query"].lower()
        
        print(f"🔐 Checking permissions for {user_role}: '{query}'")
        
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
            
            # Check if trying to access other users' payroll
            payroll_keywords = ['salary', 'payroll', 'calculate', 'employee']
            if any(keyword in query for keyword in payroll_keywords):
                user_employee_id = state["user_context"].get('employee_id')
                if user_employee_id not in query:
                    state["permission_granted"] = False
                    state["denied_reason"] = "You can only access your own payroll information."
                    print(f"❌ Payroll access denied - user can only access {user_employee_id}")
                    return state
        
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
        """Handle payroll related tasks"""
        try:
            query = state["user_query"].lower()
            user_role = state["user_context"].get('role', 'user')
            
            print(f"💰 Handling payroll request: '{query}' for role: {user_role}")
            
            if "calculate salary" in query or "salary for" in query:
                emp_id = self._extract_employee_id(state["user_query"])
                print(f"💰 Extracting employee ID: {emp_id}")
                
                # For non-admin users, only allow access to their own salary
                if user_role != 'admin':
                    user_emp_id = state["user_context"].get('employee_id')
                    if emp_id != user_emp_id:
                        emp_id = user_emp_id  # Force to their own employee ID
                        print(f"🔒 Non-admin user restricted to own ID: {emp_id}")
                
                if emp_id:
                    print(f"💰 Calculating salary for: {emp_id}")
                    result = self.payroll_tools.calculate_salary(emp_id)
                    state["tool_result"] = {"type": "salary_calculation", "result": result}
                else:
                    state["tool_result"] = {"type": "error", "message": "Please specify employee ID"}
            
            elif "payroll report" in query or "report" in query:
                if user_role == 'admin':
                    department = self._extract_department(state["user_query"])
                    print(f"📊 Generating payroll report for: {department or 'all departments'}")
                    result = self.payroll_tools.generate_payroll_report(department)
                    state["tool_result"] = {"type": "payroll_report", "result": result}
                else:
                    state["tool_result"] = {"type": "error", "message": "Payroll reports are available to HR Admin only"}
            
            elif "all employees" in query or "list employees" in query:
                if user_role == 'admin':
                    print("👥 Getting all employees")
                    results = self.payroll_tools.get_all_employees()
                    state["tool_result"] = {"type": "all_employees", "results": results}
                else:
                    state["tool_result"] = {"type": "error", "message": "Employee list is available to HR Admin only"}
            
            else:
                user_emp_id = state["user_context"].get('employee_id', 'your employee ID')
                state["tool_result"] = {
                    "type": "payroll_help",
                    "message": f"I can help you check your salary. Try: 'Calculate salary for {user_emp_id}'"
                }
                
        except Exception as e:
            print(f"❌ Payroll error: {e}")
            state["tool_result"] = {"type": "error", "message": f"Payroll error: {str(e)}"}
        
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
        """Generate general responses based on user role"""
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
        else:
            capabilities = f"""
🎯 As a regular user, you can access:

**💰 Your Own Payroll Information:**
• "Calculate salary for {user_name.split()[0] if user_name else 'your employee ID'}"
• "Show my payroll details"

**📋 General HR Inquiries:**
• Ask about company policies
• Get help with HR procedures

Note: For candidate management and other employees' information, please contact HR Admin.
"""
        
        return f"👋 Hello {user_name}!\n\n{capabilities}\n\nHow can I help you today?"
    
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