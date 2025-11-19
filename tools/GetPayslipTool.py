import sys
import os
import logging
from typing import Optional, Dict, Any, List, Union
from pydantic import BaseModel, Field
from langchain_core.tools import tool

# Add project root to path
parent_dir = os.path.dirname(os.getcwd())
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Import client and Pydantic models
from clients.kentro import KentroClient, Payslip, PayslipFile

# Set up logging
logger = logging.getLogger(__name__)

class PayslipToolInput(BaseModel):
    candidate_id: str = Field(description="The flex worker's candidate ID.")
    latest: bool = Field(default=False, description="Set to True to retrieve only the single most recent payslip metadata.")
    payslip_id: Optional[int] = Field(default=None, description="Get a specific payslip file by ID.")
    
@tool(args_schema=PayslipToolInput)
def get_payslip(candidate_id: str, latest: bool = False, payslip_id: Optional[int] = None) -> Any:
    """
    Retrieves payslip information for a flex worker.
    Returns Pydantic models (Payslip or PayslipFile) or lists of them.
    """
    client = KentroClient()
    
    try:
        # Ensure candidate_id is int as required by client methods
        cand_id = int(candidate_id)

        # Case 1: Specific File (Requesting a specific ID usually implies wanting the file content)
        if payslip_id:
            file_obj: Optional[PayslipFile] = client.get_payslip_file(cand_id, payslip_id)
            if not file_obj:
                return {"error": f"Payslip file with ID {payslip_id} not found."}
            return file_obj

        # Fetch list of payslips (List[Payslip])
        payslips: List[Payslip] = client.get_payslips(cand_id)

        # Case 2: Latest Payslip (Metadata Only)
        if latest:
            if not payslips:
                return {"error": "No payslips were found."}
            
            # Sort by entry_date descending to find the newest
            payslips.sort(key=lambda x: x.entry_date, reverse=True)
            latest_slip = payslips[0]
            
            # Return the Pydantic metadata object directly
            # (Skipping get_payslip_file call as requested)
            return latest_slip
            
        # Case 3: Full List of Payslips
        return payslips

    except ValueError:
        return {"error": f"Invalid Candidate ID format: {candidate_id}"}
    except Exception as e:
        logger.error(f"Error in get_payslip: {e}")
        return {"error": str(e)}