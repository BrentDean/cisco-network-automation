from types import SimpleNamespace

import pytest

from cisco_network_automation.netconf import (
    HOSTNAME_FILTER,
    NetconfClient,
    NetconfSettings,
)


class FakeConnection:
    def __init__(self):
        self.server_capabilities = [
            "urn:ietf:params:netconf:base:1.0",
            "urn:ietf:params:netconf:capability:candidate:1.0",
            "urn:ietf:params:xml:ns:yang:ietf-yang-library?module=ietf-yang-library",
        ]
        self.session_id = 42
        self.get_config_calls = []

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
    assert connection.get_config_calls == [
        ("running", ("subtree", HOSTNAME_FILTER))
    ]


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
