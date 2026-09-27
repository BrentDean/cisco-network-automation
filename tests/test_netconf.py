from types import SimpleNamespace

import pytest

from cisco_network_automation.netconf import (
    HOSTNAME_FILTER,
    NetconfClient,
    NetconfSettings,
    parse_interface_oper_xml,
)

INTERFACE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<data xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
  <interfaces xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-interfaces-oper">
    <interface>
      <name>GigabitEthernet1</name>
      <admin-status>if-state-up</admin-status>
      <oper-status>if-oper-state-ready</oper-status>
      <ipv4>10.10.20.48</ipv4>
      <ipv4-subnet-mask>255.255.255.0</ipv4-subnet-mask>
      <description>MANAGEMENT INTERFACE - DON'T TOUCH ME</description>
    </interface>
  </interfaces>
</data>
"""


class FakeConnection:
    def __init__(self):
        self.server_capabilities = [
            "urn:ietf:params:netconf:base:1.0",
            "urn:ietf:params:netconf:capability:candidate:1.0",
            "urn:ietf:params:xml:ns:yang:ietf-yang-library?module=ietf-yang-library",
        ]
        self.session_id = 42
        self.get_config_calls = []
        self.get_calls = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def get_config(self, *, source, filter):
        self.get_config_calls.append((source, filter))
        return SimpleNamespace(
            data_xml=(
                '<data xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">'
                '<native xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-native">'
                "<hostname>cat8000v</hostname>"
                "</native></data>"
            )
        )

    def get(self, *, filter):
        self.get_calls.append(filter)
        return SimpleNamespace(data_xml=INTERFACE_XML)


class FakeConnect:
    def __init__(self):
        self.calls = []
        self.connections = []

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        connection = FakeConnection()
        self.connections.append(connection)
        return connection


def settings(**kwargs):
    values = {
        "host": "10.10.20.48",
        "username": "developer",
        "password": "test",
        "hostkey_verify": False,
    }
    values.update(kwargs)
    return NetconfSettings(**values)


def test_netconf_hello_reports_capabilities():
    connect = FakeConnect()
    client = NetconfClient(settings(), connect=connect)

    report = client.hello()

    assert report == {
        "protocol": "netconf",
        "session_id": "42",
        "capability_count": 3,
        "supports_candidate": True,
        "supports_yang_library": True,
    }
    assert connect.calls[0]["device_params"] == {"name": "iosxe"}
    assert connect.calls[0]["port"] == 830
    assert connect.calls[0]["hostkey_verify"] is False


def test_netconf_hostname_uses_running_subtree_filter():
    connect = FakeConnect()
    client = NetconfClient(settings(), connect=connect)

    assert client.get_hostname() == "cat8000v"

    connection = connect.connections[0]
    assert connection.get_config_calls == [("running", ("subtree", HOSTNAME_FILTER))]


def test_parse_live_interface_xml_shape():
    state = parse_interface_oper_xml(INTERFACE_XML)

    assert state.name == "GigabitEthernet1"
    assert state.admin_up is True
    assert state.oper_up is True
    assert state.ipv4 == "10.10.20.48/24"
    assert state.description == "MANAGEMENT INTERFACE - DON'T TOUCH ME"


def test_netconf_interface_uses_operational_subtree_filter():
    connect = FakeConnect()
    client = NetconfClient(settings(), connect=connect)

    state = client.get_interface_state("GigabitEthernet1")

    assert state.ipv4 == "10.10.20.48/24"
    filter_type, filter_xml = connect.connections[0].get_calls[0]
    assert filter_type == "subtree"
    assert "<name>GigabitEthernet1</name>" in filter_xml
    assert "Cisco-IOS-XE-interfaces-oper" in filter_xml


def test_netconf_settings_fail_closed_for_missing_credentials(monkeypatch):
    monkeypatch.delenv("CISCO_HOST", raising=False)
    monkeypatch.delenv("CISCO_USERNAME", raising=False)
    monkeypatch.delenv("CISCO_PASSWORD", raising=False)

    with pytest.raises(RuntimeError, match="must be set"):
        NetconfSettings.from_env()


def test_netconf_hostkey_verification_defaults_true(monkeypatch):
    monkeypatch.setenv("CISCO_HOST", "10.10.20.48")
    monkeypatch.setenv("CISCO_USERNAME", "developer")
    monkeypatch.setenv("CISCO_PASSWORD", "test")
    monkeypatch.delenv("CISCO_NETCONF_HOSTKEY_VERIFY", raising=False)

    assert NetconfSettings.from_env().hostkey_verify is True
