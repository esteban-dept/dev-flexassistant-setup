import sys
parent_dir = os.path.dirname(os.getcwd())
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

import requests
import os
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from clients.kentro import KentroClient

class PayslipToolInput(BaseModel):
    employee_email: str = Field(description="The flex worker's email address.")
    latest: bool = Field(default=False, description="Get only the most recent payslip.")
    payslip_id: Optional[int] = Field(default=None, description="Get a specific payslip by ID.")

class KentroInput(BaseModel):
    employee_email: str = Field(description="The flex worker's email address.")

# --- GetPayslipTool ---
@tool(args_schema=PayslipToolInput)
def get_payslip_tool(employee_email: str, latest: bool = False, payslip_id: Optional[int] = None) -> Dict[str, Any]:
    """Retrieves payslip information (list or specific file) for a flex worker."""
    client = KentroClient()
    try:
        cand_id = client.get_candidate_id_from_email(employee_email)
        if not cand_id:
            return {"error": f"Candidate not found: {employee_email}"}

        # Case 1: Specific File
        if payslip_id:
            file_obj = client.get_payslip_file(cand_id, payslip_id)
            return {"file": file_obj.dict(by_alias=False)} if file_obj else {"error": "File not found"}

        # Case 2: List (or Latest)
        payslips = client.get_payslips(cand_id)
        
        if latest and payslips:
            # Sort by entry_date desc
            payslips.sort(key=lambda x: x.entry_date, reverse=True)
            latest_slip = payslips[0]
            # Fetch the actual file for the latest slip
            file_obj = client.get_payslip_file(cand_id, latest_slip.id)
            return {
                "latest_payslip_metadata": latest_slip.dict(),
                "file": file_obj.dict() if file_obj else None
            }
            
        return {"payslips": [p.dict() for p in payslips]}

    except Exception as e:
        return {"error": str(e)}