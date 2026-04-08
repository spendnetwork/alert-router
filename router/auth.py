"""
Spend Network API authentication.

Authenticates with the Spend Network API and returns a bearer token
for use in subsequent API calls.
"""

import sys
import requests

API_BASE = "https://api.spendnetwork.cloud"
LOGIN_ENDPOINT = f"{API_BASE}/api/v3/login/access-token"


def get_token(username: str, password: str) -> str:
    """
    Authenticate with Spend Network API.

    Args:
        username: Spend Network login email
        password: Spend Network password

    Returns:
        Bearer token string.

    Raises:
        SystemExit with clear message on failure.
    """
    try:
        response = requests.post(
            LOGIN_ENDPOINT,
            json={"username": username, "password": password},
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
    except requests.RequestException as e:
        print(f"[ERROR] Network error during authentication: {e}")
        sys.exit(1)

    if response.status_code != 200:
        print(f"[ERROR] Authentication failed (HTTP {response.status_code})")
        print(f"[ERROR] Response: {response.text}")
        sys.exit(1)

    data = response.json()
    token = data.get("access_token")

    if not token:
        print(f"[ERROR] No access_token in response: {data}")
        sys.exit(1)

    return token
