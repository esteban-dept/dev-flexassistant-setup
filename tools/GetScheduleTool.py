import os
import sys
import time
from requests.exceptions import HTTPError

parent_dir = os.path.dirname(os.getcwd())
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from langchain_core.tools import tool
from pydantic import BaseModel, Field
from typing import List, Dict, Any
# Import both the client AND the data model
from clients.planbition import PlanbitionClient, ScheduleItem

# Initialize the client once
client = PlanbitionClient()

class ScheduleInput(BaseModel):
    employee_number: str = Field(description="The unique employee number for the flex worker.")
    start_date: str = Field(description="The start date of the period to query, in YYYY-MM-DD format.")
    end_date: str = Field(description="The end date of the period to query, in YYYY-MM-DD format.")

@tool(args_schema=ScheduleInput)
def get_schedule(employee_number: str, start_date: str, end_date: str) -> Dict[str, Any]:
    """
    Retrieves the work schedule for a flex worker from the Planbition API
    for a specified date range. This tool is called by the ActionExecutionAgent
    when a user asks about their schedule.
    """
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # The client now returns a list of Pydantic ScheduleItem objects
            schedule_items = client.get_employee_schedule(
                employee_number=employee_number,
                start_date=start_date,
                end_date=end_date
            )
            
            # Serialize the Pydantic models back into dictionaries
            # so they can be returned as JSON to the agent.
            #schedule_list = [item.dict() for item in schedule_items]
            
            # Return a structured dictionary for the agent
            return schedule_items
            
        except HTTPError as e:
            if e.response.status_code == 500 and attempt < max_retries - 1:
                print(f"500 Server Error on attempt {attempt + 1}. Retrying in 2 seconds...")
                time.sleep(2)
                continue
            else:
                raise e
        except Exception as e:
            if "500" in str(e) and attempt < max_retries - 1:
                print(f"Server error detected: {e}. Retrying in 2 seconds...")
                time.sleep(2)
                continue
            else:
                raise e
    
    return "Failed to retrieve schedule after multiple attempts"