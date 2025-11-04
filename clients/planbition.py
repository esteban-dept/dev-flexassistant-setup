# For schedule data (employee data and employee schedule)

# File: planbition_client.py

import requests
import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

# Set up logging
logger = logging.getLogger(__name__)

class PlanbitionClient:
    """
    Client for the Planbition REST API.
    
    Handles JWT token authentication and provides methods for
    retrieving schedule data as required by the GetScheduleTool.
    """
    
    def __init__(self):
        """Initializes the client by loading credentials from environment variables."""
        self.base_url = os.environ.get("PLANBITION_BASE_URL")
        self.api_key = os.environ.get("PLANBITION_KEY")
        self.username = os.environ.get("PLANBITION_USERNAME")
        self.password = os.environ.get("PLANBITION_PASSWORD")
        
        if not all([self.base_url, self.api_key, self.username, self.password]):
            logger.error("PLANBITION_BASE_URL, KEY, USERNAME, or PASSWORD not set.")
            raise ValueError("Planbition API credentials are not fully configured.")
            
        self._bearer_token: Optional[str] = None
        self._token_expiry = datetime.now()

    def _get_bearer_token(self) -> str:
        """
        Retrieves a valid 60-minute bearer token, authenticating if necessary.
        
        This method caches the token until it's within a 1-minute
        expiry window.
        """
        # Check if current token is valid (with a 1-minute buffer)
        if self._bearer_token and self._token_expiry > (datetime.now() + timedelta(minutes=1)):
            return self._bearer_token
            
        # Token is invalid or expired, perform authentication
        auth_url = f"{self.base_url}/authenticate/login"
        auth_payload = {
            "Key": self.api_key,
            "UserName": self.username,
            "Password": self.password
        }
        
        try:
            logger.info("Authenticating with Planbition API...")
            response = requests.post(auth_url, json=auth_payload)
            response.raise_for_status()
            
            response_data = response.json()
            if not response_data.get("success") or not response_data.get("token"):
                logger.error(f"Planbition auth failed: {response_data.get('error')}")
                raise Exception(f"Planbition auth failed: {response_data.get('error', 'No token')}")

            self._bearer_token = response_data["token"]
            # Token is valid for 60 minutes
            self._token_expiry = datetime.now() + timedelta(minutes=60)
            logger.info("Successfully retrieved Planbition token.")
            return self._bearer_token
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error during Planbition authentication: {e}")
            raise

    def _make_request(self, method: str, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Helper function to make authenticated API requests."""
        token = self._get_bearer_token()
        
        url = f"{self.base_url}/api/{endpoint}" # All API endpoints are prefixed with /api/
        headers = {
            "Authorization": f"Bearer {token}", 
            "Content-Type": "application/json",
            "Accept": "text/plain" 
        }
        
        try:
            response = requests.request(method, url, headers=headers, params=params)
            
            # Handle token expiry (403 Forbidden is a common response)
            if response.status_code == 403: 
                logger.warning("Received 403 (Forbidden), retrying with new token.")
                self._bearer_token = None # Force re-authentication
                token = self._get_bearer_token()
                headers["Authorization"] = f"Bearer {token}"
                response = requests.request(method, url, headers=headers, params=params)

            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling Planbition API {endpoint}: {e}")
            raise

    def get_employee_schedule(self, employee_number: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """
        Fetches the schedule for a specific employee within a date range.
        
        This uses the ScheduleEmployeeShiftDemand GET endpoint and filters
        by employeeNumber and the shift's start time.
        
        Args:
            employee_number: The unique employee number of the flex worker.
            start_date: The start of the date range (e.g., "YYYY-MM-DD").
            end_date: The end of the date range (e.g., "YYYY-MM-DD").
            
        Returns:
            A list of schedule entries.
        """
        
        endpoint = "ScheduleEmployeeShiftDemand" # [cite: 3243]
        
        # This filter is more robust because 'employeeNumber' is a
        # confirmed field in the GET response for this endpoint.
        filters = [
            f"employeeNumber eq '{employee_number}'",
            f"startTime ge {start_date}", # Filter for shifts starting on or after this date
            f"startTime le {end_date}"  # Filter for shifts starting on or before this date
        ]
        
        params = {
            "filter": " and ".join(filters), # [cite: 1566-1567]
            "PageNumber": 1,                 # [cite: 1513]
            "PageSize": 100                  # [cite: 1517, 1521]
        }
        
        try:
            return self._make_request("GET", endpoint, params=params)
        except Exception as e:
            print(f"Could not retrieve schedule for employee {employee_number}: {e}")
            return []