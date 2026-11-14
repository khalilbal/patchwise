from __future__ import annotations

from urllib.request import urlopen


def is_cisa_kev(cve_id: str) -> bool:
    if not cve_id:
        return False
    try:
        url = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
        with urlopen(url, timeout=10) as response:
            payload = response.read().decode("utf-8")
        return cve_id.lower() in payload.lower()
    except Exception:
        return False
