import litellm
import dspy
import os
import json
from typing import List, Dict, Any
from pydantic import BaseModel

# Configure LiteLLM
litellm.drop_params = True

class RowGeneration(dspy.Signature):
    """Generate realistic synthetic seed rows for a database table."""
    table_name = dspy.InputField()
    columns = dspy.InputField()
    num_rows = dspy.InputField()
    context = dspy.InputField(desc="Domain context and constraints")
    rows = dspy.OutputField(desc="JSON array of generated rows")

class SchemaInference(dspy.Signature):
    """Extract a canonical SchemaSpec from raw schema artifacts."""
    raw_artifact = dspy.InputField(desc="SQL DDL, JSON Schema, or natural language description")
    schema_spec = dspy.OutputField(desc="JSON representation of SchemaSpec with columns, types, and constraints")

class DistributionExtractor(dspy.Signature):
    """Hypothesize likely statistical distributions for database columns."""
    table_context = dspy.InputField()
    column_name = dspy.InputField()
    column_semantic = dspy.InputField()
    distribution_prior = dspy.OutputField(desc="JSON with distribution type (Normal, Log-Normal, etc.) and parameters")

class SeedingEngine:
    def __init__(self, model: str = None):
        self.model = model or os.environ.get("LLM_DEFAULT_MODEL", "openai/gpt-4o-mini")
        # Initialize DSPy with LiteLLM
        lm = dspy.LM(f"openai/{self.model}")
        dspy.settings.configure(lm=lm)
        
    def infer_schema(self, raw_artifact: str) -> Dict[str, Any]:
        """Infer schema from raw source using LLM."""
        predictor = dspy.Predict(SchemaInference)
        response = predictor(raw_artifact=raw_artifact)
        return self._parse_json(response.schema_spec)

    def extract_priors(self, table_name: str, column: Dict[str, Any]) -> Dict[str, Any]:
        """Extract statistical priors for a column."""
        predictor = dspy.Predict(DistributionExtractor)
        response = predictor(
            table_context=table_name,
            column_name=column["name"],
            column_semantic=column.get("semantic_type", "unknown")
        )
        return self._parse_json(response.distribution_prior)

    def generate_seed_rows(self, table_name: str, columns: List[Dict[str, Any]], n: int, domain_context: str = "") -> List[Dict[str, Any]]:
        """Generate high-fidelity seed rows using DSPy."""
        predictor = dspy.Predict(RowGeneration)
        cols_str = json.dumps(columns, indent=2)
        response = predictor(
            table_name=table_name,
            columns=cols_str,
            num_rows=str(n),
            context=domain_context
        )
        return self._parse_json(response.rows)

    def _parse_json(self, content: str) -> Any:
        try:
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            return json.loads(content.strip())
        except Exception as e:
            print(f"Failed to parse LLM response: {e}")
            return {}

class ConstraintGraph:
    """Represents semantic relationships between tables and columns."""
    def __init__(self, schema: Dict[str, Any]):
        self.schema = schema
        self.graph = {}
        self._build_graph()
        
    def _build_graph(self):
        # Extract foreign keys and semantic dependencies
        for db in self.schema.get("databases", []):
            for table in db.get("tables", []):
                t_name = table["name"]
                self.graph[t_name] = {"dependencies": [], "columns": table.get("attributes", [])}
                
                for attr in table.get("attributes", []):
                    for const in attr.get("constraints", []):
                        if "FOREIGN KEY" in const.upper():
                            # Simplified parser
                            ref = const.split("REFERENCES")[-1].strip().split("(")[0].strip()
                            self.graph[t_name]["dependencies"].append(ref)

    def get_generation_order(self) -> List[str]:
        """Topological sort to determine generation order."""
        visited = set()
        stack = []
        
        def visit(node):
            if node not in visited:
                visited.add(node)
                for dep in self.graph.get(node, {}).get("dependencies", []):
                    if dep in self.graph:
                        visit(dep)
                stack.append(node)
                
        for node in self.graph:
            visit(node)
            
        return stack
