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

class ContractsInput(BaseModel):
    employee_email: str = Field(description="The flex worker's email address. Used to find their CandidateId.")

@tool(args_schema=ContractsInput)
def get_contracts_tool(employee_email: str) -> Dict[str, Any]:
    """
    Retrieves a list of all contracts (past and present) for a flex worker
    from the Kentro (Pivoton) API.
    """
    
    client = KentroClient()
    
    try:
        # Step 1: Get the CandidateId using the email
        candidate_id = client.get_candidate_id_from_email(employee_email)
        if not candidate_id:
            return {"error": f"No candidate found with email {employee_email}."}
            
        # Step 2: Fetch the contracts
        logger.info(f"GetContractsTool: Fetching contracts for Candidate {candidate_id}")
        contracts_list = client.get_contracts(candidate_id)
        
        return {"contracts": contracts_list}

    except Exception as e:
        logger.error(f"GetContractsTool: An error occurred: {e}")
        # This structured error will be handled by the ChatSupervisor
        return {"error": f"An unexpected error occurred while retrieving contracts: {str(e)}"}