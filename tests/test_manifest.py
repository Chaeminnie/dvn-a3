"""Manifest and data package are consistent with each other and with the app."""

import re
from pathlib import Path

import pandas as pd
import yaml

from src import config, data

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = yaml.safe_load((ROOT / "dashboard.yml").read_text(encoding="utf-8"))


def test_data_package_validates() -> None:
    assert data.validate() == []


def test_datasets_match_manifest() -> None:
    for spec in MANIFEST["datasets"]:
        frame = pd.read_csv(ROOT / spec["sample"])
        assert len(frame) >= spec["minimum_rows"], spec["id"]
        assert set(spec["columns"]) == set(frame.columns), spec["id"]
        assert not frame.duplicated(spec["primary_key"]).any(), spec["id"]
        for name, col in spec["columns"].items():
            if "allowed_values" in col:
                assert set(frame[name].dropna()) <= set(col["allowed_values"]), (spec["id"], name)
            if "minimum" in col:
                assert frame[name].min() >= col["minimum"], (spec["id"], name)
                assert frame[name].max() <= col["maximum"], (spec["id"], name)


def test_view_containers_and_control_defaults_match_app(monkeypatch) -> None:
    from streamlit.testing.v1 import AppTest

    monkeypatch.setenv("DASHBOARD_SAMPLE_MODE", "1")
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
    assert not app.exception
    views_source = (ROOT / "src" / "views.py").read_text(encoding="utf-8")
    for view in MANIFEST["views"]:
        assert f'key="{view["id"]}"' in views_source, view["id"]
        for control in view["controls"]:
            assert control["key"] in app.session_state, control["key"]
            actual = app.session_state[control["key"]]
            expected = control["default_value"]
            if isinstance(actual, tuple):
                actual, expected = list(actual), list(expected)
            assert actual == expected, (control["key"], actual, expected)
    assert "DASHBOARD_SAMPLE_MODE" in (ROOT / "app.py").read_text(encoding="utf-8")


def test_hardcoded_dates_match_data_files() -> None:
    prices = pd.read_csv(ROOT / "data" / "source" / "prices.csv")
    api = pd.read_csv(ROOT / "data" / "source" / "api_token_counts_raw.csv")
    assert set(prices["collected_on"]) == {config.LAST_REFRESH}
    assert set(api["collected_at"].str[:10]) == {config.TOKEN_COUNTS_RUN}
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", config.FLORES_RETRIEVED)


def test_every_source_is_declared_and_used() -> None:
    declared = {s["id"] for s in MANIFEST["sources"]}
    used = {sid for d in MANIFEST["datasets"] for sid in d["source_ids"]}
    used |= {sid for v in MANIFEST["views"] for sid in v["source_ids"]}
    assert used <= declared
    assert declared <= used
