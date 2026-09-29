"""Minimal CLI for starting a bounded Testnet soak run."""
from __future__ import annotations
import argparse
import json
from .soak_runner import SoakRunConfig, SoakTestRunner


def build_parser():
    parser=argparse.ArgumentParser(prog="chantrading-soak")
    parser.add_argument("--duration-ms", type=int, required=True)
    parser.add_argument("--start-ms", type=int, default=None)
    parser.add_argument("--end-ms", type=int, default=None)
    return parser


def main(argv=None):
    args=build_parser().parse_args(argv)
    runner=SoakTestRunner(SoakRunConfig(args.duration_ms))
    runner.start(args.start_ms)
    end=args.end_ms
    if end is None:
        end=(args.start_ms or runner.clock_ms()) + args.duration_ms
    report=runner.stop(end)
    print(json.dumps(report.to_dict(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
