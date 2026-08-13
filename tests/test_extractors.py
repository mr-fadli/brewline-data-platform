# tests/test_extractors.py
import pandas as pd
from pathlib import Path
from brewline.extractors import extract_csv, extract_json


def test_extract_csv_preserves_string_types(tmp_path: Path):
    """Bronze should not infer types -- large digit strings (like tracking
    numbers) must survive as strings, not get silently coerced to int/float
    and lose precision or overflow."""
    csv = tmp_path / "orders.csv"
    csv.write_text("id,tracking_number\n1,12345678901234567890")
    df = extract_csv(csv)
    value = df["tracking_number"].iloc[0]
    assert isinstance(value, str)
    assert value == "12345678901234567890"  # exact match -- proves no precision was lost


def test_extract_json_handles_nested_data(tmp_path: Path):
    """Nested fields should stay nested in bronze."""
    json_file = tmp_path / "orders.json"
    json_file.write_text('[{"id": 1, "line_items": [{"sku": "COF-001"}]}]')
    df = extract_json(json_file)
    assert isinstance(df["line_items"].iloc[0], list)


def test_extract_json_returns_empty_dataframe_for_empty_array(tmp_path: Path):
    """extractors themselves don't raise on empty input -- that check
    belongs to ingest.py's orchestrator (run()), which explicitly rejects
    an empty extraction result before loading it to bronze."""
    json_file = tmp_path / "empty.json"
    json_file.write_text("[]")
    df = extract_json(json_file)
    assert len(df) == 0
