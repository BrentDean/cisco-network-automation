"""Normalized network-state models used by collectors and validators."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class InterfaceState:
    name: str
    admin_up: bool
    oper_up: bool
    ipv4: str | None = None
    description: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "InterfaceState":
        return cls(
            name=str(data["name"]),
            admin_up=bool(data["admin_up"]),
            oper_up=bool(data["oper_up"]),
            ipv4=data.get("ipv4"),
            description=data.get("description"),
        )


@dataclass(frozen=True)
class RouteState:
    prefix: str
    next_hop: str | None = None
    protocol: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RouteState":
        return cls(
            prefix=str(data["prefix"]),
            next_hop=data.get("next_hop"),
            protocol=data.get("protocol"),
        )


@dataclass(frozen=True)
class DeviceSnapshot:
    hostname: str
    interfaces: tuple[InterfaceState, ...] = field(default_factory=tuple)
    routes: tuple[RouteState, ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DeviceSnapshot":
        return cls(
            hostname=str(data["hostname"]),
            interfaces=tuple(
                InterfaceState.from_dict(item) for item in data.get("interfaces", [])
            ),
            routes=tuple(RouteState.from_dict(item) for item in data.get("routes", [])),
            metadata=dict(data.get("metadata", {})),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def interface_map(self) -> dict[str, InterfaceState]:
        return {item.name: item for item in self.interfaces}

    def route_map(self) -> dict[str, RouteState]:
        return {item.prefix: item for item in self.routes}
