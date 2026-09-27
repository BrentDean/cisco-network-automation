import json
from pathlib import Path

import pytest

from cisco_network_automation.collectors import (
    build_device_snapshot,
    normalize_interfaces_oper,
    normalize_routing_state,
)

ROOT = Path(__file__).parent.parent


def load_interfaces_fixture():
    return json.loads(
        (ROOT / "tests/fixtures/interfaces_oper.json").read_text(encoding="utf-8")
    )


def load_routing_fixture():
    return json.loads(
        (ROOT / "tests/fixtures/routing_state.json").read_text(encoding="utf-8")
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


def test_normalize_routing_state_matches_live_ios_xe_shape():
    routes = normalize_routing_state(load_routing_fixture())

    assert len(routes) == 4

    default_route = routes[0]
    assert default_route.prefix == "0.0.0.0/0"
    assert default_route.next_hop == "10.10.20.254"
    assert default_route.protocol == "static"

    local_route = routes[1]
    assert local_route.prefix == "1.1.1.1/32"
    assert local_route.next_hop is None
    assert local_route.protocol == "direct"

    connected_route = routes[2]
    assert connected_route.prefix == "10.10.20.0/24"
    assert connected_route.next_hop is None
    assert connected_route.protocol == "direct"


def test_build_device_snapshot_records_live_collection_metadata():
    snapshot = build_device_snapshot(
        {"Cisco-IOS-XE-native:hostname": "Cat8kv"},
        {"Cisco-IOS-XE-native:version": "17.15"},
        load_interfaces_fixture(),
        load_routing_fixture(),
    )

    assert snapshot.hostname == "Cat8kv"
    assert len(snapshot.interfaces) == 3
    assert len(snapshot.routes) == 4
    assert snapshot.metadata == {
        "source": "restconf",
        "ios_xe_version": "17.15",
        "interface_model": "Cisco-IOS-XE-interfaces-oper:interfaces",
        "interface_count": 3,
        "routing_model": "ietf-routing:routing-instance",
        "route_count": 4,
    }


def test_normalize_interfaces_rejects_missing_container():
    with pytest.raises(TypeError, match="interfaces-oper"):
        normalize_interfaces_oper({})


def test_normalize_interfaces_rejects_bad_mask():
    payload = load_interfaces_fixture()
    payload["Cisco-IOS-XE-interfaces-oper:interfaces"]["interface"][0][
        "ipv4-subnet-mask"
    ] = "not-a-mask"

    with pytest.raises(ValueError, match="invalid IPv4 subnet mask"):
        normalize_interfaces_oper(payload)


def test_normalize_routing_state_rejects_missing_container():
    with pytest.raises(TypeError, match="routing-instance"):
        normalize_routing_state({})
