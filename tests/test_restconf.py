from cisco_network_automation.restconf import (
    YANG_JSON,
    RestconfClient,
    RestconfSettings,
)


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self):
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return FakeResponse({"Cisco-IOS-XE-native:hostname": "cat8kv"})


def test_restconf_get_builds_expected_request():
    session = FakeSession()
    client = RestconfClient(
        RestconfSettings(
            host="devnetsandboxiosxec8k.cisco.com",
            username="generated-user",
            password="generated-password",
        ),
        session=session,
    )

    payload = client.get_hostname()

    assert payload["Cisco-IOS-XE-native:hostname"] == "cat8kv"
    assert len(session.calls) == 1
    url, kwargs = session.calls[0]
    assert url == (
        "https://devnetsandboxiosxec8k.cisco.com:443/"
        "restconf/data/Cisco-IOS-XE-native:native/hostname"
    )
    assert kwargs["headers"]["Accept"] == YANG_JSON
    assert kwargs["verify"] is True
    assert kwargs["timeout"] == 15.0


def test_restconf_get_honors_disabled_tls_verification():
    session = FakeSession()
    client = RestconfClient(
        RestconfSettings(
            host="devnetsandboxiosxec8k.cisco.com",
            username="generated-user",
            password="generated-password",
            verify_tls=False,
        ),
        session=session,
    )

    client.get_hostname()

    _, kwargs = session.calls[0]
    assert kwargs["verify"] is False


def test_restconf_settings_require_credentials(monkeypatch):
    monkeypatch.delenv("CISCO_HOST", raising=False)
    monkeypatch.delenv("CISCO_USERNAME", raising=False)
    monkeypatch.delenv("CISCO_PASSWORD", raising=False)

    try:
        RestconfSettings.from_env()
    except RuntimeError as exc:
        assert "must be set" in str(exc)
    else:
        raise AssertionError("expected missing credentials to fail closed")


def test_restconf_settings_parse_tls_verification(monkeypatch):
    monkeypatch.setenv("CISCO_HOST", "devnetsandboxiosxec8k.cisco.com")
    monkeypatch.setenv("CISCO_USERNAME", "generated-user")
    monkeypatch.setenv("CISCO_PASSWORD", "generated-password")
    monkeypatch.setenv("CISCO_VERIFY_TLS", "false")

    settings = RestconfSettings.from_env()

    assert settings.verify_tls is False


def test_restconf_settings_reject_invalid_tls_value(monkeypatch):
    monkeypatch.setenv("CISCO_HOST", "devnetsandboxiosxec8k.cisco.com")
    monkeypatch.setenv("CISCO_USERNAME", "generated-user")
    monkeypatch.setenv("CISCO_PASSWORD", "generated-password")
    monkeypatch.setenv("CISCO_VERIFY_TLS", "sometimes")

    try:
        RestconfSettings.from_env()
    except RuntimeError as exc:
        assert "CISCO_VERIFY_TLS" in str(exc)
    else:
        raise AssertionError("expected invalid TLS setting to fail closed")
