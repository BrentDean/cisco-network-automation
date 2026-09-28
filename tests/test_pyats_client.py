from types import SimpleNamespace

import pytest

from cisco_network_automation.models import InterfaceState
from cisco_network_automation.pyats_client import (
    CommonInterfaceState,
    PyatsClient,
    common_from_model,
    normalize_genie_ip_interface_brief,
)

PARSED = {
    "interface": {
        "GigabitEthernet1": {
            "ip_address": "10.10.20.48",
            "interface_is_ok": "YES",
            "method": "NVRAM",
            "status": "up",
            "protocol": "up",
        },
        "GigabitEthernet2": {
            "ip_address": "unassigned",
            "interface_is_ok": "YES",
            "method": "NVRAM",
            "status": "administratively down",
            "protocol": "down",
        },
    }
}


class FakeDevice:
    def __init__(self):
        self.connected = False
        self.disconnected = False
        self.commands = []

    def connect(self, **kwargs):
        assert kwargs == {"log_stdout": False}
        self.connected = True

    def parse(self, command):
        self.commands.append(command)
        return PARSED

    def disconnect(self):
        self.disconnected = True


class FakeLoader:
    def __init__(self):
        self.device = FakeDevice()

    def load(self, path):
        assert path.endswith("pyats_testbed.example.yaml")
        return SimpleNamespace(devices={"cat8000v": self.device})


def test_normalize_genie_live_shape():
    state = normalize_genie_ip_interface_brief(PARSED, "GigabitEthernet1")

    assert state == CommonInterfaceState(
        name="GigabitEthernet1",
        admin_up=True,
        oper_up=True,
        ipv4_address="10.10.20.48",
    )


def test_normalize_genie_unassigned_and_admin_down():
    state = normalize_genie_ip_interface_brief(PARSED, "GigabitEthernet2")

    assert state.admin_up is False
    assert state.oper_up is False
    assert state.ipv4_address is None


def test_pyats_client_connects_parses_and_disconnects(tmp_path):
    loader = FakeLoader()
    path = tmp_path / "pyats_testbed.example.yaml"
    path.write_text("devices: {}", encoding="utf-8")

    state = PyatsClient(path, loader=loader).get_interface_state(
        "cat8000v",
        "GigabitEthernet1",
    )

    assert state.ipv4_address == "10.10.20.48"
    assert loader.device.connected is True
    assert loader.device.disconnected is True
    assert loader.device.commands == ["show ip interface brief"]


def test_common_from_model_removes_prefix_length():
    state = InterfaceState(
        name="GigabitEthernet1",
        admin_up=True,
        oper_up=True,
        ipv4="10.10.20.48/24",
        description="ignored in common projection",
    )

    assert common_from_model(state) == CommonInterfaceState(
        name="GigabitEthernet1",
        admin_up=True,
        oper_up=True,
        ipv4_address="10.10.20.48",
    )


def test_normalize_genie_rejects_missing_interface():
    with pytest.raises(TypeError, match="did not contain interface mapping"):
        normalize_genie_ip_interface_brief(PARSED, "Loopback250")
