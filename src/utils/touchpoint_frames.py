"""Parse uploaded touchpoint files with identifier columns kept as text (#66).

pandas infers ``10423``, ``00123`` or a GA4 ``user_pseudo_id`` like
``1234567890.1709280000`` as numbers. As numbers, leading zeros and trailing
digits are lost, and a float ``customer_id`` fails the Touchpoint model, so the
journey builder dropped those rows without an error. Identifier columns are
read as strings instead. Header matching is case-insensitive, like the rest of
the upload path.
"""

import io

import pandas as pd

ID_COLUMNS = ("customer_id", "session_id", "campaign_id", "creative_id", "email")


def _as_text(series: pd.Series) -> pd.Series:
    return series.map(lambda value: value if pd.isna(value) else str(value)).astype(object)


def read_touchpoint_frame(content: bytes, extension: str, *, json_lines_first: bool = True) -> pd.DataFrame:
    """Read CSV, JSON (array or lines) or Parquet bytes; ID columns as str.

    Only identifier columns change type; every other column is inferred as
    before. ``json_lines_first`` keeps each caller's existing JSON order (v2
    tries JSON Lines first, v1 reads a JSON document).
    """
    if extension == "csv":
        header = pd.read_csv(io.BytesIO(content), nrows=0).columns
        dtype = {column: str for column in header if str(column).lower() in ID_COLUMNS}
        return pd.read_csv(io.BytesIO(content), dtype=dtype)
    if extension == "json":
        dtype = {column: str for column in ID_COLUMNS}
        if json_lines_first:
            try:
                frame = pd.read_json(io.BytesIO(content), lines=True, dtype=dtype)
            except ValueError:
                frame = pd.read_json(io.BytesIO(content), dtype=dtype)
        else:
            frame = pd.read_json(io.BytesIO(content), dtype=dtype)
    elif extension == "parquet":
        frame = pd.read_parquet(io.BytesIO(content))
    else:
        raise ValueError(f"Unsupported file format: {extension}")
    for column in frame.columns:
        if str(column).lower() in ID_COLUMNS:
            frame[column] = _as_text(frame[column])
    return frame
