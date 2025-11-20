from typing import TypedDict, Annotated
from langchain_core.messages import AnyMessage

# Agent State
class AgentState(TypedDict):
   messages: Annotated[list[AnyMessage], "Conversation messages"]
   next_action: Annotated[str, "Next action to take"]
   retrieved_data: Annotated[str, "Data retrieved from tools"]
   error_message: Annotated[str, "Error message if any"]
   attempts: Annotated[int, "Number of attempts made"]
   max_retries: Annotated[int, "Maximum number of retries allowed"]