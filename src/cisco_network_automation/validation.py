"""Deterministic validation of normalized network state."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .models import DeviceSnapshot


@dataclass(frozen=True)
class CheckResult:
    check: str
    passed: bool
    expected: Any
    observed: Any
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def validate_snapshot(
    snapshot: DeviceSnapshot,
    policy: dict[str, Any],
) -> list[CheckResult]:
    results: list[CheckResult] = []

    if "hostname" in policy:
        expected = policy["hostname"]
        results.append(
            CheckResult(
                "hostname",
                snapshot.hostname == expected,
                expected,
                snapshot.hostname,
                "device hostname matches policy",
            )
        )

    interfaces = snapshot.interface_map()
    for expected in policy.get("interfaces", []):
        name = str(expected["name"])
        observed = interfaces.get(name)
        results.append(
            CheckResult(
                f"interface:{name}:present",
                observed is not None,
                True,
                observed is not None,
                "required interface is present"
                if observed
                else "required interface is missing",
            )
        )
        if observed is None:
            continue
        for field in ("admin_up", "oper_up", "ipv4", "description"):
            if field in expected:
                value = getattr(observed, field)
                results.append(
                    CheckResult(
                        f"interface:{name}:{field}",
                        value == expected[field],
                        expected[field],
                        value,
                        f"{field} matches policy",
                    )
                )

    routes = snapshot.route_map()
    for expected in policy.get("routes", []):
        prefix = str(expected["prefix"])
        present = bool(expected.get("present", True))
        observed = routes.get(prefix)
        results.append(
            CheckResult(
                f"route:{prefix}:present",
                (observed is not None) == present,
                present,
                observed is not None,
                "route presence matches policy",
            )
        )
        if observed is None or not present:
            continue
        for field in ("next_hop", "protocol"):
            if field in expected:
                value = getattr(observed, field)
                results.append(
                    CheckResult(
                        f"route:{prefix}:{field}",
                        value == expected[field],
                        expected[field],
                        value,
                        f"{field} matches policy",
                    )
                )

    return results
