from dataclasses import dataclass
@dataclass(frozen=True)
class Attribution:
    trade_id:str; decision_id:str; signal_id:str; entry_fractal_id:str; exit_fractal_id:str; entry_bi_id:str; exit_bi_id:str; entry_segment_id:str; exit_segment_id:str; center_id:str; a_sequence_id:str; divergence_type:str; divergence_reference:str; trigger_type:str; exit_type:str; stop_type:str; side:str; initial_r:float; realized_r:float; gross_pnl:float; net_pnl:float; execution_drag:float; ruleset_hash:str
