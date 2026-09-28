"""Input/output helpers for snapshots, policies, and reports."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from .models import DeviceSnapshot


def load_snapshot(path: str | Path) -> DeviceSnapshot:
    return DeviceSnapshot.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def load_policy(path: str | Path) -> dict[str, Any]:
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("policy must contain a YAML mapping at the top level")
    return payload


def write_json(path: str | Path, payload: Any) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
