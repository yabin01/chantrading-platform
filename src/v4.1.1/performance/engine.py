from .models import PerformanceSnapshot
class PerformanceEngine:
    def calculate(self,trades):
        n=len(trades)
        if not n: return PerformanceSnapshot(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0)
        wins=[t for t in trades if t.net_pnl>0]; losses=[t for t in trades if t.net_pnl<0]
        gp=sum(t.net_pnl for t in wins); gl=sum(-t.net_pnl for t in losses); net=sum(t.net_pnl for t in trades)
        rs=[t.net_pnl/t.initial_risk for t in trades if t.initial_risk>0]
        equity=peak=max_dd=0.
        for t in trades:
            equity+=t.net_pnl; peak=max(peak,equity); max_dd=min(max_dd,equity-peak)
        return PerformanceSnapshot(n,len(wins),len(losses),n-len(wins)-len(losses),len(wins)/n,gp,gl,net,net/n,sum(rs)/len(rs) if rs else 0,net/n,gp/gl if gl else float("inf"),max_dd,sum(t.fees for t in trades),sum(t.slippage for t in trades),sum(t.net_pnl-t.gross_pnl for t in trades))
