from pydantic import BaseModel
from typing import List, Optional, Any
import requests
from src.clinpgx_lookup.search_utils import calc_similarity
import pandas as pd
from loguru import logger

class RSIDSearchResult(BaseModel):
    id: str
    name: str
    url: str
    score: float
    
def pgkb_rsid_search(rsid: str, threshold: float = 0.8, top_k: int = 1) -> Optional[List[RSIDSearchResult]]:
    base_url = "https://api.pharmgkb.org/v1/data/variant?symbol="
    response = requests.get(base_url + rsid)
    if response.status_code == 200:
        data = response.json()
        score = calc_similarity(rsid, data['data'][0]['symbol'])
        if data['data']:
            return [RSIDSearchResult(id=result['id'], name=result['symbol'], url=f"https://www.clinpgx.org/variant/{result['id']}", score=score) for result in data['data']]
    return []