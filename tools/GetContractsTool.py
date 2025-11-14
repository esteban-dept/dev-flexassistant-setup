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

class KentroInput(BaseModel):
    employee_email: str = Field(description="The flex worker's email address.")
    
    # --- GetContractsTool ---
@tool(args_schema=KentroInput)
def get_contracts_tool(employee_email: str) -> Dict[str, Any]:
    """
    Retrieves a list of all contracts (past and present) for a flex worker
    from the Kentro (Pivoton) API.
    """
    client = KentroClient()
    try:
        cand_id = client.get_candidate_id_from_email(employee_email)
        if not cand_id:
            return {"error": f"Candidate not found: {employee_email}"}
            
        contracts = client.get_contracts(cand_id)
        return {"contracts": [c.dict() for c in contracts]}
    except Exception as e:
        return {"error": str(e)}