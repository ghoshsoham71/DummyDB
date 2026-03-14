import pytest
import pandas as pd
import pyarrow as pa
from src.utils.arrow_utils import save_data_arrow, read_data_arrow
from src.utils.seeding_engine import ConstraintGraph
from src.utils.quality_engine import QualityEngine

def test_arrow_serialization(tmp_path):
    data = {"users": [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]}
    out_dir = tmp_path / "data"
    paths = save_data_arrow(data, str(out_dir), format="csv")
    
    assert len(paths) == 1
    table = read_data_arrow(paths[0])
    assert table.num_rows == 2
    assert "name" in table.column_names

def test_constraint_graph():
    schema = {
        "databases": [{
            "tables": [
                {"name": "users", "attributes": [{"name": "id", "constraints": ["PRIMARY KEY"]}]},
                {"name": "posts", "attributes": [{"name": "user_id", "constraints": ["FOREIGN KEY REFERENCES users(id)"]}]}
            ]
        }]
    }
    cg = ConstraintGraph(schema)
    order = cg.get_generation_order()
    assert order == ["users", "posts"]

def test_quality_engine():
    real = pd.Series(["A", "A", "B"])
    synth = pd.Series(["A", "B", "B"])
    qe = QualityEngine()
    tvd = qe.calculate_tvd(real, synth)
    assert 0 <= tvd <= 1
