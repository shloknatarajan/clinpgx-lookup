from pydantic import BaseModel
from typing import List, Optional
import requests
from src.clinpgx_lookup.search_utils import calc_similarity, general_search
import pandas as pd
class DrugSearchResult(BaseModel):
    id: str
    name: str
    url: str
    score: float
"""
ClinPGx Search
"""
def local_clinpgx_search(drug_name: str, threshold: float = 0.8, top_k: int = 1) -> Optional[List[DrugSearchResult]]:
    local_path = "clinpgx_data/drugs/drugs.tsv"
    df = pd.read_csv(local_path, sep="\t")
    results = general_search(df, drug_name, "Name", "PharmGKB Accession Id", threshold=threshold, top_k=top_k)
    if results:
        return [DrugSearchResult(id=result['PharmGKB Accession Id'], name=result['Name'], url=f"https://www.clinpgx.org/chemical/{result['PharmGKB Accession Id']}", score=result['score']) for result in results]
    return []

"""
RxNorm Search
"""
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



