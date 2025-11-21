from typing import TypedDict, Annotated
from langchain_core.messages import AnyMessage

# Agent State
class AgentState(TypedDict):
   date: Annotated[str, "Current date context for queries"]
   messages: Annotated[list[AnyMessage], "Conversation messages"]
   candidate_id: Annotated[str, "Candidate ID for Kentro"]
   employee_number: Annotated[str, "Employee Number for Planbition"]
   next_action: Annotated[str, "Next action to take"]
   retrieved_data: Annotated[str, "Data retrieved from tools"]
   error_message: Annotated[str, "Error message if any"]
   attempts: Annotated[int, "Number of attempts made"]
   max_retries: Annotated[int, "Maximum number of retries allowed"]