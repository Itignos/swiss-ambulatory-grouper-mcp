"""HTTP client for the local Java TarifMatcher bridge."""
from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class TarifMatcherClientError(RuntimeError):
    """Raised when the TarifMatcher bridge cannot be reached or returns an error."""


class TarifMatcherClient:
    def __init__(self, base_url: str, *, timeout: int = 30) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def health(self) -> dict[str, Any]:
        return self._request("GET", "/health")

    def grouper_evaluate(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/grouper/evaluate", payload)

    def mapper_map(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/mapper/map", payload)

    def casemaster_apply(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/casemaster/apply", payload)

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = Request(
            self.base_url + path,
            data=data,
            method=method,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                body = response.read().decode("utf-8")
        except HTTPError as exc:
            raise TarifMatcherClientError(f"TarifMatcher bridge returned HTTP {exc.code}: {exc.reason}") from exc
        except URLError as exc:
            raise TarifMatcherClientError(f"TarifMatcher bridge is unavailable: {exc.reason}") from exc
        except OSError as exc:
            raise TarifMatcherClientError(f"TarifMatcher bridge request failed: {exc}") from exc

        try:
            parsed = json.loads(body) if body else {}
        except json.JSONDecodeError as exc:
            raise TarifMatcherClientError(f"TarifMatcher bridge returned invalid JSON: {body[:200]}") from exc
        if not isinstance(parsed, dict):
            raise TarifMatcherClientError("TarifMatcher bridge returned a non-object JSON response")
        return parsed
