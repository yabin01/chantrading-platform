REQUIRED=["connectivity","market_metadata","account_position","submit","cancel","partial_fill","full_fill","reduce_only","duplicate_event","connection_loss","reconciliation","restart_recovery","intent_equivalence"]
def certify(results):
    missing=[x for x in REQUIRED if not results.get(x,False)]
    return {"certified":not missing,"missing":missing}
