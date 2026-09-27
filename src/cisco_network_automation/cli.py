"""CLI for Cisco IOS XE state validation and guarded RESTCONF demo changes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .collectors import capture_device_snapshot
from .diff import semantic_diff
from .io import load_policy, load_snapshot, write_json
from .reporting import build_validation_report
from .restconf import RestconfClient, RestconfSettings
from .validation import validate_snapshot


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

    commands.add_parser("restconf-create-demo-loopback")
    commands.add_parser("restconf-delete-demo-loopback")
    return parser


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
