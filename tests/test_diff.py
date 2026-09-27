from pathlib import Path

from cisco_network_automation.diff import semantic_diff
from cisco_network_automation.io import load_snapshot

ROOT = Path(__file__).parent.parent


def test_no_diff_for_identical_snapshots():
    snapshot = load_snapshot(ROOT / "tests/fixtures/baseline.json")
    result = semantic_diff(snapshot, snapshot)
    assert result["change_count"] == 0


def test_semantic_diff_detects_interface_and_route_changes():
    before = load_snapshot(ROOT / "tests/fixtures/baseline.json")
    after = load_snapshot(ROOT / "tests/fixtures/changed.json")
    result = semantic_diff(before, after)
    assert result["change_count"] == 2
    assert result["interfaces"][0]["name"] == "Loopback100"
    assert result["routes"][0]["prefix"] == "0.0.0.0/0"
