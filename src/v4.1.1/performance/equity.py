def equity_curve(trades,starting_equity=0.):
    equity=starting_equity; peak=equity; rows=[]
    for t in trades:
        equity+=t.net_pnl; peak=max(peak,equity); dd=equity-peak
        rows.append({"trade_id":t.trade_id,"equity":equity,"peak":peak,"drawdown":dd,"drawdown_pct":dd/peak if peak else 0.})
    return rows
