from collections import defaultdict
def group(records,fields):
    d=defaultdict(list)
    for r in records: d[tuple(getattr(r,f) for f in fields)].append(r)
    return d
def summarize(records):
    n=len(records); wins=[r for r in records if r.net_pnl>0]; losses=[r for r in records if r.net_pnl<0]; gp=sum(r.net_pnl for r in wins); gl=sum(-r.net_pnl for r in losses); rs=[r.realized_r for r in records]
    return {"count":n,"win_rate":len(wins)/n if n else 0,"net_pnl":sum(r.net_pnl for r in records),"avg_R":sum(rs)/len(rs) if rs else 0,"expectancy":sum(rs)/len(rs) if rs else 0,"profit_factor":gp/gl if gl else float("inf")}
def aggregate(records,fields): return {key:summarize(items) for key,items in group(records,fields).items()}
