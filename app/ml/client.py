from __future__ import annotations

from typing import Any, Dict

import aiohttp

from app.config import Config


class MlAdvisorClient:
    def __init__(self, config: Config) -> None:
        self._base_url = config.ml_base_url.strip()

    def is_enabled(self) -> bool:
        return bool(self._base_url)

    async def evaluate_setup(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.is_enabled():
            return {"ml_score": 0.0, "blacklisted": False, "reason": "", "parameter_adjustments": {}}
        url = f"{self._base_url.rstrip('/')}/evaluate_setup"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=5) as resp:
                    if resp.status >= 400:
                        return {"ml_score": 0.0, "blacklisted": False, "reason": "", "parameter_adjustments": {}}
                    data = await resp.json()
                    return {
                        "ml_score": float(data.get("ml_score", 0.0)),
                        "blacklisted": bool(data.get("blacklisted", False)),
                        "reason": data.get("reason", ""),
                        "parameter_adjustments": data.get("parameter_adjustments", {}),
                    }
        except Exception:
            return {"ml_score": 0.0, "blacklisted": False, "reason": "", "parameter_adjustments": {}}

    async def reload_model(self) -> str:
        if not self.is_enabled():
            return "ML Advisor is disabled in config."
        
        url = f"{self._base_url.rstrip('/')}/reload"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, timeout=5) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return f"ML Server Response: {data.get('message')} (Mode: {data.get('mode')})"
                    else:
                        return f"Error: ML Server returned status {resp.status}"
        except Exception as e:
            return f"Connection failed: {str(e)}"

