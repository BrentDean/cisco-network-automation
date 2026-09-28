"""Read-only NETCONF/YANG client for Cisco IOS XE."""

from __future__ import annotations

import os
from dataclasses import dataclass
from ipaddress import IPv4Network
from typing import Any
from xml.etree import ElementTree

from ncclient import manager

from .models import InterfaceState

NATIVE_NS = "http://cisco.com/ns/yang/Cisco-IOS-XE-native"
INTERFACES_OPER_NS = "http://cisco.com/ns/yang/Cisco-IOS-XE-interfaces-oper"
HOSTNAME_FILTER = f'<native xmlns="{NATIVE_NS}"><hostname/></native>'


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default

    value = raw.strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False

    raise RuntimeError(f"{name} must be one of: true/false, 1/0, yes/no, on/off")


def _text(parent: ElementTree.Element, name: str) -> str | None:
    element = parent.find(f"{{{INTERFACES_OPER_NS}}}{name}")
    if element is None or element.text is None:
        return None
    value = element.text.strip()
    return value or None


def _ipv4_cidr(address: str | None, mask: str | None) -> str | None:
    if not address or not mask or address == "0.0.0.0" or mask == "0.0.0.0":
        return None
    try:
        prefix = IPv4Network(f"0.0.0.0/{mask}").prefixlen
    except ValueError as exc:
        raise ValueError(f"invalid NETCONF IPv4 subnet mask {mask!r}") from exc
    return f"{address}/{prefix}"


def parse_interface_oper_xml(xml: str) -> InterfaceState:
    """Normalize one IOS XE interfaces-oper NETCONF response."""
    root = ElementTree.fromstring(xml)
    interface = root.find(f".//{{{INTERFACES_OPER_NS}}}interface")
    if interface is None:
        raise ValueError("NETCONF response did not contain an operational interface")

    name = _text(interface, "name")
    if not name:
        raise ValueError("NETCONF interface response is missing name")

    description = _text(interface, "description")
    return InterfaceState(
        name=name,
        admin_up=_text(interface, "admin-status") == "if-state-up",
        oper_up=_text(interface, "oper-status") in {
            "if-oper-state-ready",
            "if-oper-state-up",
        },
        ipv4=_ipv4_cidr(
            _text(interface, "ipv4"),
            _text(interface, "ipv4-subnet-mask"),
        ),
        description=description,
    )


@dataclass(frozen=True)
class NetconfSettings:
    host: str
    username: str
    password: str
    port: int = 830
    hostkey_verify: bool = True
    timeout_seconds: int = 15

    @classmethod
    def from_env(cls) -> NetconfSettings:
        host = os.getenv("CISCO_HOST", "").strip()
        username = os.getenv("CISCO_USERNAME", "").strip()
        password = os.getenv("CISCO_PASSWORD", "")
        if not host or not username or not password:
            raise RuntimeError("CISCO_HOST, CISCO_USERNAME, and CISCO_PASSWORD must be set")

        return cls(
            host=host,
            username=username,
            password=password,
            port=int(os.getenv("CISCO_NETCONF_PORT", "830")),
            hostkey_verify=_env_bool("CISCO_NETCONF_HOSTKEY_VERIFY", True),
        )


class NetconfClient:
    """Small read-only IOS XE NETCONF client."""

    def __init__(self, settings: NetconfSettings, *, connect: Any = manager.connect) -> None:
        self.settings = settings
        self._connect = connect

    def _connection_args(self) -> dict[str, Any]:
        return {
            "host": self.settings.host,
            "port": self.settings.port,
            "username": self.settings.username,
            "password": self.settings.password,
            "hostkey_verify": self.settings.hostkey_verify,
            "device_params": {"name": "iosxe"},
            "allow_agent": False,
            "look_for_keys": False,
            "timeout": self.settings.timeout_seconds,
        }

    def hello(self) -> dict[str, Any]:
        with self._connect(**self._connection_args()) as connection:
            capabilities = sorted(str(item) for item in connection.server_capabilities)
            return {
                "protocol": "netconf",
                "session_id": str(connection.session_id),
                "capability_count": len(capabilities),
                "supports_candidate": any(
                    "urn:ietf:params:netconf:capability:candidate" in item
                    for item in capabilities
                ),
                "supports_yang_library": any("yang-library" in item for item in capabilities),
            }

    def get_hostname(self) -> str:
        with self._connect(**self._connection_args()) as connection:
            reply = connection.get_config(
                source="running",
                filter=("subtree", HOSTNAME_FILTER),
            )

        root = ElementTree.fromstring(reply.data_xml)
        hostname = root.find(f".//{{{NATIVE_NS}}}hostname")
        if hostname is None or hostname.text is None or not hostname.text.strip():
            raise ValueError("NETCONF response did not contain Cisco IOS XE native hostname")
        return hostname.text.strip()

    def get_interface_state(self, name: str) -> InterfaceState:
        filter_xml = (
            f'<interfaces xmlns="{INTERFACES_OPER_NS}">'
            f"<interface><name>{name}</name></interface>"
            "</interfaces>"
        )
        with self._connect(**self._connection_args()) as connection:
            reply = connection.get(filter=("subtree", filter_xml))
        state = parse_interface_oper_xml(reply.data_xml)
        if state.name != name:
            raise ValueError(
                f"NETCONF returned interface {state.name!r} while {name!r} was requested"
            )
        return state
