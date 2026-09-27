"""Normalize Cisco IOS XE RESTCONF responses into project state models."""

from __future__ import annotations

from ipaddress import IPv4Network
from typing import Any

from .models import DeviceSnapshot, InterfaceState
from .restconf import RestconfClient

INTERFACES_OPER_KEY = "Cisco-IOS-XE-interfaces-oper:interfaces"
HOSTNAME_KEY = "Cisco-IOS-XE-native:hostname"
VERSION_KEY = "Cisco-IOS-XE-native:version"

_OPER_UP_STATES = {
    "if-oper-state-ready",
    "if-oper-state-up",
}


def _scalar(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"RESTCONF response is missing string field {key!r}")
    return value


def _ipv4_cidr(address: Any, subnet_mask: Any) -> str | None:
    if not isinstance(address, str) or not isinstance(subnet_mask, str):
        return None
    if address == "0.0.0.0" or subnet_mask == "0.0.0.0":
        return None

    try:
        prefix_length = IPv4Network(f"0.0.0.0/{subnet_mask}").prefixlen
    except ValueError as exc:
        raise ValueError(f"invalid IPv4 subnet mask {subnet_mask!r}") from exc

    return f"{address}/{prefix_length}"


def normalize_interfaces_oper(payload: dict[str, Any]) -> tuple[InterfaceState, ...]:
    """Normalize IOS XE interfaces-oper data into deterministic interface state."""
    container = payload.get(INTERFACES_OPER_KEY)
    if not isinstance(container, dict):
        raise TypeError(f"RESTCONF response is missing {INTERFACES_OPER_KEY!r}")

    raw_interfaces = container.get("interface", [])
    if not isinstance(raw_interfaces, list):
        raise TypeError("interfaces-oper interface field must be a list")

    normalized: list[InterfaceState] = []
    for item in raw_interfaces:
        if not isinstance(item, dict):
            raise TypeError("interfaces-oper entries must be JSON objects")

        name = item.get("name")
        if not isinstance(name, str) or not name:
            raise ValueError("interface entry is missing a valid name")

        description = item.get("description")
        normalized.append(
            InterfaceState(
                name=name,
                admin_up=item.get("admin-status") == "if-state-up",
                oper_up=item.get("oper-status") in _OPER_UP_STATES,
                ipv4=_ipv4_cidr(
                    item.get("ipv4"),
                    item.get("ipv4-subnet-mask"),
                ),
                description=description if isinstance(description, str) and description else None,
            )
        )

    return tuple(normalized)


def build_device_snapshot(
    hostname_payload: dict[str, Any],
    version_payload: dict[str, Any],
    interfaces_payload: dict[str, Any],
) -> DeviceSnapshot:
    """Build a normalized snapshot from the first live RESTCONF collection set."""
    hostname = _scalar(hostname_payload, HOSTNAME_KEY)
    version = _scalar(version_payload, VERSION_KEY)
    interfaces = normalize_interfaces_oper(interfaces_payload)

    return DeviceSnapshot(
        hostname=hostname,
        interfaces=interfaces,
        metadata={
            "source": "restconf",
            "ios_xe_version": version,
            "interface_model": INTERFACES_OPER_KEY,
            "interface_count": len(interfaces),
        },
    )


def capture_device_snapshot(client: RestconfClient) -> DeviceSnapshot:
    """Collect a read-only normalized snapshot from an IOS XE device."""
    return build_device_snapshot(
        client.get_hostname(),
        client.get_version(),
        client.get_interfaces_oper(),
    )
