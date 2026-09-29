from collections import defaultdict
def summarize_groups(trades,field,engine):
    groups=defaultdict(list)
    for t in trades: groups[getattr(t,field)].append(t)
    return {k:engine.calculate(v) for k,v in groups.items()}
