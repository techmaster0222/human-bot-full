"""
AdsPower API Client
Low-level client for AdsPower Local API.
"""

import json
from dataclasses import dataclass
from typing import Any

import requests
from loguru import logger


@dataclass
class APIResponse:
    """Wrapper for AdsPower API responses"""

    success: bool
    code: int
    msg: str
    data: dict[str, Any]

    @classmethod
    def from_response(cls, response: requests.Response) -> "APIResponse":
        """Create from requests Response"""
        try:
            json_data = response.json()
            return cls(
                success=json_data.get("code") == 0,
                code=json_data.get("code", -1),
                msg=json_data.get("msg", ""),
                data=json_data.get("data", {}),
            )
        except Exception as e:
            return cls(success=False, code=-1, msg=str(e), data={})

    @classmethod
    def error(cls, msg: str) -> "APIResponse":
        """Create error response"""
        return cls(success=False, code=-1, msg=msg, data={})


def create_proxy_config(
    proxy_type: str = "http", host: str = "", port: int = 0, username: str = "", password: str = ""
) -> dict[str, str]:
    """
    Create proxy configuration for AdsPower API.

    Args:
        proxy_type: Proxy type (http, https, socks5)
        host: Proxy host
        port: Proxy port
        username: Proxy username
        password: Proxy password

    Returns:
        Dict with proxy configuration
    """
    return {
        "proxy_type": proxy_type,
        "proxy_host": host,
        "proxy_port": str(port),
        "proxy_user": username,
        "proxy_password": password,
        "proxy_soft": "other",
    }


class AdsPowerClient:
    """
    Low-level client for AdsPower Local API.

    API Documentation: https://localapi-doc-en.adspower.com/

    Usage:
        client = AdsPowerClient("http://local.adspower.net:50325")

        # Check status
        if client.check_status():
            print("AdsPower is running")

        # Create profile
        response = client.create_profile(name="my_profile")
        profile_id = response.data.get("id")

        # Start browser
        response = client.start_browser(profile_id)
        ws_url = response.data.get("ws", {}).get("puppeteer")
    """

    def __init__(self, api_url: str = "http://local.adspower.net:50325", api_key: str = None):
        """
        Initialize AdsPower client.

        Args:
            api_url: AdsPower Local API URL
            api_key: API key (optional, depends on AdsPower settings)
        """
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.timeout = 30

        logger.debug(f"AdsPowerClient initialized: {self.api_url}")

    def _request(
        self, method: str, endpoint: str, params: dict = None, json_data: dict = None
    ) -> APIResponse:
        """Make API request"""
        url = f"{self.api_url}{endpoint}"

        # Add API key if configured
        if self.api_key:
            params = params or {}
            params["api_key"] = self.api_key

        try:
            if method.upper() == "GET":
                response = requests.get(url, params=params, timeout=self.timeout)
            else:
                response = requests.post(url, params=params, json=json_data, timeout=self.timeout)

            return APIResponse.from_response(response)

        except requests.exceptions.ConnectionError:
            return APIResponse.error("Cannot connect to AdsPower. Is it running?")
        except requests.exceptions.Timeout:
            return APIResponse.error("Request timed out")
        except Exception as e:
            return APIResponse.error(f"Request failed: {e}")

    # ============== Status ==============

    def check_status(self) -> bool:
        """
        Check if AdsPower is running.

        Returns:
            True if AdsPower is accessible
        """
        response = self._request("GET", "/status")
        return response.success

    # ============== Profile Management ==============

    def create_profile(
        self,
        name: str,
        group_id: str = None,
        domain_name: str = None,
        proxy_config: dict = None,
        fingerprint_config: dict = None,
        user_agent: str = None,
    ) -> APIResponse:
        """
        Create a new browser profile.

        Args:
            name: Profile name
            group_id: Group ID for organization (optional, omit for ungrouped)
            domain_name: Primary domain
            proxy_config: Proxy configuration dict
            fingerprint_config: Browser fingerprint config
            user_agent: Custom user agent

        Returns:
            APIResponse with profile ID in data
        """
        payload = {
            "name": name,
            "group_id": group_id or "0",  # AdsPower requires group_id
        }

        if domain_name:
            payload["domain_name"] = domain_name

        if proxy_config:
            payload["user_proxy_config"] = proxy_config

        if fingerprint_config:
            payload["fingerprint_config"] = fingerprint_config
        else:
            # Default fingerprint config
            payload["fingerprint_config"] = {
                "automatic_timezone": "1",
                "language": ["en-US", "en"],
                "flash": "block",
                "scan_port_type": "1",
                "webrtc": "proxy",
                "canvas": "1",
                "webgl_image": "1",
                "webgl": "3",
                "audio": "1",
                "client_rects": "1",
                "device_name_switch": "1",
                "random_ua": {
                    "ua_browser": ["chrome"],
                    "ua_version": ["120", "121", "122", "123", "124", "125"],
                },
            }

        if user_agent:
            payload["fingerprint_config"]["ua"] = user_agent

        return self._request("POST", "/api/v1/user/create", json_data=payload)

    def get_profile(self, profile_id: str) -> APIResponse:
        """Get profile details"""
        return self._request("GET", "/api/v1/user/info", params={"user_id": profile_id})

    def list_profiles(
        self, page: int = 1, page_size: int = 100, group_id: str = None, search: str = None
    ) -> APIResponse:
        """
        List all profiles.

        Args:
            page: Page number
            page_size: Results per page
            group_id: Filter by group
            search: Search keyword

        Returns:
            APIResponse with list of profiles
        """
        params = {"page": page, "page_size": page_size}

        if group_id:
            params["group_id"] = group_id
        if search:
            params["search"] = search

        return self._request("GET", "/api/v1/user/list", params=params)

    def update_profile(self, profile_id: str, **kwargs) -> APIResponse:
        """Update profile settings"""
        payload = {"user_id": profile_id, **kwargs}
        return self._request("POST", "/api/v1/user/update", json_data=payload)

    def update_profile_proxy(self, profile_id: str, proxy_config: dict) -> APIResponse:
        """Update profile proxy settings"""
        return self.update_profile(profile_id, user_proxy_config=proxy_config)

    def delete_profile(self, profile_ids: list[str]) -> APIResponse:
        """
        Delete profiles.

        Args:
            profile_ids: List of profile IDs to delete

        Returns:
            APIResponse
        """
        payload = {"user_ids": profile_ids}
        return self._request("POST", "/api/v1/user/delete", json_data=payload)

    # ============== Browser Control ==============

    def start_browser(
        self,
        profile_id: str,
        headless: bool = False,
        open_url: str = None,
        launch_args: list[str] = None,
    ) -> APIResponse:
        """
        Start browser for a profile.

        Args:
            profile_id: Profile ID
            headless: Run in headless mode
            open_url: URL to open on start
            launch_args: Additional Chrome arguments

        Returns:
            APIResponse with WebSocket URLs for automation
        """
        params = {"user_id": profile_id, "headless": "1" if headless else "0"}

        if open_url:
            params["open_urls"] = open_url

        if launch_args:
            # AdsPower expects launch_args as a JSON string
            params["launch_args"] = json.dumps(launch_args)

        return self._request("GET", "/api/v1/browser/start", params=params)

    def stop_browser(self, profile_id: str) -> APIResponse:
        """Stop browser for a profile"""
        return self._request("GET", "/api/v1/browser/stop", params={"user_id": profile_id})

    def check_browser_status(self, profile_id: str) -> APIResponse:
        """Check if browser is running for a profile"""
        return self._request("GET", "/api/v1/browser/active", params={"user_id": profile_id})

    # ============== Groups ==============

    def list_groups(self, page: int = 1, page_size: int = 100) -> APIResponse:
        """List profile groups"""
        return self._request(
            "GET", "/api/v1/group/list", params={"page": page, "page_size": page_size}
        )

    def create_group(self, name: str) -> APIResponse:
        """Create a profile group"""
        return self._request("POST", "/api/v1/group/create", json_data={"group_name": name})
