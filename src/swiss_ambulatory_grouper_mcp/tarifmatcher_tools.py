"""High-level tool helpers exposed by the MCP layer."""
from __future__ import annotations

from typing import Any, Protocol


class GrouperClient(Protocol):
    def grouper_evaluate(self, payload: dict[str, Any]) -> dict[str, Any]: ...


def normalize_services(services: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for service in services:
        code = str(service.get("code", "")).strip()
        if not code:
            raise ValueError("Each service must include a non-empty code")
        normalized.append(
            {
                "code": code,
                "quantity": int(service.get("quantity", 1)),
                "side": service.get("side"),
                "date": service.get("date"),
            }
        )
    return normalized


def evaluate_grouper(
    client: GrouperClient,
    *,
    sex: str,
    age_years: int,
    diagnosis: str,
    services: list[dict[str, Any]],
    drugs: list[dict[str, Any]] | None = None,
    entry_date: str | None = None,
    age_days: int = 0,
    birth_date: str | None = None,
    capitulum: str | None = None,
    include_decision_path: bool = False,
    include_tax_points: bool = False,
    include_catalog_labels: bool = False,
) -> dict[str, Any]:
    if not services:
        raise ValueError("A grouper evaluation requires at least one service")
    diagnosis = diagnosis.strip()
    if not diagnosis:
        raise ValueError("A grouper evaluation requires a diagnosis")

    payload = {
        "patient_case": {
            "sex": sex,
            "age_years": int(age_years),
            "age_days": int(age_days),
            "birth_date": birth_date,
            "entry_date": entry_date,
            "diagnosis": diagnosis,
            "capitulum": capitulum,
            "services": normalize_services(services),
            "drugs": drugs or [],
        },
        "options": {
            "include_decision_path": include_decision_path,
            "include_tax_points": include_tax_points,
            "include_catalog_labels": include_catalog_labels,
        },
    }
    return client.grouper_evaluate(payload)
