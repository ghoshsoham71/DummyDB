"""
Mock Data Generator — generates realistic seed data from a parsed schema
using Groq LLM. Sends table definitions to the LLM and receives back
structured JSON rows.

Requires the GROQ_API_KEY environment variable to be set.
"""

import csv
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

from src.utils.rate_limiter import (
    check_rate_limit,
    acquire_concurrency_slot,
    release_concurrency_slot,
    validate_request_size,
    RateLimitExceeded,
)

logger = logging.getLogger(__name__)

GROQ_API_URL = os.environ.get("LLM_API_URL", "https://api.groq.com/openai/v1/chat/completions")
DEFAULT_MODEL = os.environ.get("LLM_DEFAULT_MODEL", "openai/gpt-oss-120b")


# ── Prompt construction ───────────────────────────────────────────────────────

def _build_prompt(table_name: str, columns: List[Dict[str, str]], num_rows: int) -> str:
    """Build a prompt asking the LLM to generate rows for one table."""
    col_lines = []
    for col in columns:
        line = f"  - {col['name']} ({col['type']})"
        if col.get("constraints"):
            line += f"  [{', '.join(col['constraints'])}]"
        col_lines.append(line)

    return f"""Generate exactly {num_rows} rows of realistic sample data for the database table "{table_name}".

Columns:
{chr(10).join(col_lines)}

Rules:
- Return ONLY a JSON array of objects, one object per row.
- Each object must have all listed column names as keys.
- Values must match column data types (integers for INT, strings for VARCHAR, ISO dates for DATE/TIMESTAMP, etc.).
- For AUTO_INCREMENT / PRIMARY_KEY integer columns, use sequential IDs starting at 1.
- Make the data realistic and varied — use real-looking names, emails, addresses, prices, dates, etc.
- Do NOT wrap output in markdown fences or add any commentary — just the raw JSON array.
"""


def _parse_llm_json(raw: str) -> List[Dict[str, Any]]:
    """Extract a JSON array from the LLM response, tolerating markdown fences."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()
    return json.loads(text)


# ── Single-table generation ───────────────────────────────────────────────────

def _generate_table(
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
        raise ValueError(f"LLM did not return a JSON array for table '{table_name}'")

    logger.info(f"LLM generated {len(rows)} rows for table '{table_name}'")
    return rows


# ── Full-schema generation ────────────────────────────────────────────────────

def generate_mock_data(
    schema: Dict[str, Any],
    num_rows: Optional[Dict[str, int]] = None,
    default_rows: int = 10,
    skip_rate_limit: bool = False,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Generate mock data for every table in the schema using Groq LLM.

    Args:
        schema:          Parsed schema dict (has a 'databases' key).
        num_rows:        Optional per-table row counts, e.g. {"users": 20}.
        default_rows:    Fallback row count when a table is not in num_rows.
        skip_rate_limit:  Skip rate limiting (True when seed data is provided).

    Returns:
        Dict mapping table_name → list of row dicts.

    Raises:
        EnvironmentError: If GROQ_API_KEY is not set.
    """
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "GROQ_API_KEY environment variable is not set. "
            "Get a free key at https://console.groq.com/keys"
        )

    num_rows = num_rows or {}

    # Collect all tables
    all_tables = [
        table
        for database in schema.get("databases", [])
        for table in database.get("tables", [])
    ]

    # Rate-limit checks (before touching the LLM) — skip when seed data is provided
    if not skip_rate_limit:
        validate_request_size(len(all_tables), num_rows)
        check_rate_limit(client_id="generate", cost=len(all_tables))

    result: Dict[str, List[Dict[str, Any]]] = {}

    for table in all_tables:
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

        if not skip_rate_limit:
            if not acquire_concurrency_slot(timeout=60.0):
                raise RateLimitExceeded("Server too busy — try again shortly.")
        try:
            rows = _generate_table(table_name, columns, n, api_key)
            result[table_name] = rows
        except Exception as e:
            logger.error(f"LLM generation failed for table '{table_name}': {e}")
            raise
        finally:
            if not skip_rate_limit:
                release_concurrency_slot()

    return result


# ── Streaming generation (yields SSE events) ─────────────────────────────────

def generate_mock_data_streaming(
    schema: Dict[str, Any],
    num_rows: Optional[Dict[str, int]] = None,
    default_rows: int = 10,
    output_dir: str = "synthetic_data",
    skip_rate_limit: bool = False,
):
    """
    Generator that yields JSON-encoded SSE events as each table is produced.

    Event types:
      - {"event": "start", "total_tables": N}
      - {"event": "table_start", "table": name, "rows_requested": N, "index": i}
      - {"event": "table_done",  "table": name, "rows_generated": N, "index": i}
      - {"event": "error",       "table": name, "message": str}
      - {"event": "complete",    "file_paths": [...], "summary": {...}}
    """
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        yield json.dumps({"event": "error", "table": "", "message": "GROQ_API_KEY not set"})
        return

    num_rows = num_rows or {}
    all_tables = []
    for database in schema.get("databases", []):
        for table in database.get("tables", []):
            all_tables.append(table)

    # Rate-limit checks — skip when seed data is provided
    if not skip_rate_limit:
        try:
            validate_request_size(len(all_tables), num_rows)
            check_rate_limit(client_id="stream", cost=len(all_tables))
        except RateLimitExceeded as e:
            yield json.dumps({"event": "error", "table": "", "message": str(e)})
            return

    yield json.dumps({"event": "start", "total_tables": len(all_tables)})

    generated: Dict[str, List[Dict[str, Any]]] = {}

    for idx, table in enumerate(all_tables):
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

        yield json.dumps({
            "event": "table_start",
            "table": table_name,
            "rows_requested": n,
            "index": idx + 1,
            "total_tables": len(all_tables),
        })

        try:
            if not skip_rate_limit:
                if not acquire_concurrency_slot(timeout=60.0):
                    yield json.dumps({"event": "error", "table": table_name, "message": "Server too busy — try again shortly."})
                    continue
            try:
                rows = _generate_table(table_name, columns, n, api_key)
            finally:
                if not skip_rate_limit:
                    release_concurrency_slot()
            generated[table_name] = rows
            yield json.dumps({
                "event": "table_done",
                "table": table_name,
                "rows_generated": len(rows),
                "index": idx + 1,
                "total_tables": len(all_tables),
            })
        except Exception as e:
            logger.error(f"LLM generation failed for table '{table_name}': {e}")
            yield json.dumps({
                "event": "error",
                "table": table_name,
                "message": str(e),
            })

    # Save all generated data
    if generated:
        file_paths = save_mock_data_csv(generated, output_dir)
        summary = {
            t: {"rows": len(r), "columns": len(r[0]) if r else 0}
            for t, r in generated.items()
        }
        yield json.dumps({
            "event": "complete",
            "file_paths": file_paths,
            "summary": summary,
        })
    else:
        yield json.dumps({"event": "error", "table": "", "message": "No data generated"})


# ── CSV export ────────────────────────────────────────────────────────────────

def save_mock_data_csv(
    data: Dict[str, List[Dict[str, Any]]],
    output_dir: str,
) -> List[str]:
    """Save generated data to CSV files. Returns list of written file paths."""
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
