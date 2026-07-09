"""Import BFS ICD-10/CIM-10 ClaML files into a minimal multilingual schema."""
from __future__ import annotations

import sqlite3
from pathlib import Path
import xml.etree.ElementTree as ET

from .sqlite_copy import quote_identifier, require_file

XML_NS = "{http://www.w3.org/XML/1998/namespace}"


def ensure_icd10_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ICD10_Code (
            code TEXT NOT NULL,
            language TEXT NOT NULL,
            kind TEXT,
            label TEXT,
            parent_code TEXT,
            PRIMARY KEY (code, language)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ICD10_Rubric (
            code TEXT NOT NULL,
            language TEXT NOT NULL,
            kind TEXT NOT NULL,
            label TEXT NOT NULL
        )
        """
    )


def import_icd10_claml(source_file: Path, output_db: Path, *, language: str) -> int:
    require_file(source_file, f"ICD-10 ClaML {language}")
    output_db.parent.mkdir(parents=True, exist_ok=True)
    tree = ET.parse(source_file)
    root = tree.getroot()
    classes = root.findall(".//Class")

    with sqlite3.connect(output_db) as conn:
        ensure_icd10_schema(conn)
        conn.execute("DELETE FROM ICD10_Code WHERE language = ?", (language,))
        conn.execute("DELETE FROM ICD10_Rubric WHERE language = ?", (language,))
        imported = 0
        for class_element in classes:
            code = class_element.attrib.get("code")
            if not code:
                continue
            kind = class_element.attrib.get("kind")
            parent = class_element.find("SuperClass")
            parent_code = parent.attrib.get("code") if parent is not None else None
            rubrics = extract_rubrics(class_element, language)
            preferred = next((label for rubric_kind, label in rubrics if rubric_kind == "preferred"), None)
            if preferred is None and rubrics:
                preferred = rubrics[0][1]
            conn.execute(
                """
                INSERT OR REPLACE INTO ICD10_Code (code, language, kind, label, parent_code)
                VALUES (?, ?, ?, ?, ?)
                """,
                (code, language, kind, preferred, parent_code),
            )
            conn.executemany(
                "INSERT INTO ICD10_Rubric (code, language, kind, label) VALUES (?, ?, ?, ?)",
                [(code, language, rubric_kind, label) for rubric_kind, label in rubrics],
            )
            imported += 1
        conn.commit()
    return imported


def extract_rubrics(class_element: ET.Element, language: str) -> list[tuple[str, str]]:
    rubrics: list[tuple[str, str]] = []
    for rubric in class_element.findall("Rubric"):
        kind = rubric.attrib.get("kind", "unknown")
        labels = rubric.findall("Label")
        selected_label = None
        for label in labels:
            label_lang = label.attrib.get(f"{XML_NS}lang")
            if label_lang is None or label_lang.lower().startswith(language.lower()):
                selected_label = "".join(label.itertext()).strip()
                break
        if selected_label:
            rubrics.append((kind, selected_label))
    return rubrics


def create_compatibility_views(output_db: Path) -> None:
    """Create stable ICD10_* views for simple querying."""
    with sqlite3.connect(output_db) as conn:
        conn.execute("DROP VIEW IF EXISTS ICD10_Preferred")
        conn.execute(
            """
            CREATE VIEW ICD10_Preferred AS
            SELECT code, language, label, parent_code
            FROM ICD10_Code
            """
        )
        conn.commit()
