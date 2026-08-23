#!/usr/bin/env python3
"""CLI entrypoint for the lead-gen pipeline.

Examples:
    python scripts/run_pipeline.py --confirm-profile ecommerce-brands
    python scripts/run_pipeline.py --confirm-profile ecommerce-brands \
        --approve-spend 100
    python scripts/run_pipeline.py --confirm-profile ecommerce-brands --send
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from leadgen import pipeline  # noqa: E402
from leadgen.config import ConfigError, load_settings  # noqa: E402
from leadgen.hitl import HumanApprovalRequired  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--confirm-profile",
        help="Name of the profile you intend to run — must match the "
        "active profile in config/client_profiles.yaml.",
    )
    parser.add_argument(
        "--limit", type=int, default=25, help="Max leads to fetch this run."
    )
    parser.add_argument(
        "--approve-spend",
        type=int,
        default=None,
        help="Approve fetching up to N leads if that exceeds the profile's "
        "free threshold.",
    )
    parser.add_argument(
        "--send",
        action="store_true",
        help="Actually send emails via Gmail instead of only drafting them.",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    settings = load_settings()

    try:
        rows = pipeline.run(
            settings=settings,
            confirm_profile=args.confirm_profile,
            limit=args.limit,
            approve_spend=args.approve_spend,
            send=args.send,
        )
    except (ConfigError, HumanApprovalRequired) as e:
        print(f"\nBLOCKED: {e}\n", file=sys.stderr)
        return 2

    print(f"\nDone. {len(rows)} leads processed this run.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
