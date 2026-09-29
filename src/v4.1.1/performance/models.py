from dataclasses import dataclass
@dataclass(frozen=True)
class Trade:
    trade_id:str; side:str; gross_pnl:float; net_pnl:float; initial_risk:float
    fees:float=0.; slippage:float=0.; trigger_type:str=""; divergence_type:str=""; stop_type:str=""; decision_id:str=""; signal_id:str=""; ruleset_hash:str=""
@dataclass(frozen=True)
class PerformanceSnapshot:
    total_trades:int; wins:int; losses:int; breakeven:int; win_rate:float; gross_profit:float; gross_loss:float; net_pnl:float; avg_pnl:float; avg_r:float; expectancy:float; profit_factor:float; max_drawdown:float; fees:float; slippage:float; execution_drag:float
