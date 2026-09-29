from dataclasses import dataclass
from enum import Enum
class OrderState(str,Enum):
 CREATED="CREATED"; SUBMITTING="SUBMITTING"; ACCEPTED="ACCEPTED"; PARTIALLY_FILLED="PARTIALLY_FILLED"; FILLED="FILLED"; CANCEL_REQUESTED="CANCEL_REQUESTED"; CANCELLED="CANCELLED"; REJECTED="REJECTED"; UNKNOWN="UNKNOWN"; RECONCILIATION_REQUIRED="RECONCILIATION_REQUIRED"
@dataclass(frozen=True)
class OrderIntent:
 intent_id:str; decision_id:str; signal_id:str; symbol:str; side:str; position_action:str; order_type:str; quantity:float; price:float|None; reduce_only:bool; client_order_id:str; risk_snapshot_id:str; ruleset_hash:str
