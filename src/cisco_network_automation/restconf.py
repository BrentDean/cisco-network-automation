"""RESTCONF client for Cisco IOS XE read-only collection and guarded demo changes."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from requests import Session
from requests.auth import HTTPBasicAuth
from requests.exceptions import HTTPError

YANG_JSON = "application/yang-data+json"
YANG_PATCH_XML = "application/yang-patch+xml"
DEMO_LOOPBACK = 250
DEMO_ADDRESS = "192.0.2.250"
DEMO_MASK = "255.255.255.255"
DEMO_DESCRIPTION = "portfolio-change-validation"


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


@dataclass(frozen=True)
class RestconfSettings:
    host: str
    username: str
    password: str
    port: int = 443
    verify_tls: bool = True
    timeout_seconds: float = 15.0
    allow_writes: bool = False

    @classmethod
    def from_env(cls) -> RestconfSettings:
        host = os.getenv("CISCO_HOST", "").strip()
        username = os.getenv("CISCO_USERNAME", "").strip()
        password = os.getenv("CISCO_PASSWORD", "")
        if not host or not username or not password:
            raise RuntimeError("CISCO_HOST, CISCO_USERNAME, and CISCO_PASSWORD must be set")
        return cls(
            host=host,
            username=username,
            password=password,
            port=int(os.getenv("CISCO_RESTCONF_PORT", "443")),
            verify_tls=_env_bool("CISCO_VERIFY_TLS", True),
            allow_writes=_env_bool("CISCO_ALLOW_WRITES", False),
        )


class RestconfClient:
    def __init__(self, settings: RestconfSettings, *, session: Session | None = None) -> None:
        self.settings = settings
        self.session = session or Session()

    @property
    def base_url(self) -> str:
        return f"https://{self.settings.host}:{self.settings.port}/restconf/data"

    def _request(self, method: str, path: str, **kwargs: Any):
        return self.session.request(
            method,
            f"{self.base_url}/{path.lstrip('/')}",
            auth=HTTPBasicAuth(self.settings.username, self.settings.password),
            timeout=self.settings.timeout_seconds,
            verify=self.settings.verify_tls,
            **kwargs,
        )

    def get(self, path: str) -> dict[str, Any]:
        response = self._request("GET", path, headers={"Accept": YANG_JSON})
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise TypeError("RESTCONF response must be a JSON object")
        return payload

    def get_hostname(self) -> dict[str, Any]:
        return self.get("Cisco-IOS-XE-native:native/hostname")

    def get_version(self) -> dict[str, Any]:
        return self.get("Cisco-IOS-XE-native:native/version")

    def get_interfaces_oper(self) -> dict[str, Any]:
        return self.get("Cisco-IOS-XE-interfaces-oper:interfaces")

    def get_routing_state(self) -> dict[str, Any]:
        return self.get("ietf-routing:routing-state/routing-instance")

    def get_loopback(self, number: int) -> dict[str, Any] | None:
        response = self._request(
            "GET",
            f"Cisco-IOS-XE-native:native/interface/Loopback={number}",
            headers={"Accept": YANG_JSON},
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise TypeError("RESTCONF response must be a JSON object")
        return payload

    def _require_writes(self) -> None:
        if not self.settings.allow_writes:
            raise RuntimeError("writes disabled; set CISCO_ALLOW_WRITES=true for the private lab")

    def create_demo_loopback(self) -> dict[str, Any]:
        self._require_writes()
        if self.get_loopback(DEMO_LOOPBACK) is not None:
            raise RuntimeError(f"Loopback{DEMO_LOOPBACK} already exists; refusing to overwrite it")

        patch = f"""<yang-patch xmlns="urn:ietf:params:xml:ns:yang:ietf-yang-patch">
  <patch-id>create-portfolio-loopback-{DEMO_LOOPBACK}</patch-id>
  <edit>
    <edit-id>create-loopback-{DEMO_LOOPBACK}</edit-id>
    <operation>create</operation>
    <target>/Loopback={DEMO_LOOPBACK}</target>
    <value>
      <Loopback xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-native">
        <name>{DEMO_LOOPBACK}</name>
        <description>{DEMO_DESCRIPTION}</description>
        <ip>
          <address>
            <primary>
              <address>{DEMO_ADDRESS}</address>
              <mask>{DEMO_MASK}</mask>
            </primary>
          </address>
        </ip>
      </Loopback>
    </value>
  </edit>
</yang-patch>"""
        response = self._request(
            "PATCH",
            "Cisco-IOS-XE-native:native/interface",
            headers={"Accept": YANG_JSON, "Content-Type": YANG_PATCH_XML},
            data=patch,
        )
        response.raise_for_status()
        created = self.get_loopback(DEMO_LOOPBACK)
        if created is None:
            raise RuntimeError("Loopback creation returned success but verification failed")
        return {"result": "created", "loopback": DEMO_LOOPBACK, "verified": True}

    def delete_demo_loopback(self) -> dict[str, Any]:
        self._require_writes()
        current = self.get_loopback(DEMO_LOOPBACK)
        if current is None:
            raise RuntimeError(f"Loopback{DEMO_LOOPBACK} is absent; refusing ambiguous rollback")

        entries = current.get("Cisco-IOS-XE-native:Loopback")
        if not isinstance(entries, list) or len(entries) != 1:
            raise RuntimeError("unexpected Loopback250 response; refusing deletion")
        entry = entries[0]
        if not isinstance(entry, dict) or entry.get("description") != DEMO_DESCRIPTION:
            raise RuntimeError("Loopback250 is not owned by this demo; refusing deletion")

        response = self._request(
            "DELETE",
            f"Cisco-IOS-XE-native:native/interface/Loopback={DEMO_LOOPBACK}",
            headers={"Accept": YANG_JSON},
        )
        response.raise_for_status()
        if self.get_loopback(DEMO_LOOPBACK) is not None:
            raise RuntimeError("Loopback deletion returned success but verification failed")
        return {"result": "deleted", "loopback": DEMO_LOOPBACK, "verified": True}
