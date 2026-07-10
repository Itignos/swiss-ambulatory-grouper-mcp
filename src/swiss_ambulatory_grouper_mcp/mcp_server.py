"""Minimal HTTP entrypoint for local Docker smoke tests.

This module is the runtime shell that will host MCP tools. The first skeleton
exposes HTTP endpoints so Docker/Kubernetes health and bridge wiring can be
verified before the real MCP transport is added.
"""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from typing import Any

from .lookup_service import LookupError, SQLiteLookupService
from .tarifmatcher_client import TarifMatcherClient, TarifMatcherClientError
from .tarifmatcher_runtime import TarifMatcherRuntimeConfig
from .tarifmatcher_tools import evaluate_grouper


class RuntimeHandler(BaseHTTPRequestHandler):
    client: TarifMatcherClient
    lookup: SQLiteLookupService
    runtime_config: TarifMatcherRuntimeConfig

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._handle_health()
            return
        self._send_json(404, {"ok": False, "error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path == "/grouper/evaluate":
            self._handle_grouper_evaluate()
            return
        if self.path == "/mapper/map":
            self._handle_mapper_map()
            return
        if self.path == "/lookup/lkaat/search":
            self._handle_lkaat_search()
            return
        if self.path == "/lookup/lkaat/details":
            self._handle_lkaat_details()
            return
        if self.path == "/lookup/diagnoses/search":
            self._handle_diagnosis_search()
            return
        self._send_json(404, {"ok": False, "error": "not_found"})

    def log_message(self, format: str, *args: object) -> None:
        # Keep container logs concise; explicit responses/errors are JSON.
        return

    def _handle_health(self) -> None:
        try:
            bridge = self.client.health()
            self._send_json(
                200,
                {
                    "ok": True,
                    "status": "running",
                    "runtime_files": self.runtime_config.validate_files(),
                    "bridge": bridge,
                },
            )
        except TarifMatcherClientError as exc:
            self._send_json(
                503,
                {
                    "ok": False,
                    "status": "bridge_unavailable",
                    "runtime_files": self.runtime_config.validate_files(),
                    "error": str(exc),
                },
            )

    def _handle_grouper_evaluate(self) -> None:
        try:
            payload = self._read_json()
            result = evaluate_grouper(
                self.client,
                sex=payload["sex"],
                age_years=payload["age_years"],
                diagnosis=payload["diagnosis"],
                services=payload["services"],
                drugs=payload.get("drugs"),
                entry_date=payload.get("entry_date"),
                age_days=payload.get("age_days", 0),
                birth_date=payload.get("birth_date"),
                capitulum=payload.get("capitulum"),
                include_decision_path=payload.get("include_decision_path", False),
                include_tax_points=payload.get("include_tax_points", False),
                include_catalog_labels=payload.get("include_catalog_labels", False),
            )
            self._send_json(200 if result.get("ok", False) else 502, result)
        except (KeyError, TypeError, ValueError) as exc:
            self._send_json(400, {"ok": False, "error": "invalid_request", "message": str(exc)})
        except TarifMatcherClientError as exc:
            self._send_json(503, {"ok": False, "error": "bridge_unavailable", "message": str(exc)})

    def _handle_mapper_map(self) -> None:
        try:
            payload = self._read_json()
            result = self.client.mapper_map({"patient_case": payload})
            self._send_json(200 if result.get("ok", False) else 502, result)
        except (TypeError, ValueError) as exc:
            self._send_json(400, {"ok": False, "error": "invalid_request", "message": str(exc)})
        except TarifMatcherClientError as exc:
            self._send_json(503, {"ok": False, "error": "bridge_unavailable", "message": str(exc)})

    def _handle_lkaat_search(self) -> None:
        try:
            payload = self._read_json()
            result = self.lookup.search_lkaat(
                query=payload["query"],
                language=payload.get("language", "de"),
                limit=payload.get("limit", 20),
            )
            self._send_json(200, result)
        except (KeyError, TypeError, ValueError, LookupError) as exc:
            self._send_json(400, {"ok": False, "error": "invalid_request", "message": str(exc)})

    def _handle_lkaat_details(self) -> None:
        try:
            payload = self._read_json()
            result = self.lookup.lkaat_details(
                code=payload["code"],
                language=payload.get("language", "de"),
            )
            self._send_json(200 if result.get("ok", False) else 404, result)
        except (KeyError, TypeError, ValueError, LookupError) as exc:
            self._send_json(400, {"ok": False, "error": "invalid_request", "message": str(exc)})

    def _handle_diagnosis_search(self) -> None:
        try:
            payload = self._read_json()
            result = self.lookup.search_diagnoses(
                query=payload["query"],
                language=payload.get("language", "de"),
                limit=payload.get("limit", 20),
            )
            self._send_json(200, result)
        except (KeyError, TypeError, ValueError, LookupError) as exc:
            self._send_json(400, {"ok": False, "error": "invalid_request", "message": str(exc)})

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            raise ValueError("Request JSON must be an object")
        return parsed

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def run() -> None:
    config = TarifMatcherRuntimeConfig.from_env()
    RuntimeHandler.runtime_config = config
    RuntimeHandler.client = TarifMatcherClient(config.base_url)
    RuntimeHandler.lookup = SQLiteLookupService(config.sqlite_db)
    port = int(os.environ.get("MCP_PORT", os.environ.get("PORT", "3000")))
    server = ThreadingHTTPServer(("0.0.0.0", port), RuntimeHandler)
    print(f"Swiss ambulatory MCP runtime listening on port {port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    run()
