import os
import sys

parent_dir = os.path.dirname(os.getcwd())
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from langchain_core.tools import tool
from pydantic import BaseModel, Field
from typing import List, Dict, Any
from clients.planbition import PlanbitionClient# Import the client from Step 1


# Initialize the client once
client = PlanbitionClient()

class ScheduleInput(BaseModel):
    employee_number: str = Field(description="The unique employee number for the flex worker.")
    start_date: str = Field(description="The start date of the period to query, in YYYY-MM-DD format.")
    end_date: str = Field(description="The end date of the period to query, in YYYY-MM-DD format.")

@tool(args_schema=ScheduleInput)
def get_schedule(employee_number: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """
    Retrieves the work schedule for a flex worker from the Planbition API
    for a specified date range. This tool is called by the ActionExecutionAgent
    when a user asks about their schedule.
    """
    try:
        # The client handles all auth and filtering
        schedule_data = client.get_schedule(
            employee_number=employee_number,
            start_date=start_date,
            end_date=end_date
        )
        # The tool returns the raw structured data
        # The AnswerAgent will be responsible for formatting this
        # into a user-friendly response
        return schedule_data
    except Exception as e:
        # The agent's error handling will catch this
        return f"Error retrieving schedule: {e}"