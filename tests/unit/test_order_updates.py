import json
from chantrading.adapters.hyperliquid.order_updates import (
    parse_fill, parse_order_update, parse_position,
)


def test_parse_order_update():
    m={"channel":"orderUpdates","data":{"status":"filled","order":{"oid":7,"cloid":"cl-1","coin":"ETH","filledSz":"0.01"}}}
    e=parse_order_update(json.dumps(m))
    assert e.status=="FILLED"
    assert e.client_order_id=="cl-1"
    assert e.filled_quantity=="0.01"


def test_parse_fill():
    m={"channel":"userFills","data":[{"oid":7,"coin":"ETH","side":"B","sz":"0.01","px":"2000","time":123}]}
    e=parse_fill(json.dumps(m))
    assert e.exchange_order_id=="7"
    assert e.quantity=="0.01"


def test_parse_position():
    m={"channel":"clearinghouseState","data":{"assetPositions":[{"position":{"coin":"ETH","szi":"0.01","entryPx":"2000"}}]}}
    e=parse_position(json.dumps(m))
    assert e.symbol=="ETH"
    assert e.size=="0.01"
