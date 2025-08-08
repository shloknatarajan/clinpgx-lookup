from pydantic import BaseModel
from typing import List, Optional


class DrugSearchResult(BaseModel):
    id: str
    score: float
    name: str
    generic_names: List[str]



    