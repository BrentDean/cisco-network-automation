"""Easypy job for the live IOS XE three-way interface validation."""

from __future__ import annotations

import os
from pathlib import Path

from pyats.easypy import run


def main(runtime) -> None:
    run(
        testscript=str(
            Path(__file__).resolve().parents[1]
            / "validation"
            / "pyats_interface_validation.py"
        ),
        testbed=runtime.testbed,
        device_name=os.getenv("CISCO_PYATS_DEVICE", "cat8000v"),
        interface_name=os.getenv("CISCO_VALIDATION_INTERFACE", "GigabitEthernet1"),
        expected_ipv4=os.getenv("CISCO_VALIDATION_IPV4", "10.10.20.48"),
    )
