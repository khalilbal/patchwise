from __future__ import annotations

import json
from typing import Any

import requests


def lookup_osv(package_name: str, version: str) -> dict[str, Any]:
    if not package_name:
        return {}
    url = "https://api.osv.dev/v1/query"
    payload = {"version": version, "package": {"name": package_name, "ecosystem": "PyPI"}}
    try:
        response = requests.post(url, data=json.dumps(payload), timeout=10)
        response.raise_for_status()
    except Exception:
        return {}
    try:
        data = response.json()
    except ValueError:
        return {}
    return data
