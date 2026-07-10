"""SQLite-backed lookup helpers for LKAAT services and ICD-10 diagnoses."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3
from typing import Any


LANGUAGE_TO_LK = {"de": "D", "fr": "F", "it": "I"}
SUPPORTED_LANGUAGES = set(LANGUAGE_TO_LK)


class LookupError(ValueError):
    """Raised for invalid lookup requests or unavailable lookup data."""


def normalize_language(language: str | None) -> str:
    lang = (language or "de").strip().lower()
    if lang not in SUPPORTED_LANGUAGES:
        raise LookupError(f"Unsupported language '{language}'. Expected one of: de, fr, it")
    return lang


def like_pattern(query: str) -> str:
    value = query.strip()
    if not value:
        raise LookupError("query must not be empty")
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {key: row[key] for key in row.keys()}


@dataclass(frozen=True)
class SQLiteLookupService:
    """Read-only lookup service over the generated Swiss ambulatory SQLite DB."""

    db_path: Path | None

    def _connect(self) -> sqlite3.Connection:
        if self.db_path is None:
            raise LookupError("SWISS_AMBULATORY_GROUPER_DB is not configured")
        if not self.db_path.exists():
            raise LookupError(f"SQLite database not found: {self.db_path}")
        con = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
        con.row_factory = sqlite3.Row
        return con

    def search_lkaat(self, query: str, language: str | None = "de", limit: int = 20) -> dict[str, Any]:
        lang = normalize_language(language)
        lk_lang = LANGUAGE_TO_LK[lang]
        limit = bounded_limit(limit)
        pattern = like_pattern(query)
        code_pattern = pattern.replace(".", "")
        with self._connect() as con:
            rows = con.execute(
                """
                SELECT
                    l.LKN AS code,
                    t.SPRACHE AS source_language,
                    t.BEZ_255 AS title,
                    t.MED_INTERPRET AS medical_interpretation,
                    l.LEISTUNG_TYP AS service_type,
                    l.SEITE AS side_required,
                    l.PROCEDURE_TYPE AS procedure_type,
                    l.USED_FOR_GROUPING AS used_for_grouping,
                    l.ASSIGNED_SERVICE_POSITION AS assigned_service_position,
                    l.GUELTIG_VON AS valid_from,
                    l.GUELTIG_BIS AS valid_to,
                    CASE
                        WHEN replace(l.LKN, '.', '') = replace(:query, '.', '') THEN 0
                        WHEN replace(l.LKN, '.', '') LIKE :code_pattern ESCAPE '\\' THEN 1
                        WHEN t.BEZ_255 LIKE :pattern ESCAPE '\\' THEN 2
                        WHEN t.MED_INTERPRET LIKE :pattern ESCAPE '\\' THEN 3
                        ELSE 9
                    END AS rank
                FROM LK_LEISTUNG l
                JOIN LK_LEISTUNG_TEXT t ON t.LKN = l.LKN
                WHERE t.SPRACHE = :language
                  AND (
                    replace(l.LKN, '.', '') LIKE :code_pattern ESCAPE '\\'
                    OR t.BEZ_255 LIKE :pattern ESCAPE '\\'
                    OR t.MED_INTERPRET LIKE :pattern ESCAPE '\\'
                  )
                ORDER BY rank, l.LKN
                LIMIT :limit
                """,
                {
                    "query": query.strip(),
                    "pattern": pattern,
                    "code_pattern": code_pattern,
                    "language": lk_lang,
                    "limit": limit,
                },
            ).fetchall()
        return {
            "ok": True,
            "query": query,
            "language": lang,
            "count": len(rows),
            "results": [lkaat_summary(row) for row in rows],
        }

    def lkaat_details(self, code: str, language: str | None = "de") -> dict[str, Any]:
        lang = normalize_language(language)
        lk_lang = LANGUAGE_TO_LK[lang]
        normalized_code = code.strip().upper()
        if not normalized_code:
            raise LookupError("code must not be empty")
        with self._connect() as con:
            row = con.execute(
                """
                SELECT
                    l.LKN AS code,
                    t.SPRACHE AS source_language,
                    t.BEZ_255 AS title,
                    t.MED_INTERPRET AS medical_interpretation,
                    l.LEISTUNG_TYP AS service_type,
                    typ.BEZ_255 AS service_type_title,
                    l.SEITE AS side_required,
                    l.PROCEDURE_TYPE AS procedure_type,
                    l.USED_FOR_GROUPING AS used_for_grouping,
                    l.ASSIGNED_SERVICE_POSITION AS assigned_service_position,
                    l.GUELTIG_VON AS valid_from,
                    l.GUELTIG_BIS AS valid_to,
                    l.MUT_DAT AS modified_at
                FROM LK_LEISTUNG l
                LEFT JOIN LK_LEISTUNG_TEXT t ON t.LKN = l.LKN AND t.SPRACHE = :language
                LEFT JOIN LK_LEISTUNG_TYP typ ON typ.LEISTUNG_TYP = l.LEISTUNG_TYP AND typ.SPRACHE = :language
                WHERE l.LKN = :code OR replace(l.LKN, '.', '') = replace(:code, '.', '')
                ORDER BY l.LKN
                LIMIT 1
                """,
                {"code": normalized_code, "language": lk_lang},
            ).fetchone()
            if row is None:
                return {"ok": False, "error": "not_found", "code": code, "language": lang}
            hierarchy = con.execute(
                """
                SELECT LKN_MASTER AS parent_code, LKN_SLAVE AS child_code
                FROM LK_LEISTUNG_HIERARCHIE
                WHERE LKN_MASTER = :code OR LKN_SLAVE = :code
                ORDER BY LKN_MASTER, LKN_SLAVE
                LIMIT 100
                """,
                {"code": row["code"]},
            ).fetchall()
        detail = row_to_dict(row)
        detail["hierarchy"] = [row_to_dict(h) for h in hierarchy]
        return {"ok": True, "language": lang, "result": detail}

    def search_diagnoses(self, query: str, language: str | None = "de", limit: int = 20) -> dict[str, Any]:
        lang = normalize_language(language)
        limit = bounded_limit(limit)
        pattern = like_pattern(query)
        code_pattern = pattern.replace(".", "")
        with self._connect() as con:
            rows = con.execute(
                """
                WITH matches AS (
                    SELECT
                        c.code,
                        c.language,
                        c.kind,
                        c.label,
                        c.parent_code,
                        'code' AS source,
                        CASE
                            WHEN replace(c.code, '.', '') = replace(:query, '.', '') THEN 0
                            WHEN replace(c.code, '.', '') LIKE :code_pattern ESCAPE '\\' THEN 1
                            WHEN c.label LIKE :pattern ESCAPE '\\' THEN 2
                            ELSE 9
                        END AS rank
                    FROM ICD10_Code c
                    WHERE c.language = :language
                      AND (
                        replace(c.code, '.', '') LIKE :code_pattern ESCAPE '\\'
                        OR c.label LIKE :pattern ESCAPE '\\'
                      )
                    UNION ALL
                    SELECT
                        r.code,
                        r.language,
                        r.kind,
                        r.label,
                        NULL AS parent_code,
                        'rubric' AS source,
                        CASE
                            WHEN replace(r.code, '.', '') = replace(:query, '.', '') THEN 0
                            WHEN replace(r.code, '.', '') LIKE :code_pattern ESCAPE '\\' THEN 1
                            WHEN r.kind = 'preferred' THEN 2
                            ELSE 3
                        END AS rank
                    FROM ICD10_Rubric r
                    WHERE r.language = :language
                      AND (
                        replace(r.code, '.', '') LIKE :code_pattern ESCAPE '\\'
                        OR r.label LIKE :pattern ESCAPE '\\'
                      )
                )
                SELECT
                    code,
                    language,
                    GROUP_CONCAT(DISTINCT kind) AS kinds,
                    label,
                    MAX(parent_code) AS parent_code,
                    GROUP_CONCAT(DISTINCT source) AS sources,
                    MIN(rank) AS rank
                FROM matches
                GROUP BY code, language, label
                ORDER BY rank, code, label
                LIMIT :limit
                """,
                {
                    "query": query.strip(),
                    "pattern": pattern,
                    "code_pattern": code_pattern,
                    "language": lang,
                    "limit": limit,
                },
            ).fetchall()
        return {
            "ok": True,
            "query": query,
            "language": lang,
            "count": len(rows),
            "results": [row_to_dict(row) for row in rows],
        }


def bounded_limit(limit: int | str | None) -> int:
    if limit is None:
        return 20
    try:
        value = int(limit)
    except (TypeError, ValueError) as exc:
        raise LookupError("limit must be an integer") from exc
    return max(1, min(value, 100))


def lkaat_summary(row: sqlite3.Row) -> dict[str, Any]:
    result = row_to_dict(row)
    text = result.get("medical_interpretation")
    if isinstance(text, str) and len(text) > 400:
        result["medical_interpretation_excerpt"] = text[:397].rstrip() + "..."
        result.pop("medical_interpretation", None)
    return result
