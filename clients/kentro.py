import requests
import os
import logging
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from langchain_core.tools import tool

# Set up logging
logger = logging.getLogger(__name__)

# 1. DATA MODELS

class Candidate(BaseModel):
    candidate_id: int = Field(alias="CandidateId")
    first_name: str = Field(alias="FirstName")
    surname: str = Field(alias="Surname")
    email: str = Field(alias="EmailAddress")
    # Add other fields as needed, filtering out unused ones via extra="ignore"
    
    class Config:
        extra = "ignore"

class Payslip(BaseModel):
    id: int = Field(alias="PaySlipId")
    business_unit_id: int = Field(alias="BusinessUnitId")
    serial_number: str = Field(alias="SerialNumber")
    frequency: Optional[str] = Field(None, alias="WagePaymentFrequency")
    entry_date: str = Field(alias="EntryDate")
    amount: Optional[float] = Field(None, alias="PaidAmount")

    class Config:
        extra = "ignore"

class PayslipFile(BaseModel):
    name: str = Field(alias="Name")
    file_name: str = Field(alias="FileName")
    size: int = Field(alias="Size")
    binary_data: str = Field(alias="BinaryFile") # Base64 string

    class Config:
        extra = "ignore"

class Contract(BaseModel):
    id: int = Field(alias="ContractId")
    code: Optional[str] = Field(None, alias="ContractCode")
    status: Optional[str] = Field(None, alias="CurrentStatus")
    start_date: str = Field(alias="StartDate")
    end_date: Optional[str] = Field(None, alias="EndDate")
    function_description: Optional[str] = Field(None, alias="FunctionDescription")
    hourly_wage: Optional[float] = Field(None, alias="Wage")
    wage_unit: Optional[str] = Field(None, alias="WageTimeUnit")
    # Helper for display
    employment_desc: Optional[str] = Field(None, alias="EmploymentDescription")

    class Config:
        extra = "ignore"

class ReservationBalance(BaseModel):
    # Identifiers
    candidate_id: Optional[int] = Field(None, alias="CandidateId")
    business_unit_tax_category_id: Optional[int] = Field(None, alias="BusinessUnitTaxcategoryId")
    type_id: int = Field(alias="ReservationTypeId")
    
    # Descriptions & Codes
    description: str = Field(alias="ReservationTypeDescription")
    setu_code: Optional[str] = Field(None, alias="SetuCode")
    
    # Settings
    display_in_portal: Optional[bool] = Field(None, alias="DisplayInPortal")
    year: int = Field(alias="Year")
    
    # Balances - UPDATED: Made Optional to handle 'null' values from API
    accrued_amount: Optional[float] = Field(None, alias="AccruedAmount")
    accrued_unit: Optional[str] = Field(None, alias="AccruedUnit")
    available_balance: Optional[float] = Field(None, alias="AvailableBalance")
    
    # Withdrawal Info
    withdrawal_unit: Optional[str] = Field(None, alias="BalanceWithdrawalUnit")
    max_withdrawal_limit: Optional[float] = Field(None, alias="MaximumWithdrawalLimit")
    allow_withdraw_all: Optional[bool] = Field(None, alias="AllowWithdrawAll")

    class Config:
        extra = "ignore"

# ==============================================================================

# 2. CLIENT

class KentroClient:
    """
    API Client for the Kentro (Pivoton) Public API.
    Returns Pydantic models instead of raw dictionaries.
    """
    
    def __init__(self):
        self.base_url = os.environ.get("KENTRO_BASE_URL")
        self.username = os.environ.get("KENTRO_USERNAME")
        self.password = os.environ.get("KENTRO_PASSWORD")
        
        if not all([self.base_url, self.username, self.password]):
            logger.error("KENTRO credentials not fully configured.")
            raise ValueError("Kentro API credentials are missing.")
            
        self.auth = (self.username, self.password)

    def _make_request(self, method: str, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
        url = f"{self.base_url}{endpoint}"
        headers = {"Accept": "application/json"}
        
        try:
            response = requests.request(method, url, headers=headers, auth=self.auth, params=params)
            response.raise_for_status()
            if response.status_code == 204: # No Content
                return None
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling Kentro API {endpoint}: {e}")
            raise

    def get_candidate_from_email(self, email: str) -> Optional[Candidate]:
        """Retrieves the Candidate object using email address."""
        params = {"EmailAddress": email}
        try:
            data = self._make_request("GET", "/candidates", params=params)
            if data and isinstance(data, list) and len(data) > 0:
                # Validate and return the first match
                return Candidate(**data[0])
            else:
                logger.warning(f"No candidate found for email {email}")
                return None
        except Exception as e:
            logger.error(f"Failed to retrieve Candidate: {e}")
            return None

    def get_candidate_id_from_email(self, email: str) -> Optional[int]:
        """Helper to get just the ID."""
        candidate = self.get_candidate_from_email(email)
        return candidate.candidate_id if candidate else None

    def get_payslips(self, candidate_id: int, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Payslip]:
        """Gets a list of Payslip models."""
        endpoint = f"/candidates/{candidate_id}/pay_slips"
        params = {}
        if start_date:
            params["createdFrom"] = start_date
        if end_date:
            params["createdTo"] = end_date
            
        try:
            raw_list = self._make_request("GET", endpoint, params=params) or []
            return [Payslip(**item) for item in raw_list]
        except Exception as e:
            logger.error(f"Error parsing payslips: {e}")
            return []

    def get_payslip_file(self, candidate_id: int, payslip_id: int) -> Optional[PayslipFile]:
        """Retrieves the PayslipFile model."""
        endpoint = f"/candidates/{candidate_id}/pay_slips/{payslip_id}/file"
        try:
            data = self._make_request("GET", endpoint)
            if data:
                return PayslipFile(**data)
            return None
        except Exception as e:
            logger.error(f"Error parsing payslip file: {e}")
            return None

    def get_contracts(self, candidate_id: int) -> List[Contract]:
        """Gets a list of Contract models."""
        endpoint = f"/candidates/{candidate_id}/contracts"
        try:
            raw_list = self._make_request("GET", endpoint) or []
            return [Contract(**item) for item in raw_list]
        except Exception as e:
            logger.error(f"Error parsing contracts: {e}")
            return []

    def get_reservation_balances(self, candidate_id: int) -> List[ReservationBalance]:
        """Gets a list of ReservationBalance models."""
        endpoint = f"/candidates/{candidate_id}/reservation-balances"
        try:
            raw_list = self._make_request("GET", endpoint) or []
            return [ReservationBalance(**item) for item in raw_list]
        except Exception as e:
            logger.error(f"Error parsing reservation balances: {e}")
            return []
