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

from archive.kentro import KentroClient

# --- Input Schemas ---

class KentroInput(BaseModel):
    """Shared input schema for Kentro tools that only need an email."""
    employee_email: str = Field(description="The flex worker's email address. Used to find their CandidateId.")
    
# --- GetReservationsTool ---
@tool(args_schema=KentroInput)
def get_reservations_tool(employee_email: str) -> Dict[str, Any]:
    """
    Retrieves a list of all reservation balances (vacation, etc.)
    for a flex worker from the Kentro (Pivoton) API.
    """
    client = KentroClient()
    try:
        cand_id = client.get_candidate_id_from_email(employee_email)
        if not cand_id:
            return {"error": f"Candidate not found: {employee_email}"}
            
        balances = client.get_reservation_balances(cand_id)
        return {"reservations": [b.dict() for b in balances]}
    except Exception as e:
        return {"error": str(e)}