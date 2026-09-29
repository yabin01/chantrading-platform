def alerts(snapshot):
    out=[]
    if snapshot.status=="WARNING": out.append(("WARNING","LIQUIDATION_BUFFER_LOW"))
    if snapshot.status=="CRITICAL": out.append(("CRITICAL","LIQUIDATION_BUFFER_CRITICAL"))
    if snapshot.status=="HALTED": out.append(("HALTED","RISK_GUARD"))
    if snapshot.risk_utilization>1: out.append(("CRITICAL","RISK_UTILIZATION_EXCEEDED"))
    if snapshot.stop_distance<=0: out.append(("HALTED","INVALID_STOP_DISTANCE"))
    return out
