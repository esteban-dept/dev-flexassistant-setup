# For paylisp, and reservations

import requests
import os
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

# Set up logging
logger = logging.getLogger(__name__)

class KentroClient:
    """
    API Client for the Kentro (Pivoton) Public API.
    
    This client uses HTTP Basic Authentication to retrieve candidate-specific
    data for payslips, reservations, and contracts.
    """
    
    def __init__(self):
        """Initializes the client by loading credentials from environment variables."""
        self.base_url = os.environ.get("KENTRO_BASE_URL")
        self.username = os.environ.get("KENTRO_USERNAME")
        self.password = os.environ.get("KENTRO_PASSWORD")
        
        if not all([self.base_url, self.username, self.password]):
            logger.error("KENTRO_BASE_URL, KENTRO_USERNAME, or KENTRO_PASSWORD not set.")
            raise ValueError("Kentro API credentials are not fully configured.")
            
        self.auth = (self.username, self.password)

    def _make_request(self, method: str, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Helper function to make authenticated requests."""
        url = f"{self.base_url}{endpoint}"
        headers = {"Accept": "application/json"}
        
        try:
            response = requests.request(method, url, headers=headers, auth=self.auth, params=params)
            response.raise_for_status()  # Raises HTTPError for 4xx/5xx responses
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling Kentro API endpoint {endpoint}: {e}")
            raise

    def get_candidate_id_from_email(self, email: str) -> Optional[int]:
        """Retrieves the internal CandidateId using the candidate's email address."""
        params = {"EmailAddress": email}
        try:
            logger.info(f"KentroClient: Fetching CandidateId for email {email}")
            candidates = self._make_request("GET", "/candidates", params=params)
            if candidates and len(candidates) > 0:
                candidate_id = candidates[0].get("CandidateId")
                logger.info(f"KentroClient: Found CandidateId {candidate_id}")
                return candidate_id
            else:
                logger.warning(f"KentroClient: No candidate found for email {email}")
                return None
        except Exception as e:
            logger.error(f"KentroClient: Failed to retrieve CandidateId: {e}")
            return None

    def get_payslips(self, candidate_id: int, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """Gets a list of payslips for a given candidate."""
        endpoint = f"/candidates/{candidate_id}/pay_slips"
        params = {}
        if start_date:
            params["createdFrom"] = start_date
        if end_date:
            params["createdTo"] = end_date
        logger.info(f"KentroClient: Fetching payslip list for Candidate {candidate_id}")
        return self._make_request("GET", endpoint, params=params or None)

    def get_payslip_file(self, candidate_id: int, payslip_id: int) -> Dict[str, Any]:
        """RetrieVes the binary file (as a base64 string) for a specific payslip."""
        endpoint = f"/candidates/{candidate_id}/pay_slips/{payslip_id}/file"
        logger.info(f"KentroClient: Fetching payslip file {payslip_id} for Candidate {candidate_id}")
        return self._make_request("GET", endpoint)
    
    def get_contracts(self, candidate_id: int) -> List[Dict[str, Any]]:
        """
        Gets the list of contracts for a given candidate.
        
        Calls: GET /candidates/{CandidateId}/contracts
        """
        endpoint = f"/candidates/{candidate_id}/contracts" #
        logger.info(f"KentroClient: Fetching contracts for Candidate {candidate_id}")
        return self._make_request("GET", endpoint)
    
    def get_reservation_balances(self, candidate_id: int) -> List[Dict[str, Any]]:
        """
        Calls GET /candidates/{CandidateId}/reservation-balances
        (Uses this endpoint as .../reservations is deprecated)
        """
        endpoint = f"/candidates/{candidate_id}/reservation-balances"
        return self._make_request("GET", endpoint)
    

    