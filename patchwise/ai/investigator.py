from __future__ import annotations

import os
from typing import Any

import requests


class AIInvestigator:
    def __init__(self, api_key: str | None = None, base_url: str | None = None, model: str = "gpt-4o-mini") -> None:
        self.api_key = api_key or os.getenv("PATCHWISE_AI_API_KEY", "")
        self.base_url = (base_url or os.getenv("PATCHWISE_AI_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
        self.model = model or os.getenv("PATCHWISE_AI_MODEL", "gpt-4o-mini")

    def available(self) -> bool:
        return bool(self.api_key) and bool(self.base_url)

    def investigate(self, finding: dict[str, Any], source_excerpt: str) -> dict[str, Any]:
        if not self.available():
            return {"summary": "AI investigation is disabled because no API key or base URL is configured.", "confidence": "low"}

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a careful security investigator. Distinguish facts from hypotheses and do not claim information without evidence."},
                {"role": "user", "content": f"Evaluate this finding cautiously:\n{finding}\n\nSource excerpt:\n{source_excerpt}"},
            ],
            "temperature": 0.2,
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        try:
            response = requests.post(f"{self.base_url}/chat/completions", json=payload, headers=headers, timeout=20)
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            return {"summary": content, "confidence": "medium"}
        except Exception:
            return {"summary": "AI investigation could not complete. Check API connectivity and the configured credentials.", "confidence": "low"}
