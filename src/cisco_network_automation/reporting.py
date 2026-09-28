"""Structured validation evidence generation."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .models import DeviceSnapshot
from .validation import CheckResult


def build_validation_report(
    snapshot: DeviceSnapshot,
    checks: list[CheckResult],
    *,
    diff: dict[str, Any] | None = None,
) -> dict[str, Any]:
    passed = sum(item.passed for item in checks)
    failed = len(checks) - passed
    report: dict[str, Any] = {
        "generated_at": datetime.now(UTC).isoformat(),
        "device": snapshot.hostname,
        "result": "PASS" if failed == 0 else "FAIL",
        "summary": {"checks": len(checks), "passed": passed, "failed": failed},
        "checks": [item.to_dict() for item in checks],
    }
    if diff is not None:
        report["diff"] = diff
    return report
