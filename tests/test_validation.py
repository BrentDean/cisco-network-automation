from pathlib import Path

from cisco_network_automation.io import load_policy, load_snapshot
from cisco_network_automation.validation import validate_snapshot

ROOT = Path(__file__).parent.parent


def test_baseline_matches_policy():
    snapshot = load_snapshot(ROOT / "tests/fixtures/baseline.json")
    policy = load_policy(ROOT / "policies/lab_policy.yaml")
    checks = validate_snapshot(snapshot, policy)
    assert checks
    assert all(check.passed for check in checks)


def test_changed_snapshot_fails_policy():
    snapshot = load_snapshot(ROOT / "tests/fixtures/changed.json")
    policy = load_policy(ROOT / "policies/lab_policy.yaml")
    checks = validate_snapshot(snapshot, policy)
    assert any(not check.passed for check in checks)
    assert {check.check for check in checks if not check.passed} >= {
        "interface:Loopback100:admin_up",
        "interface:Loopback100:oper_up",
        "route:0.0.0.0/0:present",
    }
