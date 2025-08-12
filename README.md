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
- Use approximateTerm endpoint to get top results.

## Alleles
- For RSIDs:
    - Search through the pharmgkb list for rsID under 'Variant Name' column
    - There are synonyms but let's save that for later
    - If it doesn't show up there try tmVar3
- For Star Alleles:
    - Try the pharmgkb api
    - Try the tmVar3 api
    - Sort by score but prefer pharmgkb api


## Questions
- If you use one of the APIs, can you fuzzy search?
- Is fuzzy search important? 
    - Seems like it would be for drugs but for alleles/genes not sure