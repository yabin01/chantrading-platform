from .models import RiskSnapshot
class RiskExposureEngine:
    def calculate(self,equity,side,quantity,mark,entry,stop,initial_risk,leverage,liquidation_price=None,drawdown=0.,daily_loss=0.,consecutive_losses=0,warning_buffer=0.05,critical_buffer=0.02):
        stop_distance=(entry-stop) if side=="LONG" else (stop-entry)
        if equity<=0: status="HALTED"
        elif stop_distance<0: status="HALTED"
        else:
            status="NORMAL"
            if liquidation_price is not None:
                d=(mark-liquidation_price) if side=="LONG" else (liquidation_price-mark); b=d/mark
                if b<=0: status="HALTED"
                elif b<critical_buffer: status="CRITICAL"
                elif b<warning_buffer: status="WARNING"
        notional=abs(quantity*mark); exposure=notional/equity if equity>0 else float("inf"); risk_util=initial_risk/equity if equity>0 else float("inf")
        liq_dist=None if liquidation_price is None else ((mark-liquidation_price) if side=="LONG" else (liquidation_price-mark)); liq_buf=None if liq_dist is None else liq_dist/mark
        return RiskSnapshot(equity,side,quantity,mark,entry,stop,notional,leverage,initial_risk,risk_util,stop_distance,liquidation_price,liq_dist,liq_buf,exposure,drawdown,daily_loss,consecutive_losses,status)
