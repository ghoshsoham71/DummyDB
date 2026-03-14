import json
from typing import Dict, Any, List

def build_prompt(table_name: str, columns: List[Dict[str, str]], num_rows: int) -> str:
    lines = []
    for c in columns:
        l = f"  - {c['name']} ({c['type']})"
        if c.get("constraints"): l += f" [{', '.join(c['constraints'])}]"
        lines.append(l)
    return f"""Generate exactly {num_rows} rows of realistic sample data for "{table_name}".
Columns:
{chr(10).join(lines)}
Rules:
- Return ONLY a JSON array of objects.
- Realistic and varied data.
- No markdown fences or commentary.
"""

def parse_llm_json(raw: str) -> List[Dict[str, Any]]:
    t = raw.strip()
    if t.startswith("```"):
        lines = [l for l in t.split("\n") if not l.strip().startswith("```")]
        t = "\n".join(lines).strip()
    return json.loads(t)
