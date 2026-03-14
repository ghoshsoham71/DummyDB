import csv
import json
import logging
import os
from pathlib import Path
from typing import List
import httpx
from src.utils.rate_limiter import check_rate_limit, acquire_concurrency_slot, release_concurrency_slot, validate_request_size
from .mock.helpers import build_prompt, parse_llm_json

logger = logging.getLogger(__name__)
GROQ_URL = os.environ.get("LLM_API_URL", "https://api.groq.com/openai/v1/chat/completions")
MODEL = os.environ.get("LLM_DEFAULT_MODEL", "openai/gpt-oss-120b")

def _generate_table(name: str, cols: List[dict], n: int, key: str) -> List[dict]:
    p = build_prompt(name, cols, n)
    pay = {"model": MODEL, "messages": [{"role": "system", "content": "JSON array output only."}, {"role": "user", "content": p}], "temperature": 0.7}
    with httpx.Client(timeout=60.0) as c:
        r = c.post(GROQ_URL, headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, json=pay)
        r.raise_for_status()
    rows = parse_llm_json(r.json()["choices"][0]["message"]["content"])
    if not isinstance(rows, list): raise ValueError("Not a list")
    return rows

def generate_mock_data_streaming(schema: dict, num_rows: dict = None, default_rows: int = 10, output_dir: str = "synthetic_data", skip_rl: bool = False):
    key = os.environ.get("GROQ_API_KEY")
    if not key: yield json.dumps({"event": "error", "message": "Key not set"}); return
    num_rows = num_rows or {}
    tabs = [t for db in schema.get("databases", []) for t in db.get("tables", [])]
    if not skip_rl: validate_request_size(len(tabs), num_rows); check_rate_limit("stream", len(tabs))
    yield json.dumps({"event": "start", "total_tables": len(tabs)})
    gen = {}
    for idx, t in enumerate(tabs):
        name = t["name"]
        n = num_rows.get(name, default_rows)
        cols = [{"name": a["name"], "type": a.get("type", "VARCHAR"), "constraints": a.get("constraints", [])} for a in t.get("attributes", [])]
        yield json.dumps({"event": "table_start", "table": name, "index": idx + 1})
        try:
            if not skip_rl and not acquire_concurrency_slot(60.0): yield json.dumps({"event": "error", "message": "Busy"}); continue
            try: rows = _generate_table(name, cols, n, key)
            finally: 
                if not skip_rl: release_concurrency_slot()
            gen[name] = rows
            yield json.dumps({"event": "table_done", "table": name, "rows": len(rows)})
        except Exception as e: yield json.dumps({"event": "error", "message": str(e)})
    if gen:
        p = Path(output_dir); p.mkdir(parents=True, exist_ok=True)
        paths = []
        for tn, rs in gen.items():
            f = p / f"{tn}.csv"
            with open(f, "w", newline="", encoding="utf-8") as file:
                w = csv.DictWriter(file, fieldnames=rs[0].keys()); w.writeheader(); w.writerows(rs)
            paths.append(str(f))
        yield json.dumps({"event": "complete", "file_paths": paths})
