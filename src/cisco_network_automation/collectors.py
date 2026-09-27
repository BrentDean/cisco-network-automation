"""Normalize Cisco IOS XE RESTCONF responses into project state models."""

from __future__ import annotations

from ipaddress import IPv4Network
from typing import Any

from .models import DeviceSnapshot, InterfaceState, RouteState
from .restconf import RestconfClient

INTERFACES_OPER_KEY = "Cisco-IOS-XE-interfaces-oper:interfaces"
ROUTING_INSTANCE_KEY = "ietf-routing:routing-instance"
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


def _normalized_protocol(value: Any) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    return value.rsplit(":", 1)[-1]


def _route_next_hop(route: dict[str, Any]) -> str | None:
    next_hop = route.get("next-hop")
    if not isinstance(next_hop, dict):
        return None

    address = next_hop.get("next-hop-address")
    if isinstance(address, str) and address not in {"", "0.0.0.0", "::"}:
        return address

    extension_hops = next_hop.get("cisco-xe-ietf-routing-ext:next-hop-list")
    if isinstance(extension_hops, list):
        for hop in extension_hops:
            if not isinstance(hop, dict):
                continue
            address = hop.get("next-hop-address")
            if isinstance(address, str) and address not in {"", "0.0.0.0", "::"}:
                return address

    return None


def normalize_routing_state(payload: dict[str, Any]) -> tuple[RouteState, ...]:
    """Normalize IETF routing-state RIB entries into deterministic route state."""
    instances = payload.get(ROUTING_INSTANCE_KEY)
    if not isinstance(instances, list):
        raise TypeError(f"RESTCONF response is missing {ROUTING_INSTANCE_KEY!r}")

    normalized: list[RouteState] = []
    for instance in instances:
        if not isinstance(instance, dict):
            raise TypeError("routing-instance entries must be JSON objects")

        ribs_container = instance.get("ribs", {})
        if not isinstance(ribs_container, dict):
            raise TypeError("routing-instance ribs field must be a JSON object")

        ribs = ribs_container.get("rib", [])
        if not isinstance(ribs, list):
            raise TypeError("routing-instance ribs.rib field must be a list")

        for rib in ribs:
            if not isinstance(rib, dict):
                raise TypeError("rib entries must be JSON objects")

            routes_container = rib.get("routes", {})
            if not isinstance(routes_container, dict):
                raise TypeError("rib routes field must be a JSON object")

            routes = routes_container.get("route", [])
            if not isinstance(routes, list):
                raise TypeError("rib routes.route field must be a list")

            for route in routes:
                if not isinstance(route, dict):
                    raise TypeError("route entries must be JSON objects")

                prefix = route.get("destination-prefix")
                if not isinstance(prefix, str) or not prefix:
                    raise ValueError("route entry is missing destination-prefix")

                normalized.append(
                    RouteState(
                        prefix=prefix,
                        next_hop=_route_next_hop(route),
                        protocol=_normalized_protocol(route.get("source-protocol")),
                    )
                )

    return tuple(normalized)


def build_device_snapshot(
    hostname_payload: dict[str, Any],
    version_payload: dict[str, Any],
    interfaces_payload: dict[str, Any],
    routing_payload: dict[str, Any],
) -> DeviceSnapshot:
    """Build a normalized snapshot from live read-only RESTCONF collection."""
    hostname = _scalar(hostname_payload, HOSTNAME_KEY)
    version = _scalar(version_payload, VERSION_KEY)
    interfaces = normalize_interfaces_oper(interfaces_payload)
    routes = normalize_routing_state(routing_payload)

    return DeviceSnapshot(
        hostname=hostname,
        interfaces=interfaces,
        routes=routes,
        metadata={
            "source": "restconf",
            "ios_xe_version": version,
            "interface_model": INTERFACES_OPER_KEY,
            "interface_count": len(interfaces),
            "routing_model": ROUTING_INSTANCE_KEY,
            "route_count": len(routes),
        },
    )


def capture_device_snapshot(client: RestconfClient) -> DeviceSnapshot:
    """Collect a read-only normalized snapshot from an IOS XE device."""
    return build_device_snapshot(
        client.get_hostname(),
        client.get_version(),
        client.get_interfaces_oper(),
        client.get_routing_state(),
    )
