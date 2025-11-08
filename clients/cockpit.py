# For branch details and vacancy matches

import requests
import os
from datetime import datetime, timedelta

class CockpitATSClient:
    """
    A client for the RecruitNow Cockpit Candidate Profile API.
    
    This client manages the candidate-specific bearer token via
    token exchange and provides methods to access required endpoints.
    """
    
    def __init__(self, identity_provider_token: str):
        """
        Initializes the client.
        
        Args:
            identity_provider_token: The access token from the primary
                                     identity provider (e.g., Auth0)
                                     for the logged-in flex worker.
        """
        self.base_url = os.environ.get("COCKPIT_BASE_URL")
        if not self.base_url:
            raise ValueError("COCKPIT_BASE_URL environment variable not set.")
            
        self.identity_token = identity_provider_token
        self._bearer_token = None
        self._token_expiry = datetime.now()

    def _get_bearer_token(self) -> str:
        """
        Retrieves a valid candidate-specific bearer token.
        
        If the current token is valid (not expired), it returns it.
        Otherwise, it performs a token exchange to get a new one
        """
        # Check if current token is valid (with a 1-minute buffer)
        if self._bearer_token and self._token_expiry > (datetime.now() + timedelta(minutes=1)):
            return self._bearer_token
            
        # Token is invalid or expired, perform token exchange
        token_exchange_url = f"{self.base_url}/candidateprofile/api/authentication/token"
        headers = {"Content-Type": "application/json", "accept": "application/json"}
        payload = {"token": self.identity_token} 
        
        try:
            response = requests.post(token_exchange_url, json=payload, headers=headers)
            response.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)
            
            # The API doc doesn't specify the response format, but we assume
            # it returns a JSON object with the token.
            # Common formats are {'token': '...'} or {'access_token': '...'}.
            # Adjust the key 'access_token' if the actual response differs.
            response_data = response.json()
            
            if "access_token" not in response_data and "token" not in response_data:
                raise ValueError("Token key not found in token exchange response.")

            self._bearer_token = response_data.get("access_token") or response_data.get("token")
            print("Debug bearer token:", self._bearer_token)

            # Token is valid for one hour 
            self._token_expiry = datetime.now() + timedelta(hours=1)
            
            return self._bearer_token
            
        except requests.exceptions.RequestException as e:
            # Log the error (e.g., using Azure Monitor)
            print(f"Error during Cockpit token exchange: {e}")
            raise

    def _make_request(self, method: str, endpoint: str) -> dict:
        """Helper function to make authenticated GET requests."""
        token = self._get_bearer_token()
        
        url = f"{self.base_url}/candidateprofile/api/v1/{endpoint}" 
        headers = {
            "Authorization": f"bearer {token}", 
            "accept": "application/json"
        }
        
        try:
            response = requests.request(method, url, headers=headers)
            
            if response.status_code == 401: 
                # Token may have been revoked. Clear cache and retry once.
                self._bearer_token = None 
                token = self._get_bearer_token()
                headers["Authorization"] = f"bearer {token}"
                response = requests.request(method, url, headers=headers)

            response.raise_for_status()
            
            if response.status_code == 204: # No Content [cite: 518]
                return {}
                
            return response.json() [cite: 513]
            
        except requests.exceptions.RequestException as e:
            # Log the error
            print(f"Error calling Cockpit API endpoint {endpoint}: {e}")
            raise

    # --- Endpoint Implementation ---

    def get_branch_details(self) -> dict:
        """
        Gets the owner (branch) information for the candidate.
        Used by the Fallback Tool.
        
        [HTTPGET] candidateprofile/api/v1/candidatesprofile/owner 
        """
        return self._make_request("GET", "candidatesprofile/owner")

    def get_vacancy_matches(self) -> dict:
        """
        Gets a list of vacancy matches for the candidate. 
        
        [HTTPGET] candidateprofile/api/v1/candidatesprofile/matches 
        """
        return self._make_request("GET", "candidatesprofile/matches")
