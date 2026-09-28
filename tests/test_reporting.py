from pathlib import Path

from cisco_network_automation.io import load_policy, load_snapshot
from cisco_network_automation.reporting import build_validation_report
from cisco_network_automation.validation import validate_snapshot

ROOT = Path(__file__).parent.parent


def test_report_passes_for_valid_snapshot():
    snapshot = load_snapshot(ROOT / "tests/fixtures/baseline.json")
    checks = validate_snapshot(
        snapshot,
        load_policy(ROOT / "policies/lab_policy.yaml"),
    )
    report = build_validation_report(snapshot, checks)
    assert report["result"] == "PASS"
    assert report["summary"]["failed"] == 0


def test_report_fails_for_drifted_snapshot():
    snapshot = load_snapshot(ROOT / "tests/fixtures/changed.json")
    checks = validate_snapshot(
        snapshot,
        load_policy(ROOT / "policies/lab_policy.yaml"),
    )
    report = build_validation_report(snapshot, checks)
    assert report["result"] == "FAIL"
    assert report["summary"]["failed"] >= 1
