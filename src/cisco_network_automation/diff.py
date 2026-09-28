"""Semantic pre/post comparison for normalized network snapshots."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .models import DeviceSnapshot


def semantic_diff(before: DeviceSnapshot, after: DeviceSnapshot) -> dict[str, Any]:
    before_interfaces = before.interface_map()
    after_interfaces = after.interface_map()
    before_routes = before.route_map()
    after_routes = after.route_map()

    interface_changes = []
    for name in sorted(set(before_interfaces) | set(after_interfaces)):
        old = before_interfaces.get(name)
        new = after_interfaces.get(name)
        if old != new:
            interface_changes.append(
                {
                    "name": name,
                    "before": asdict(old) if old else None,
                    "after": asdict(new) if new else None,
                }
            )

    route_changes = []
    for prefix in sorted(set(before_routes) | set(after_routes)):
        old = before_routes.get(prefix)
        new = after_routes.get(prefix)
        if old != new:
            route_changes.append(
                {
                    "prefix": prefix,
                    "before": asdict(old) if old else None,
                    "after": asdict(new) if new else None,
                }
            )

    hostname_changed = before.hostname != after.hostname
    return {
        "hostname_changed": hostname_changed,
        "hostname": {"before": before.hostname, "after": after.hostname},
        "interfaces": interface_changes,
        "routes": route_changes,
        "change_count": (
            int(hostname_changed) + len(interface_changes) + len(route_changes)
        ),
    }
