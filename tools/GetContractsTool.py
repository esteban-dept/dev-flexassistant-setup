import sys
import os
import logging
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from langchain_core.tools import tool

# Add project root to path
parent_dir = os.path.dirname(os.getcwd())
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from clients.kentro import KentroClient

# Set up logging
logger = logging.getLogger(__name__)

# --- Input Schema ---
class ContractsToolInput(BaseModel):
    candidate_id: str = Field(description="The flex worker's candidate ID.")
    
# --- GetContractsTool ---
@tool(args_schema=ContractsToolInput)
def get_contracts(candidate_id: str) -> Any:
    """
    Retrieves a list of all contracts (past and present) for a flex worker 
    from the Kentro (Pivoton) API.
    Returns a list of Contract Pydantic models.
    """
    client = KentroClient()
    try:
        # Ensure candidate_id is int as required by client methods
        cand_id = int(candidate_id)
            
        # Fetch contracts
        # This returns a List[Contract] (Pydantic models)
        contracts = client.get_contracts(cand_id)
        
        return contracts

    except ValueError:
        return {"error": f"Invalid Candidate ID format: {candidate_id}"}
    except Exception as e:
        logger.error(f"Error in get_contracts: {e}")
        return {"error": str(e)}