# api/src/utils/arrow_utils.py

import pandas as pd
import pyarrow as pa
from typing import BinaryIO, Union
import io

def df_to_arrow_bytes(df: pd.DataFrame) -> bytes:
    """Convert pandas DataFrame to Apache Arrow IPC bytes."""
    table = pa.Table.from_pandas(df)
    sink = pa.BufferOutputStream()
    with pa.ipc.new_file(sink, table.schema) as writer:
        writer.write_table(table)
    return sink.getvalue().to_pybytes()

def arrow_bytes_to_df(data: bytes) -> pd.DataFrame:
    """Convert Apache Arrow IPC bytes to pandas DataFrame."""
    reader = pa.ipc.open_file(io.BytesIO(data))
    return reader.read_all().to_pandas()

def save_df_to_arrow(df: pd.DataFrame, file_path_or_obj: Union[str, BinaryIO]):
    """Save pandas DataFrame as Arrow file."""
    table = pa.Table.from_pandas(df)
    with pa.ipc.new_file(file_path_or_obj, table.schema) as writer:
        writer.write_table(table)
