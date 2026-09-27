from cisco_network_automation.restconf import (
    DEMO_DESCRIPTION,
    DEMO_LOOPBACK,
    YANG_JSON,
    YANG_PATCH_XML,
    RestconfClient,
    RestconfSettings,
)


class FakeResponse:
    def __init__(self, payload=None, status_code=200):
        self.payload = payload or {}
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            from requests import HTTPError
            raise HTTPError(f"status {self.status_code}")

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, responses=None):
        self.calls = []
        self.responses = list(responses or [])

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        if self.responses:
            return self.responses.pop(0)
        return FakeResponse({"Cisco-IOS-XE-native:hostname": "cat8kv"})


def settings(**kwargs):
    values = {"host": "10.10.20.48", "username": "developer", "password": "test"}
    values.update(kwargs)
    return RestconfSettings(**values)


def test_restconf_get_builds_expected_request():
    session = FakeSession()
    client = RestconfClient(settings(), session=session)
    client.get_hostname()
    method, url, kwargs = session.calls[0]
    assert method == "GET"
    assert url.endswith("/restconf/data/Cisco-IOS-XE-native:native/hostname")
    assert kwargs["headers"]["Accept"] == YANG_JSON


def test_writes_fail_closed_by_default():
    client = RestconfClient(settings(allow_writes=False), session=FakeSession())
    try:
        client.create_demo_loopback()
    except RuntimeError as exc:
        assert "writes disabled" in str(exc)
    else:
        raise AssertionError("expected write gate to fail closed")


def test_create_demo_loopback_uses_scoped_yang_patch_and_verifies():
    absent = FakeResponse(status_code=404)
    created = FakeResponse({"ietf-yang-patch:yang-patch-status": {"ok": [None]}})
    verified = FakeResponse({
        "Cisco-IOS-XE-native:Loopback": [{
            "name": DEMO_LOOPBACK,
            "description": DEMO_DESCRIPTION,
        }]
    })
    session = FakeSession([absent, created, verified])
    client = RestconfClient(settings(allow_writes=True), session=session)

    result = client.create_demo_loopback()

    assert result["verified"] is True
    method, url, kwargs = session.calls[1]
    assert method == "PATCH"
    assert url.endswith("/Cisco-IOS-XE-native:native/interface")
    assert kwargs["headers"]["Content-Type"] == YANG_PATCH_XML
    assert f"<target>/Loopback={DEMO_LOOPBACK}</target>" in kwargs["data"]
    assert "192.0.2.250" in kwargs["data"]


def test_create_refuses_existing_loopback():
    existing = FakeResponse({"Cisco-IOS-XE-native:Loopback": [{"name": DEMO_LOOPBACK}]})
    client = RestconfClient(settings(allow_writes=True), session=FakeSession([existing]))
    try:
        client.create_demo_loopback()
    except RuntimeError as exc:
        assert "already exists" in str(exc)
    else:
        raise AssertionError("expected existing interface refusal")


def test_delete_requires_demo_ownership_and_verifies_absence():
    owned = FakeResponse({
        "Cisco-IOS-XE-native:Loopback": [{
            "name": DEMO_LOOPBACK,
            "description": DEMO_DESCRIPTION,
        }]
    })
    deleted = FakeResponse(status_code=204)
    absent = FakeResponse(status_code=404)
    session = FakeSession([owned, deleted, absent])
    client = RestconfClient(settings(allow_writes=True), session=session)

    result = client.delete_demo_loopback()

    assert result["verified"] is True
    assert session.calls[1][0] == "DELETE"


def test_delete_refuses_unowned_loopback():
    other = FakeResponse({
        "Cisco-IOS-XE-native:Loopback": [{
            "name": DEMO_LOOPBACK,
            "description": "someone-else",
        }]
    })
    client = RestconfClient(settings(allow_writes=True), session=FakeSession([other]))
    try:
        client.delete_demo_loopback()
    except RuntimeError as exc:
        assert "not owned" in str(exc)
    else:
        raise AssertionError("expected ownership refusal")
