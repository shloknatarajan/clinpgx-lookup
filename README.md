# ClinPGx Term Lookup

## Goal
Take a term and find it's closest occurency in ClinPGx databases
You can choose whether or not this is a gene, drug, variant, phenotype, etc.

## Considerations
- Some sort of cacheing mechanism for looking up the same variants would be nice
- How / where to save the files needed for lookup/term matching would be good. Should not just be searching through raw tsvs
- basic idea of what the algorithm should look like
- Should maybe be able to search through the synonym list as well
- Convert the files to pkl for better loading/storing

## Steps
1. Highly prioritize drug and allele/variant lookup
2. Rough plan for fallback mechanisms for both
3. Implementation
4. Package up into API
5. Publish and use

## Drugs
- Search through the Name column for similarity
- If no good maches, parse and search through generic names (also in pharmgkb table)
    - For parsing through generic names, remove the non text data and stuff in brackets
- Keep the columns ID, Name, Generic Names, Score
- Need to turn the ID into a URL and add that to the DrugRecord object.
- Fallback 1: RxNorm
- Use approximateTerm endpoint to get top results .

Arian's RxNorm Approach:
```
def get_rxcui(drug_name):
    url = "https://rxnav.nlm.nih.gov/REST/approximateTerm.json"
    params = {"term": drug_name, "maxEntries": 1}
    try:
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            candidates = data.get('approximateGroup', {}).get('candidate', [])
            if candidates:
                return candidates[0]['rxcui']
    except:
        pass
    return None

def get_normalized_name(rxcui):
    if rxcui is None:
        return None
    url = f"https://rxnav.nlm.nih.gov/REST/rxcui/{rxcui}/properties.json"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data.get('properties', {}).get('name', None)
    except:
        pass
    return None

def normalize_drug(drug_name):
    rxcui = get_rxcui(drug_name)
    return get_normalized_name(rxcui)

# Create mapping dictionary
mapping = {}
for drug in tqdm(unique_drugs, desc="Normalizing unique drug parts"):
    normalized = normalize_drug(drug)
    mapping[drug] = normalized
```

## Alleles
- For RSIDs:
    - Search through the pharmgkb list for rsID under 'Variant Name' column
    - There are synonyms but let's save that for later
    - If it doesn't show up there try tmVar3
- if that 

## Questions
- If you use one of the APIs, can you fuzzy search?
- Is fuzzy search important? 
    - Seems like it would be for drugs but for alleles/genes not sure