"""Read-only pyATS/Genie collection for Cisco IOS XE."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CommonInterfaceState:
    name: str
    admin_up: bool
    oper_up: bool
    ipv4_address: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalize_genie_ip_interface_brief(
    parsed: dict[str, Any],
    name: str,
) -> CommonInterfaceState:
    """Normalize Genie 'show ip interface brief' output into common state."""
    interfaces = parsed.get("interface")
    if not isinstance(interfaces, dict):
        raise TypeError("Genie output is missing interface mapping")

    item = interfaces.get(name)
    if not isinstance(item, dict):
        raise ValueError(f"Genie output did not contain interface {name!r}")

    address = item.get("ip_address")
    ipv4_address = (
        address
        if isinstance(address, str) and address not in {"", "unassigned"}
        else None
    )

    return CommonInterfaceState(
        name=name,
        admin_up=item.get("status") == "up",
        oper_up=item.get("protocol") == "up",
        ipv4_address=ipv4_address,
    )


def common_from_model(state: Any) -> CommonInterfaceState:
    """Project a normalized InterfaceState into fields shared with Genie."""
    ipv4_address = None
    if isinstance(state.ipv4, str) and state.ipv4:
        ipv4_address = state.ipv4.split("/", 1)[0]

    return CommonInterfaceState(
        name=state.name,
        admin_up=state.admin_up,
        oper_up=state.oper_up,
        ipv4_address=ipv4_address,
    )


class PyatsClient:
    """Small read-only pyATS/Genie client using a YAML testbed."""

    def __init__(
        self,
        testbed_path: Path,
        *,
        loader: Any | None = None,
    ) -> None:
        if loader is None:
            from pyats.topology import loader as pyats_loader

            loader = pyats_loader
        self.testbed_path = testbed_path
        self.loader = loader

    def get_interface_state(self, device_name: str, interface_name: str) -> CommonInterfaceState:
        testbed = self.loader.load(str(self.testbed_path))
        device = testbed.devices[device_name]

        device.connect(log_stdout=False)
        try:
            parsed = device.parse("show ip interface brief")
        finally:
            device.disconnect()

        if not isinstance(parsed, dict):
            raise TypeError("Genie parser output must be a dictionary")

        return normalize_genie_ip_interface_brief(parsed, interface_name)
