# For schedule data (employee data and employee schedule)

import requests
import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Union

# Set up logging
logger = logging.getLogger(__name__)

class PlanbitionClient:
    """
    Client for the Planbition REST API.
    """
    
    def __init__(self):
        self.base_url = os.environ.get("PLANBITION_BASE_URL")
        self.api_key = os.environ.get("PLANBITION_KEY")
        self.username = os.environ.get("PLANBITION_USERNAME")
        self.password = os.environ.get("PLANBITION_PASSWORD")
        
        if not all([self.base_url, self.api_key, self.username, self.password]):
            logger.error("PLANBITION credentials not fully configured.")
            raise ValueError("Planbition API credentials are missing.")
            
        self._bearer_token: Optional[str] = None
        self._token_expiry = datetime.now()

    def _get_bearer_token(self) -> str:
        """Retrieves or refreshes the 60-minute JWT bearer token."""
        if self._bearer_token and self._token_expiry > (datetime.now() + timedelta(minutes=1)):
            return self._bearer_token
            
        auth_url = f"{self.base_url}/authenticate/login"
        auth_payload = {
            "Key": self.api_key,
            "UserName": self.username,
            "Password": self.password
        }
        
        try:
            response = requests.post(auth_url, json=auth_payload)
            response.raise_for_status()
            data = response.json()
            
            if not data.get("success") or not data.get("token"):
                raise Exception(f"Auth failed: {data.get('error')}")

            self._bearer_token = data["token"]
            self._token_expiry = datetime.now() + timedelta(minutes=60)
            return self._bearer_token
        except Exception as e:
            logger.error(f"Planbition auth error: {e}")
            raise

    def _make_request(self, method: str, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Makes an authenticated request to the API."""
        token = self._get_bearer_token()
        url = f"{self.base_url}/api/{endpoint}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "text/plain"
        }
        
        try:
            response = requests.request(method, url, headers=headers, params=params)
            if response.status_code == 403:
                self._bearer_token = None
                headers["Authorization"] = f"Bearer {self._get_bearer_token()}"
                response = requests.request(method, url, headers=headers, params=params)
                
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error calling {endpoint}: {e}")
            raise

    def _parse_api_datetime(self, date_obj: Union[Dict[str, int], str]) -> Optional[datetime]:
        """
        Helper to parse the specific dictionary date format returned by this API.
        Handles both dict: {'year': 2024, 'month': 11, ...} and ISO strings.
        """
        if not date_obj:
            return None
            
        if isinstance(date_obj, dict):
            try:
                return datetime(
                    year=date_obj.get('year', 1970),
                    month=date_obj.get('month', 1),
                    day=date_obj.get('day', 1),
                    hour=date_obj.get('hour', 0),
                    minute=date_obj.get('minute', 0),
                    second=date_obj.get('second', 0)
                )
            except Exception as e:
                logger.warning(f"Failed to parse date dict: {date_obj} - {e}")
                return None
                
        if isinstance(date_obj, str):
            try:
                return datetime.fromisoformat(date_obj)
            except ValueError:
                return None
                
        return None

    def get_employee_schedule(self, employee_number: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """
        Fetches schedule and filters client-side using custom date parsing.
        """
        # 1. Parse request input dates
        try:
            if not start_date or not end_date:
                 raise ValueError("Dates cannot be empty")
            req_start = datetime.fromisoformat(str(start_date))
            req_end = datetime.fromisoformat(str(end_date))
            req_end = req_end.replace(hour=23, minute=59, second=59)
        except Exception as e:
            logger.error(f"Invalid input dates: {e}")
            return []

        endpoint = "ScheduleEmployeeShiftDemand"
        params = {
            "filter": f"contains(EmployeeNumber, '{employee_number}')",
            "PageNumber": 1,
            "PageSize": 500 
        }
        
        try:
            logger.info(f"Fetching schedule for {employee_number}...")
            response = self._make_request("GET", endpoint, params=params)
            all_items = response.get("items", [])
            
            filtered_items = []
            for item in all_items:
                # Use new helper to parse the complex dictionary format
                start_val = item.get('StartTime') or item.get('startTime')
                shift_start = self._parse_api_datetime(start_val)

                if shift_start and req_start <= shift_start <= req_end:
                    # Optional: Enrich item with a standard ISO string for easier frontend use
                    item['iso_start_time'] = shift_start.isoformat()
                    filtered_items.append(item)
            
            logger.info(f"Returning {len(filtered_items)} valid shifts.")
            return filtered_items

        except Exception as e:
            logger.error(f"Error in get_employee_schedule: {e}")
            return []

    def get_employee_details(self, employee_number: str) -> Optional[Dict[str, Any]]:
        # ... (previous implementation was fine, no changes needed here) ...
        endpoint = "Employee"
        params = {"filter": f"contains(EmployeeNumber, '{employee_number}')"}
        try:
            result = self._make_request("GET", endpoint, params=params)
            items = result.get("items", [])
            if items:
                emp = items[0]
                first = emp.get('firstName', '').strip()
                insertion = emp.get('insertion', '').strip()
                last = emp.get('lastName', '').strip()
                full_name = f"{first} {insertion} {last}" if insertion else f"{first} {last}"

                return {
                    "employee_id": emp.get("id"),
                    "employee_number": emp.get("employeeNumber"),
                    "full_name": full_name.strip(),
                    "email": emp.get("email"),
                    "country": emp.get("country", "Unknown"),
                    "is_active": emp.get("isActive", False)
                }
            return None
        except Exception as e:
            logger.error(f"Failed to get employee details: {e}")
            return None