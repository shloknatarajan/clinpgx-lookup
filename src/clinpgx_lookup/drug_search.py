from pydantic import BaseModel
from typing import List, Optional
import requests
from src.clinpgx_lookup.search_utils import calc_similarity
class DrugSearchResult(BaseModel):
    id: str
    name: str
    url: str
    score: float

def get_first_rxnorm_candidate(data):
    """
    Get the first candidate object with RXNORM as the source.
    
    Args:
        data (dict): The response data dictionary
        
    Returns:
        dict or None: First candidate with RXNORM source, or None if not found
    """
    candidates = data.get("approximateGroup", {}).get("candidate", [])
    
    for candidate in candidates:
        if candidate.get("source") == "RXNORM":
            return candidate
    
    return None 

def rxnorm_search(drug_name: str) -> Optional[DrugSearchResult]:
    url = "https://rxnav.nlm.nih.gov/REST/approximateTerm.json"
    params = {"term": drug_name, "maxEntries": 1}
    response = requests.get(url, params=params, timeout=5)
    if response.status_code == 200:
        data = response.json()
        candidate = get_first_rxnorm_candidate(data)
        if candidate:
            rxcui = candidate['rxcui']
            url = f"https://ndclist.com/rxnorm/rxcui/{rxcui}"
            name = candidate['name']
            score = calc_similarity(drug_name, name)
            return DrugSearchResult(id=rxcui, name=name, url=url, score=score)
    return DrugSearchResult(id="", name="Not Found", url="", score=0)




