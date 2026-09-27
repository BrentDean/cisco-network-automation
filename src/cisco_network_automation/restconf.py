"""Minimal read-only RESTCONF client for Cisco IOS XE."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from requests import Session
from requests.auth import HTTPBasicAuth

YANG_JSON = "application/yang-data+json"


@dataclass(frozen=True)
class RestconfSettings:
    host: str
    username: str
    password: str
    port: int = 443
    verify_tls: bool = True
    timeout_seconds: float = 15.0

    @classmethod
    def from_env(cls) -> RestconfSettings:
        host = os.getenv("CISCO_HOST", "").strip()
        username = os.getenv("CISCO_USERNAME", "").strip()
        password = os.getenv("CISCO_PASSWORD", "")
        if not host or not username or not password:
            raise RuntimeError(
                "CISCO_HOST, CISCO_USERNAME, and CISCO_PASSWORD must be set"
            )
        port = int(os.getenv("CISCO_RESTCONF_PORT", "443"))
        return cls(host=host, username=username, password=password, port=port)


class RestconfClient:
    """Small RESTCONF GET client with explicit timeouts and TLS verification."""

    def __init__(
        self,
        settings: RestconfSettings,
        *,
        session: Session | None = None,
    ) -> None:
        self.settings = settings
        self.session = session or Session()

    @property
    def base_url(self) -> str:
        return (
            f"https://{self.settings.host}:{self.settings.port}"
            "/restconf/data"
        )

    def get(self, path: str) -> dict[str, Any]:
        clean_path = path.lstrip("/")
        response = self.session.get(
            f"{self.base_url}/{clean_path}",
            headers={"Accept": YANG_JSON},
            auth=HTTPBasicAuth(
                self.settings.username,
                self.settings.password,
            ),
            timeout=self.settings.timeout_seconds,
            verify=self.settings.verify_tls,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise TypeError("RESTCONF response must be a JSON object")
        return payload

    def get_hostname(self) -> dict[str, Any]:
        return self.get("Cisco-IOS-XE-native:native/hostname")

    def get_version(self) -> dict[str, Any]:
        return self.get("Cisco-IOS-XE-native:native/version")
