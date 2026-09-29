from dataclasses import dataclass
@dataclass(frozen=True)
class DatasetKey: symbol:str; timeframe:str; ruleset_hash:str; data_version:str
class ResearchDataset:
    def __init__(self,key): self.key=key; self.records=[]
    def append(self,record):
        if record.ruleset_hash!=self.key.ruleset_hash: raise ValueError("RULESET_HASH_MISMATCH")
        self.records.append(record)
