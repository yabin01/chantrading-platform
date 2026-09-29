from .models import OrderState
LEGAL={OrderState.CREATED:{OrderState.SUBMITTING},OrderState.SUBMITTING:{OrderState.ACCEPTED,OrderState.REJECTED,OrderState.UNKNOWN},OrderState.ACCEPTED:{OrderState.PARTIALLY_FILLED,OrderState.FILLED,OrderState.CANCEL_REQUESTED,OrderState.UNKNOWN},OrderState.PARTIALLY_FILLED:{OrderState.PARTIALLY_FILLED,OrderState.FILLED,OrderState.CANCEL_REQUESTED,OrderState.UNKNOWN},OrderState.CANCEL_REQUESTED:{OrderState.CANCELLED,OrderState.PARTIALLY_FILLED,OrderState.FILLED,OrderState.UNKNOWN},OrderState.UNKNOWN:{OrderState.RECONCILIATION_REQUIRED},OrderState.FILLED:set(),OrderState.CANCELLED:set(),OrderState.REJECTED:set(),OrderState.RECONCILIATION_REQUIRED:set()}
def transition(old,new):
    if new not in LEGAL[old]: raise ValueError(f"ILLEGAL_TRANSITION:{old}->{new}")
    return new
