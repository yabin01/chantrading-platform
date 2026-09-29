"""Run the first read-only Hyperliquid Testnet 1m candle canary."""
from __future__ import annotations

import argparse
import websocket

from chantrading.adapters.hyperliquid.live_testnet import LiveTestnetCandleStream


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--coin",default="ETH")
    parser.add_argument("--duration-seconds",type=int,default=600)
    args=parser.parse_args()

    count=0

    def on_candle(event):
        nonlocal count
        count += 1
        print(
            f"CANDLE #{count} {event.coin} {event.interval} "
            f"ts={event.timestamp_ms} close={event.close} volume={event.volume}",
            flush=True,
        )

    stream=LiveTestnetCandleStream(
        ws_factory=lambda url: websocket.create_connection(
            url,
            timeout=30,
            enable_multithread=True,
        ),
        on_candle=on_candle,
    )
    received=stream.run(args.coin,args.duration_seconds)
    print(f"CANARY_OK received_candles={received}", flush=True)


if __name__=="__main__":
    main()
