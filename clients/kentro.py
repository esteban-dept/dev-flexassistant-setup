# For paylisp, sick leave, and reservations

import requests
import os
from typing import Optional, Dict, Any, List

class KentroClient:
    """
    API Client for the Kentro (Pivoton) Public API.
    
    This client uses HTTP Basic Authentication to retrieve candidate-specific
    data for payslips, reservations, and contracts.
    """
    
    def __init__(self):
        """
        Initializes the client by loading credentials from environment variables.
        """
        self.base_url = os.environ.get("KENTRO_BASE_URL")
        self.username = os.environ.get("KENTRO_USERNAME")
        self.password = os.environ.get("KENTRO_PASSWORD")
        
        if not all([self.base_url, self.username, self.password]):
            raise ValueError("KENTRO_BASE_URL, KENTRO_USERNAME, and KENTRO_PASSWORD must be set.")
            
        # Set up the auth tuple for HTTPBasicAuth
        self.auth = (self.username, self.password)

    def _make_request(self, method: str, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        Helper function to make authenticated requests.
        """
        url = f"{self.base_url}{endpoint}"
        headers = {"Accept": "application/json"}
        
        try:
            response = requests.request(method, url, headers=headers, auth=self.auth, params=params)
            response.raise_for_status()  # Raises HTTPError for 4xx/5xx responses
            
            # Handle 204 No Content
            if response.status_code == 204:
                return None
                
            return response.json()
        except requests.exceptions.RequestException as e:
            # Log the error
            print(f"Error calling Kentro API endpoint {endpoint}: {e}")
            raise

    # --- Step 1: Get Candidate ID ---
    
    def get_candidate_id_from_email(self, email: str) -> Optional[int]:
        """
        Retrieves the internal CandidateId using the candidate's email address.
        This is required for all subsequent calls.
        
        Calls: GET /candidates
        """
        params = {"EmailAddress": email}
        try:
            candidates = self._make_request("GET", "/candidates", params=params)
            # Assuming the email is unique and returns one candidate
            if candidates and len(candidates) > 0:
                return candidates[0].get("CandidateId")
        except Exception as e:
            print(f"Failed to retrieve CandidateId for email {email}: {e}")
        
        return None

    # --- Tool Endpoints ---

    def get_payslips(self, candidate_id: int, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Gets a list of payslips for a given candidate.
        
        Calls: GET /candidates/{CandidateId}/pay_slips
        """
        endpoint = f"/candidates/{candidate_id}/pay_slips"
        params = {}
        if start_date:
            params["createdFrom"] = start_date
        if end_date:
            params["createdTo"] = end_date
        
        return self._make_request("GET", endpoint, params=params or None)

    def get_payslip_file(self, candidate_id: int, payslip_id: int) -> Dict[str, Any]:
        """
        Retrieves the binary file (as a base64 string) for a specific payslip.
        
        Calls: GET /candidates/{CandidateId}/pay_slips/{PaySlipId}/file
        """
        endpoint = f"/candidates/{candidate_id}/pay_slips/{payslip_id}/file"
        return self._make_request("GET", endpoint)

    def get_reservation_balances(self, candidate_id: int) -> List[Dict[str, Any]]:
        """
        Gets the list of reservation balances for a candidate.
        
        Calls: GET /candidates/{CandidateId}/reservation-balances
        """
        endpoint = f"/candidates/{candidate_id}/reservation-balances"
        return self._make_request("GET", endpoint)

    def get_contracts(self, candidate_id: int) -> List[Dict[str, Any]]:
        """
        Gets the list of contracts for a given candidate.
        
        Calls: GET /candidates/{CandidateId}/contracts
        """
        endpoint = f"/candidates/{candidate_id}/contracts"
        return self._make_request("GET", endpoint)

    def get_sick_leave(self, candidate_id: int) -> List[Dict[str, Any]]:
        """
        Placeholder for sick leave.
        
        NOTE: The endpoint for retrieving sick leave is NOT present in the
        provided OpenAPI specification. This functionality must be
        requested from Pivoton/Kentro.
        """
        print(f"Error: Sick leave functionality for Candidate {candidate_id} is not defined in the API spec.")
        # raise NotImplementedError("Sick leave endpoint is not specified in the Kentro API.")
        return []