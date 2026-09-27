"""CLI for offline validation and semantic diffing."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .diff import semantic_diff
from .io import load_policy, load_snapshot, write_json
from .reporting import build_validation_report
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

    report = semantic_diff(
        load_snapshot(args.before),
        load_snapshot(args.after),
    )
    if args.output:
        write_json(args.output, report)
    print(json.dumps(report, indent=2))
    return 0
