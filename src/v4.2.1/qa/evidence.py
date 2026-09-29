from dataclasses import dataclass
import hashlib,json
@dataclass(frozen=True)
class Evidence:
    case_id:str; environment:str; expected:dict; observed:dict; events:list; final_exchange_state:dict; final_local_state:dict; reconciliation:str; evidence_hash:str; passed:bool
def build(case_id,expected,observed,events,exchange,local,reconciliation,passed):
    payload={"case_id":case_id,"expected":expected,"observed":observed,"events":events,"exchange":exchange,"local":local,"reconciliation":reconciliation}
    h=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    return Evidence(case_id,"TESTNET",expected,observed,events,exchange,local,reconciliation,h,passed)
