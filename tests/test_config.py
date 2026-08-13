# tests/test_config.py
from brewline.config import SOURCES


def test_all_sources_have_required_fields():
    required = {"name", "format", "load_strategy"}
    for source in SOURCES:
        assert required.issubset(source.keys()), f"{source['name']} missing fields"


def test_load_strategies_are_valid():
    valid = {"append", "snapshot"}
    for source in SOURCES:
        assert source["load_strategy"] in valid, f"{source['name']} has invalid strategy"