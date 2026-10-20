"""Command line for a one-off scan, status read, brew, or cancel."""

from __future__ import annotations

import argparse
import asyncio
import sys

from .client import BruClient, discover
from .errors import BruError


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Talk to a BRU Maker One over BLE")
    sub = parser.add_subparsers(dest="command", required=True)

    scan = sub.add_parser("scan", help="List advertising BRU machines")
    scan.add_argument("--timeout", type=float, default=8.0)

    status = sub.add_parser("status", help="Connect and read status")
    status.add_argument("address")

    brew = sub.add_parser("brew", help="Start a brew, then disconnect")
    brew.add_argument("address")
    brew.add_argument("--celsius", type=float, default=80)
    brew.add_argument("--seconds", type=int, default=180)
    brew.add_argument("--milliliters", type=float, default=250)

    cancel = sub.add_parser("cancel", help="Stop the current process")
    cancel.add_argument("address")
    return parser


async def _run(argv: list[str]) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "scan":
            machines = await discover(args.timeout)
            if not machines:
                print("No BRU machine found. Put it in pairing mode for a first bond.")
                return 1
            for machine in machines:
                label = machine.state.label if machine.state else "no status bytes"
                print(f"{machine.address}  {machine.name or ''}  {label}")
            return 0
        async with BruClient(args.address) as client:
            if args.command == "status":
                state = await client.read_status()
                print(f"{state.label} ({state.status}/{state.sub_status})")
            elif args.command == "brew":
                result = await client.start_brew(
                    args.celsius, args.seconds, args.milliliters
                )
                print(result.label)
            elif args.command == "cancel":
                await client.cancel()
                print("cancel sent")
        return 0
    except BruError as exc:
        print(exc, file=sys.stderr)
        return 1


def main() -> None:
    """Entry point for ``python -m bru_ble``."""
    raise SystemExit(asyncio.run(_run(sys.argv[1:])))


if __name__ == "__main__":
    main()
