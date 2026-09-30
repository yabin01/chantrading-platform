"""Run the first read-only Hyperliquid Testnet 1m ChanLun canary."""
from __future__ import annotations

import argparse
import websocket

from chantrading.runtime.live_canary import Live1MCanary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--coin", default="ETH")
    parser.add_argument("--duration-seconds", type=int, default=600)
    args = parser.parse_args()

    canary = Live1MCanary()
    stream = canary.build_stream(
        ws_factory=lambda url: websocket.create_connection(
            url,
            timeout=5,
            enable_multithread=True,
        )
    )

    received = stream.run(args.coin, args.duration_seconds)
    snapshot = canary.snapshot()
    print(
        f"CANARY_OK received_candles={received} "
        f"structural_events={snapshot['structural_events']} "
        f"latest_bi={snapshot['latest_bi_id']} "
        f"latest_segment={snapshot['latest_segment_id']} "
        f"latest_center={snapshot['latest_center_id']}",
        flush=True,
    )


if __name__ == "__main__":
    main()
