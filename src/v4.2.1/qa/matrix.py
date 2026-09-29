from dataclasses import dataclass
@dataclass(frozen=True)
class Case: case_id:str; name:str; critical:bool=True
CASES=[Case("C01","Connectivity"),Case("C02","Market Metadata"),Case("C03","Account Position"),Case("C04","Order Submit"),Case("C05","Cancel"),Case("C06","Partial Fill"),Case("C07","Full Fill"),Case("C08","Reduce Only"),Case("C09","Duplicate Event"),Case("C10","Connection Loss"),Case("C11","Reconciliation"),Case("C12","Restart Recovery"),Case("C13","Paper Testnet Intent Equivalence")]
def certification(results):
    missing=[c.case_id for c in CASES if not results.get(c.case_id,False)]
    return {"status":"PASS" if not missing else "FAILED","missing":missing}
