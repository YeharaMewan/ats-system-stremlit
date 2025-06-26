import json
import datetime
import os
from langchain.tools import tool
from pydantic import BaseModel, Field
from typing import Optional

# Imports required for the Vector DB tool
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma

# --- Module-Level Initialization ---
# These objects will be created only ONCE when this module is first imported.
# This solves the stability and efficiency problem.
print("--- [hr_agent_tools.py] Initializing Embeddings and Vector Store... ---")
try:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("FATAL ERROR: GOOGLE_API_KEY not found in environment variables.")

    embedding_function = GoogleGenerativeAIEmbeddings(
        model="models/embedding-001",
        google_api_key=api_key
    )
    
    vector_store = Chroma(
        persist_directory="chroma_db_store",
        embedding_function=embedding_function
    )
    print("--- Vector Store loaded successfully. ---")
except Exception as e:
    print(f"FATAL ERROR during initial load in hr_agent_tools.py: {e}")
    vector_store = None # Set to None if initialization fails

# --- Tool Input Schemas ---
class ATSInput(BaseModel):
    search_query: str = Field(description="A search query, keywords, or a full job description to find matching candidates.")

class PayrollInput(BaseModel):
    employee_id: str = Field(description="The unique identifier for the employee (e.g., 'E-123').")
    overtime_hours: Optional[int] = Field(0, description="Number of overtime hours worked. Defaults to 0.")
    bonus: Optional[float] = Field(0.0, description="Any performance bonus to be added. Defaults to 0.0.")

class ScheduleInput(BaseModel):
    candidate_id: str = Field(description="The unique ID of the candidate, e.g., 'cv_kamal_perera'.")
    interview_date_time: str = Field(description="The date and time for the interview in format YYYY-MM-DDTHH:MM:SS.")

# --- Tool Functions ---

@tool("find_matching_candidates", args_schema=ATSInput)
def find_matching_candidates(search_query: str) -> str:
    """
    Use this tool to find and rank candidates from the CV database based on skills, experience, or job roles.
    For example: 'Find me a Java developer' or 'Who has experience with AWS and Docker?'.
    """
    print(f"\n--- Executing Tool: find_matching_candidates with query: '{search_query}' ---")
    
    if not vector_store:
        return "Error: The candidate database (Vector Store) is not available due to an initialization error."

    RELEVANCE_THRESHOLD_PERCENT = 30.0
    try:
        results_with_scores = vector_store.similarity_search_with_score(search_query, k=5)
        
        filtered_results = []
        for doc, score in results_with_scores:
            match_percentage = (1 - score) * 100
            if match_percentage >= RELEVANCE_THRESHOLD_PERCENT:
                filtered_results.append((doc, match_percentage))

        if not filtered_results:
            return "No sufficiently matching candidates were found in the database for your query."

        output = "Based on the CV database, here are the most relevant candidates found:\n\n"
        filtered_results.sort(key=lambda x: x[1], reverse=True)
        for i, (doc, match_perc) in enumerate(filtered_results):
            output += f"#{i+1}: Candidate ID: {doc.metadata.get('candidate_id', 'N/A')}\n"
            output += f"   Match Score: {match_perc:.2f}%\n"
            output += f"   CV Snippet: {doc.page_content[:200].strip()}...\n\n"
        return output
    except Exception as e:
        print(f"ERROR during similarity search: {e}")
        return f"An error occurred while searching for candidates: {e}"

@tool("calculate_payroll", args_schema=PayrollInput)
def calculate_payroll(employee_id: str, overtime_hours: int = 0, bonus: float = 0.0) -> str:
    """
    Calculates the net payroll for a specific employee using their unique ID. 
    It fetches the base salary from the hr_data.json file.
    """
    print(f"\n--- Executing Tool: calculate_payroll for Employee ID: {employee_id} ---")
    try:
        with open('hr_data.json', 'r') as f:
            all_employees = json.load(f)
    except FileNotFoundError:
        return "Error: hr_data.json file not found."
    employee_data = next((emp for emp in all_employees if emp.get('employee_id') == employee_id), None)
    if not employee_data:
        return f"Error: Employee with ID '{employee_id}' not found in hr_data.json."
    base_salary = employee_data.get('base_salary', 0.0)
    overtime_pay = overtime_hours * 50.0
    gross_pay = base_salary + overtime_pay + bonus
    net_pay = gross_pay - (gross_pay * 0.20) - 300.0
    return f"Payroll calculated for {employee_data.get('name')}: Net Pay is ${net_pay:,.2f}"

@tool("schedule_interview", args_schema=ScheduleInput)
def schedule_interview(candidate_id: str, interview_date_time: str) -> str:
    """
    Schedules an interview for a given candidate at a specified date and time.
    """
    print(f"\n--- Executing Tool: schedule_interview for {candidate_id} ---")
    try:
        datetime.datetime.fromisoformat(interview_date_time)
        return f"Interview successfully scheduled for candidate '{candidate_id}' on {interview_date_time}."
    except ValueError:
        return "Error: Invalid date/time format. Please use YYYY-MM-DDTHH:MM:SS format."