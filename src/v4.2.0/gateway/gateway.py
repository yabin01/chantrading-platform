class TestnetGateway:
    def __init__(self,adapter): self.adapter=adapter
    def submit(self,intent):
        if getattr(self.adapter,"environment","")!="TESTNET": raise RuntimeError("TESTNET_ENDPOINT_REQUIRED")
        if getattr(self.adapter,"halted",False): raise RuntimeError("HALTED_NO_NEW_ORDER")
        return self.adapter.place_order(intent)
