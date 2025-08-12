from pydantic import BaseModel
from typing import List, Optional, Any
import requests
from src.clinpgx_lookup.search_utils import calc_similarity
import pandas as pd
from loguru import logger

class StarAlleleSearchResult(BaseModel):
    id: str
    name: str
    url: str
    score: float

def pgkb_star_allele_search(star_allele: str, threshold: float = 0.8, top_k: int = 1) -> Optional[List[StarAlleleSearchResult]]:
    base_url = "https://api.pharmgkb.org/v1/data/haplotype?symbol="
    response = requests.get(base_url + star_allele)
    if response.status_code == 200:
        data = response.json()
        score = calc_similarity(star_allele, data['data'][0]['symbol'])
        if data['data']:
            return [StarAlleleSearchResult(id=result['id'], name=result['symbol'], url=f"https://www.clinpgx.org/haplotype/{result['id']}", score=score) for result in data['data']]
    return []

