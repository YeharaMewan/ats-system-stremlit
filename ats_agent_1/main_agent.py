import os
from dotenv import load_dotenv
from typing import TypedDict, Annotated, Sequence
import operator
from langchain_core.messages import BaseMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.tools import Tool

# --- Import Caching functionalities ---
from langchain.globals import set_llm_cache
from langchain.cache import SQLiteCache

# --- Import the standalone tool functions and schemas ---
from hr_agent_tools import find_matching_candidates, calculate_payroll, schedule_interview, PayrollInput

# --- Environment and Cache Setup ---
load_dotenv()
if "GOOGLE_API_KEY" not in os.environ:
    raise ValueError("FATAL ERROR: GOOGLE_API_KEY not found in .env file or environment variables")

print("--- Setting up LLM Cache... ---")
set_llm_cache(SQLiteCache(database_path=".langchain.db"))

# --- Agent State Definition ---
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]

# --- DYNAMIC AGENT AND TOOL CREATION ---
def get_agent_executor(user_role: str, user_employee_id: str):
    print(f"\n--- Creating agent for role: {user_role} ---")
    
    tools = []
    
    if user_role == 'hr_admin':
        # HR Admin gets all imported tool functions
        tools = [find_matching_candidates, calculate_payroll, schedule_interview]
        print(f"--- HR Admin Tools Loaded: {[tool.name for tool in tools]} ---")

    elif user_role == 'worker':
        # Worker gets a special, sandboxed version of the payroll tool
        def worker_payroll_checker(employee_id: str, overtime_hours: int = 0, bonus: float = 0.0):
            if employee_id != user_employee_id:
                return f"Permission Denied. As a worker, you can only calculate your own payroll (Employee ID: {user_employee_id})."
            # Call the original imported function
            return calculate_payroll.func(employee_id=employee_id, overtime_hours=overtime_hours, bonus=bonus)

        sandboxed_payroll_tool = Tool(
            name="calculate_payroll",
            func=worker_payroll_checker,
            description="Calculates your personal net payroll. You must provide your employee ID for verification.",
            args_schema=PayrollInput
        )
        tools = [sandboxed_payroll_tool]
        print(f"--- Worker Tools Loaded: {[tool.name for tool in tools]} ---")

    api_key = os.getenv("GOOGLE_API_KEY")
        
    model = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash-latest",
        temperature=0,
        google_api_key=api_key
    )
    model = model.bind_tools(tools)
    
    tool_node = ToolNode(tools)

    def agent_node(state: AgentState):
        response = model.invoke(state["messages"])
        return {"messages": [response]}

    def should_continue(state: AgentState) -> str:
        if not state["messages"][-1].tool_calls:
            return "end"
        return "continue"

    workflow = StateGraph(AgentState)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tool_node)
    workflow.set_entry_point("agent")
    workflow.add_conditional_edges("agent", should_continue, {"continue": "tools", "end": END})
    workflow.add_edge("tools", "agent")

    return workflow.compile()

def run_agent(user_input: str, user_role: str, user_employee_id: str):
    agent_executor = get_agent_executor(user_role=user_role, user_employee_id=user_employee_id)
    
    from langchain_core.messages import HumanMessage
    inputs = {"messages": [HumanMessage(content=user_input)]}
    
    final_response_content = "An error occurred, or the agent could not produce a final answer."
    for output in agent_executor.stream(inputs, {"recursion_limit": 15}):
        if "agent" in output and output["agent"].get('messages'):
            last_message = output['agent']['messages'][-1]
            if not last_message.tool_calls:
                final_response_content = last_message.content

    return final_response_content