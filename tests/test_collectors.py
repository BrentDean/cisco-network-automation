import json
from pathlib import Path

import pytest

from cisco_network_automation.collectors import (
    build_device_snapshot,
    normalize_interfaces_oper,
)

ROOT = Path(__file__).parent.parent


def load_interfaces_fixture():
    return json.loads(
        (ROOT / "tests/fixtures/interfaces_oper.json").read_text(encoding="utf-8")
    )


def test_normalize_interfaces_oper_matches_live_ios_xe_shape():
    interfaces = normalize_interfaces_oper(load_interfaces_fixture())

    assert len(interfaces) == 3

    management = interfaces[0]
    assert management.name == "GigabitEthernet1"
    assert management.admin_up is True
    assert management.oper_up is True
    assert management.ipv4 == "10.10.20.148/24"
    assert management.description is None

    spare = interfaces[1]
    assert spare.name == "GigabitEthernet2"
    assert spare.admin_up is False
    assert spare.oper_up is False
    assert spare.ipv4 is None


def test_normalize_interfaces_preserves_nonempty_description():
    interfaces = normalize_interfaces_oper(load_interfaces_fixture())
    assert interfaces[2].description == "lab-spare"


def test_build_device_snapshot_records_live_collection_metadata():
    snapshot = build_device_snapshot(
        {"Cisco-IOS-XE-native:hostname": "Cat8kv"},
        {"Cisco-IOS-XE-native:version": "17.15"},
        load_interfaces_fixture(),
    )

    assert snapshot.hostname == "Cat8kv"
    assert len(snapshot.interfaces) == 3
    assert snapshot.metadata == {
        "source": "restconf",
        "ios_xe_version": "17.15",
        "interface_model": "Cisco-IOS-XE-interfaces-oper:interfaces",
        "interface_count": 3,
    }


def test_normalize_interfaces_rejects_missing_container():
    with pytest.raises(ValueError, match="interfaces-oper"):
        normalize_interfaces_oper({})


def test_normalize_interfaces_rejects_bad_mask():
    payload = load_interfaces_fixture()
    payload["Cisco-IOS-XE-interfaces-oper:interfaces"]["interface"][0][
        "ipv4-subnet-mask"
    ] = "not-a-mask"

    with pytest.raises(ValueError, match="invalid IPv4 subnet mask"):
        normalize_interfaces_oper(payload)
