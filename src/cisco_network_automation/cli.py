"""CLI for Cisco IOS XE state validation and guarded automation."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from .collectors import capture_device_snapshot, normalize_interfaces_oper
from .diff import semantic_diff
from .io import load_policy, load_snapshot, write_json
from .netconf import NetconfClient, NetconfSettings
from .reporting import build_validation_report
from .restconf import RestconfClient, RestconfSettings
from .validation import validate_snapshot

CROSS_CHECK_INTERFACE = "GigabitEthernet1"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cisco-validate")
    commands = parser.add_subparsers(dest="command", required=True)

    validate = commands.add_parser("validate")
    validate.add_argument("--snapshot", required=True, type=Path)
    validate.add_argument("--policy", required=True, type=Path)
    validate.add_argument("--output", type=Path)

    diff = commands.add_parser("diff")
    diff.add_argument("--before", required=True, type=Path)
    diff.add_argument("--after", required=True, type=Path)
    diff.add_argument("--output", type=Path)

    hello = commands.add_parser("restconf-hello")
    hello.add_argument("--output", type=Path)

    get = commands.add_parser("restconf-get")
    get.add_argument("--path", required=True)
    get.add_argument("--output", type=Path)

    snapshot = commands.add_parser("restconf-snapshot")
    snapshot.add_argument("--output", type=Path)

    netconf_hello = commands.add_parser("netconf-hello")
    netconf_hello.add_argument("--output", type=Path)

    netconf_hostname = commands.add_parser("netconf-hostname")
    netconf_hostname.add_argument("--output", type=Path)

    netconf_interface = commands.add_parser("netconf-interface")
    netconf_interface.add_argument("--name", default=CROSS_CHECK_INTERFACE)
    netconf_interface.add_argument("--output", type=Path)

    cross_check = commands.add_parser("cross-check-hostname")
    cross_check.add_argument("--output", type=Path)

    cross_check_interface = commands.add_parser("cross-check-interface")
    cross_check_interface.add_argument("--name", default=CROSS_CHECK_INTERFACE)
    cross_check_interface.add_argument("--output", type=Path)

    commands.add_parser("restconf-create-demo-loopback")
    commands.add_parser("restconf-delete-demo-loopback")
    return parser


def _restconf_hostname(client: RestconfClient) -> str:
    payload = client.get_hostname()
    hostname = payload.get("Cisco-IOS-XE-native:hostname")
    if not isinstance(hostname, str) or not hostname:
        raise ValueError("RESTCONF hostname response is missing expected value")
    return hostname


def _restconf_interface(client: RestconfClient, name: str):
    interfaces = normalize_interfaces_oper(client.get_interfaces_oper())
    for interface in interfaces:
        if interface.name == name:
            return interface
    raise ValueError(f"RESTCONF response did not contain interface {name!r}")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "validate":
        snapshot = load_snapshot(args.snapshot)
        checks = validate_snapshot(snapshot, load_policy(args.policy))
        report = build_validation_report(snapshot, checks)
        if args.output:
            write_json(args.output, report)
        print(json.dumps(report, indent=2))
        return 0 if report["result"] == "PASS" else 1

    if args.command == "diff":
        report = semantic_diff(load_snapshot(args.before), load_snapshot(args.after))
        if args.output:
            write_json(args.output, report)
        print(json.dumps(report, indent=2))
        return 0

    netconf_commands = {
        "netconf-hello",
        "netconf-hostname",
        "netconf-interface",
        "cross-check-hostname",
        "cross-check-interface",
    }
    if args.command in netconf_commands:
        netconf = NetconfClient(NetconfSettings.from_env())

        if args.command == "netconf-hello":
            report = netconf.hello()
        elif args.command == "netconf-hostname":
            report = {"protocol": "netconf", "hostname": netconf.get_hostname()}
        elif args.command == "netconf-interface":
            report = {
                "protocol": "netconf",
                "interface": asdict(netconf.get_interface_state(args.name)),
            }
        elif args.command == "cross-check-hostname":
            restconf = RestconfClient(RestconfSettings.from_env())
            netconf_hostname = netconf.get_hostname()
            restconf_hostname = _restconf_hostname(restconf)
            report = {
                "result": "PASS" if netconf_hostname == restconf_hostname else "FAIL",
                "netconf_hostname": netconf_hostname,
                "restconf_hostname": restconf_hostname,
                "match": netconf_hostname == restconf_hostname,
            }
        else:
            restconf = RestconfClient(RestconfSettings.from_env())
            netconf_state = netconf.get_interface_state(args.name)
            restconf_state = _restconf_interface(restconf, args.name)
            matches = netconf_state == restconf_state
            report = {
                "result": "PASS" if matches else "FAIL",
                "interface": args.name,
                "netconf": asdict(netconf_state),
                "restconf": asdict(restconf_state),
                "match": matches,
            }

        if args.output:
            write_json(args.output, report)
        print(json.dumps(report, indent=2))
        return 0 if report.get("result", "PASS") == "PASS" else 1

    client = RestconfClient(RestconfSettings.from_env())

    if args.command == "restconf-hello":
        report = {"hostname": client.get_hostname(), "version": client.get_version()}
    elif args.command == "restconf-snapshot":
        report = capture_device_snapshot(client).to_dict()
    elif args.command == "restconf-create-demo-loopback":
        report = client.create_demo_loopback()
    elif args.command == "restconf-delete-demo-loopback":
        report = client.delete_demo_loopback()
    else:
        report = client.get(args.path)

    if getattr(args, "output", None):
        write_json(args.output, report)
    print(json.dumps(report, indent=2))
    return 0
