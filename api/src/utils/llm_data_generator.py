"""
LLM-powered seed data generator using Groq API.

Generates contextually rich, realistic mock data by sending the parsed
schema to a Groq-hosted LLM and asking it to return rows as JSON.
Falls back to the Faker-based generator if the API key is missing or
the request fails.
"""

import csv
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = "llama-3.3-70b-versatile"


def _get_api_key() -> Optional[str]:
    return os.environ.get("GROQ_API_KEY")


def _build_prompt(table_name: str, columns: List[Dict[str, str]], num_rows: int) -> str:
    """Build a prompt asking the LLM to generate rows for one table."""
    col_descriptions = []
    for col in columns:
        desc = f"  - {col['name']} ({col['type']})"
        if col.get("constraints"):
            desc += f"  [{', '.join(col['constraints'])}]"
        col_descriptions.append(desc)
    col_block = "\n".join(col_descriptions)

    return f"""Generate exactly {num_rows} rows of realistic sample data for the database table "{table_name}".

Columns:
{col_block}

Rules:
- Return ONLY a JSON array of objects, one object per row.
- Each object must contain all the listed column names as keys.
- Values must match the column data types (e.g. integers for INT, strings for VARCHAR, ISO dates for DATE/TIMESTAMP).
- For AUTO_INCREMENT / PRIMARY_KEY integer columns, use sequential IDs starting at 1.
- Make the data realistic and varied — use real-looking names, emails, addresses, dates, etc.
- Do NOT include any markdown fences, commentary, or explanation — just the raw JSON array.
"""


def _parse_llm_json(raw: str) -> List[Dict[str, Any]]:
    """Extract a JSON array from the LLM response, tolerating markdown fences."""
    text = raw.strip()
    # Strip ```json ... ``` wrappers
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()
    return json.loads(text)


def generate_table_with_llm(
    table_name: str,
    columns: List[Dict[str, str]],
    num_rows: int,
    api_key: str,
    model: str = DEFAULT_MODEL,
) -> List[Dict[str, Any]]:
    """Call Groq LLM to generate rows for a single table."""
    prompt = _build_prompt(table_name, columns, num_rows)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You are a database seed-data generator. You output ONLY valid JSON arrays.",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 4096,
    }

    with httpx.Client(timeout=60.0) as client:
        resp = client.post(GROQ_API_URL, headers=headers, json=payload)
        resp.raise_for_status()

    data = resp.json()
    raw_content = data["choices"][0]["message"]["content"]
    rows = _parse_llm_json(raw_content)

    if not isinstance(rows, list):
        raise ValueError("LLM did not return a JSON array")

    logger.info(f"LLM generated {len(rows)} rows for table '{table_name}'")
    return rows


def generate_with_llm(
    schema: Dict[str, Any],
    num_rows: Optional[Dict[str, int]] = None,
    default_rows: int = 10,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Generate mock data for all tables using Groq LLM.

    Raises if the GROQ_API_KEY env var is not set.
    Individual table failures are logged and skipped (returns partial results).
    """
    api_key = _get_api_key()
    if not api_key:
        raise EnvironmentError("GROQ_API_KEY environment variable is not set")

    num_rows = num_rows or {}
    result: Dict[str, List[Dict[str, Any]]] = {}

    for database in schema.get("databases", []):
        for table in database.get("tables", []):
            table_name = table["name"]
            n = num_rows.get(table_name, default_rows)
            columns = [
                {
                    "name": attr["name"],
                    "type": attr.get("type", "VARCHAR"),
                    "constraints": attr.get("constraints", []),
                }
                for attr in table.get("attributes", [])
            ]

            try:
                rows = generate_table_with_llm(table_name, columns, n, api_key)
                result[table_name] = rows
            except Exception as e:
                logger.error(f"LLM generation failed for table '{table_name}': {e}")
                # Continue — caller can fall back to Faker for missing tables

    return result


def save_llm_data_csv(
    data: Dict[str, List[Dict[str, Any]]],
    output_dir: str,
) -> List[str]:
    """Save LLM-generated data to CSV files. Returns list of written paths."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths: List[str] = []

    for table_name, rows in data.items():
        if not rows:
            continue
        filepath = out / f"{table_name}_synthetic.csv"
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        paths.append(str(filepath))
        logger.info(f"Saved {len(rows)} rows → {filepath}")

    return paths
