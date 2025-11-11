import requests
import os
import sys
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from langchain_core.tools import tool

# Add the parent directory to Python path to import clients module
parent_dir = os.path.dirname(os.getcwd())
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from clients.kentro import KentroClient

# Set up logging
logger = logging.getLogger(__name__)

# --- Input Schemas ---

class KentroInput(BaseModel):
    """Shared input schema for Kentro tools that only need an email."""
    employee_email: str = Field(description="The flex worker's email address. Used to find their CandidateId.")


# --- Tool: GetReservationsTool ---
@tool(args_schema=KentroInput)
def get_reservations_tool(employee_email: str) -> Dict[str, Any]:
    """
    Retrieves a list of all reservation balances (vacation, etc.)
    for a flex worker from the Kentro (Pivoton) API.
    """
    client = KentroClient()
    
    try:
        # Step 1: Get the CandidateId using the email
        candidate_id = client.get_candidate_id_from_email(employee_email)
        if not candidate_id:
            return {"error": f"No candidate found with email {employee_email}."}
            
        # Step 2: Fetch the reservation balances
        logger.info(f"GetReservationsTool: Fetching reservation balances for Candidate {candidate_id}")
        balances = client.get_reservation_balances(candidate_id)
        
        return {"reservation_balances": balances}

    except Exception as e:
            logger.error(f"GetReservationsTool: An error occurred: {e}")
            return {"error": f"An unexpected error occurred while retrieving reservations: {str(e)}"}