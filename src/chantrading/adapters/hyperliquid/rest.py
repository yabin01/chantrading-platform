"""Minimal JSON REST transport for Hyperliquid Info requests.

Transport only: no trading or strategy decisions belong here.
"""
from __future__ import annotations

import json
import urllib.request
import urllib.error
from dataclasses import dataclass


@dataclass(frozen=True)
class RestResponse:
    status_code: int
    payload: object


class HyperliquidRestClient:
    def __init__(self, base_url: str, timeout_seconds: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def post_info(self, payload: dict) -> object:
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/info",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Hyperliquid Info HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise ConnectionError(f"Hyperliquid Info transport error: {exc}") from exc
