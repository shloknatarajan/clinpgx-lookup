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

## Install and Data Setup

This package ships without data to keep the wheel small and avoid licensing issues. You have two easy options:

- Option A: Use a local `data/` folder (dev) — keep the repo's `data/` in place and run lookups directly.
- Option B: Copy TSVs into your user cache so everything works offline after install.

Steps for Option B:

1) Install the package (after publishing):
   - `pip install clinpgx-term-lookup`

2) Prepare data once (copies TSVs to `~/.cache/clinpgx_lookup/data`):
   - If you have the repo locally:
     - `clinpgx-setup --source /path/to/repo/data`
   - Or, if your TSVs live elsewhere, point `--source` at the folder that contains `drugs/`, `genes/`, `variants/`, `phenotypes/`.

3) Validate data layout (optional but recommended):
   - `clinpgx-check-data --source /path/to/repo/data`
   - Once cached, simply run: `clinpgx-check-data` (it will find `~/.cache/clinpgx_lookup/data`)

4) Run lookups:
   - `clinpgx-lookup drug "abacavir"`
   - `clinpgx-lookup gene CYP2D6`
   - `clinpgx-lookup phenotype neutropenia`
   - `clinpgx-lookup variant rs10046`

Examples
- Change similarity threshold and number of results:
  - `clinpgx-lookup drug "fluoxetine" 0.7 10`
- Programmatic usage:
  - `from clinpgx_lookup import ClinPGxTermLookup`
  - `ids, scores = ClinPGxTermLookup().search("drug", "abacavir", threshold=0.75, top_k=3)`

Advanced
- Set `CLINPGX_DATA_DIR` to use a shared read-only data path without copying.
- Set `CLINPGX_CACHE_DIR` to control where pickle indices and copied TSVs are stored.
