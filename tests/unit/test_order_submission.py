from chantrading.adapters.hyperliquid.order_submission import (
    SigningGateway, TestnetOrderSubmitter, build_order_action,
)
from chantrading.adapters.hyperliquid.testnet_execution import TestnetOrderRequest


def req():
    return TestnetOrderRequest("cl-1","ETH","BUY","0.01","LIMIT",True)


def test_order_action_mapping():
    action=build_order_action(req(),3,"2000")
    order=action["orders"][0]
    assert action["type"]=="order"
    assert order["a"]==3
    assert order["b"] is True
    assert order["s"]=="0.01"
    assert order["r"] is True


def test_signer_is_injected():
    class Signer(SigningGateway):
        def sign(self, action, client_order_id):
            return {"action":action,"signature":"TEST","cloid":client_order_id}
    sent=[]
    submitter=TestnetOrderSubmitter(sent.append,Signer())
    submitter.submit(req(),3,"2000")
    assert sent[0]["signature"]=="TEST"


def test_no_private_key_is_required_by_submitter():
    assert "private_key" not in SigningGateway.__dict__
