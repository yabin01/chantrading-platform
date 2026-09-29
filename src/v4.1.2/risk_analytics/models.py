from dataclasses import dataclass
@dataclass(frozen=True)
class RiskSnapshot:
    equity:float; side:str; quantity:float; mark_price:float; entry_price:float; stop_price:float; notional:float; leverage:float; initial_risk:float; risk_utilization:float; stop_distance:float; liquidation_price:float|None; liquidation_distance:float|None; liquidation_buffer:float|None; exposure_ratio:float; drawdown:float; daily_loss:float; consecutive_losses:int; status:str
