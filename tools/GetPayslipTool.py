import requests
import os
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from langchain_core.tools import tool

# Set up logging
logger = logging.getLogger(__name__)

class PayslipInput(BaseModel):
    employee_email: str = Field(description="The flex worker's email address. Used to find their CandidateId.")
    latest: Optional[bool] = Field(default=False, description="Set to True to retrieve only the single most recent payslip file.")
    payslip_id: Optional[int] = Field(default=None, description="A specific PaySlipId to retrieve. If provided, 'latest' is ignored.")
    start_date: Optional[str] = Field(default=None, description="The start date (YYYY-MM-DD) for a date range query.")
    end_date: Optional[str] = Field(default=None, description="The end date (YYYY-MM-DD) for a date range query.")

@tool(args_schema=PayslipInput)
def get_payslip_tool(
    employee_email: str, 
    latest: Optional[bool] = False, 
    payslip_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Retrieves payslip information for a flex worker from the Kentro (Pivoton) API.
    
    - If 'payslip_id' is provided, it fetches that specific payslip file.
    - If 'latest' is True, it fetches the single most recent payslip file.
    - Otherwise, it returns a list of payslips, optionally filtered by date.
    """
    
    client = KentroClient()
    
    try:
        # Step 1: Get the CandidateId using the email
        candidate_id = client.get_candidate_id_from_email(employee_email)
        if not candidate_id:
            return {"error": f"No candidate found with email {employee_email}."}
            
        # Case 1: A specific payslip_id is requested
        if payslip_id:
            logger.info(f"GetPayslipTool: Fetching specific payslip {payslip_id}")
            file_data = client.get_payslip_file(candidate_id, payslip_id)
            # Return as a list for consistent data structure
            return {"payslips": [file_data]}

        # Case 2: The "latest" payslip is requested
        if latest:
            logger.info("GetPayslipTool: Fetching latest payslip")
            payslip_list = client.get_payslips(candidate_id)
            if not payslip_list:
                return {"payslips": [], "message": "No payslips were found."}
                
            # Sort to find the latest payslip (by EntryDate)
            payslip_list.sort(key=lambda x: x.get("EntryDate", ""), reverse=True)
            latest_payslip = payslip_list[0]
            latest_payslip_id = latest_payslip.get("PaySlipId")
            
            file_data = client.get_payslip_file(candidate_id, latest_payslip_id)
            # Return as a list for consistent data structure
            return {"payslips": [file_data]}

        # Case 3: A list of payslips is requested (with optional date filter)
        logger.info(f"GetPayslipTool: Fetching payslip list for dates {start_date} to {end_date}")
        payslip_list = client.get_payslips(candidate_id, start_date, end_date)
        
        return {"payslips": payslip_list}

    except Exception as e:
        logger.error(f"GetPayslipTool: An error occurred: {e}")
        # This structured error will be handled by the ChatSupervisor
        return {"error": f"An unexpected error occurred while retrieving payslips: {str(e)}"}