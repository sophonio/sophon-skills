"""Fetches report rows from the remote sales API."""

import httpx

BASE_URL = "https://sales.example.test/api"


def fetch_rows(region, page=1):
    response = httpx.get(f"{BASE_URL}/rows", params={"region": region, "page": page}, timeout=10.0)
    response.raise_for_status()
    return response.json()["rows"]
