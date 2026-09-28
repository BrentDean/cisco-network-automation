"""Live pyATS AEtest validation for a Cisco IOS XE interface."""

from __future__ import annotations

from contextlib import suppress

from pyats import aetest

from cisco_network_automation.collectors import normalize_interfaces_oper
from cisco_network_automation.netconf import NetconfClient, NetconfSettings
from cisco_network_automation.pyats_client import (
    CommonInterfaceState,
    common_from_model,
    normalize_genie_ip_interface_brief,
)
from cisco_network_automation.restconf import RestconfClient, RestconfSettings


def _restconf_interface(client: RestconfClient, name: str):
    for interface in normalize_interfaces_oper(client.get_interfaces_oper()):
        if interface.name == name:
            return interface
    raise ValueError(f"RESTCONF response did not contain interface {name!r}")


class CommonSetup(aetest.CommonSetup):
    @aetest.subsection
    def connect(self, testbed, device_name: str) -> None:
        device = testbed.devices[device_name]
        device.connect(log_stdout=False)
        self.parent.parameters["device"] = device

    @aetest.subsection
    def collect_genie_state(self, device, interface_name: str) -> None:
        parsed = device.parse("show ip interface brief")
        if not isinstance(parsed, dict):
            self.failed("Genie parser output was not a dictionary")

        self.parent.parameters["pyats_state"] = normalize_genie_ip_interface_brief(
            parsed,
            interface_name,
        )


class ValidateExpectedState(aetest.Testcase):
    @aetest.test
    def interface_is_expected(
        self,
        pyats_state: CommonInterfaceState,
        interface_name: str,
        expected_ipv4: str,
    ) -> None:
        expected = CommonInterfaceState(
            name=interface_name,
            admin_up=True,
            oper_up=True,
            ipv4_address=expected_ipv4,
        )
        if pyats_state != expected:
            self.failed(
                f"Genie state mismatch: expected {expected.to_dict()}, "
                f"observed {pyats_state.to_dict()}"
            )


class ValidateCrossProtocolState(aetest.Testcase):
    @aetest.test
    def all_sources_agree(
        self,
        pyats_state: CommonInterfaceState,
        interface_name: str,
    ) -> None:
        netconf = NetconfClient(NetconfSettings.from_env())
        restconf = RestconfClient(RestconfSettings.from_env())

        netconf_state = common_from_model(netconf.get_interface_state(interface_name))
        restconf_state = common_from_model(_restconf_interface(restconf, interface_name))

        if not pyats_state == netconf_state == restconf_state:
            self.failed(
                "Cross-protocol mismatch: "
                f"pyATS/Genie={pyats_state.to_dict()}, "
                f"NETCONF={netconf_state.to_dict()}, "
                f"RESTCONF={restconf_state.to_dict()}"
            )


class CommonCleanup(aetest.CommonCleanup):
    @aetest.subsection
    def disconnect(self, device=None) -> None:
        if device is None:
            return
        with suppress(Exception):
            device.disconnect()


if __name__ == "__main__":
    aetest.main()
