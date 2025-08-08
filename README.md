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
   - `pip install clinpgx-lookup`

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
  - `matches = ClinPGxTermLookup().search("drug", "abacavir", threshold=0.75, top_k=3)`

Advanced
- Set `CLINPGX_DATA_DIR` to use a shared read-only data path without copying.
- Set `CLINPGX_CACHE_DIR` to control where pickle indices and copied TSVs are stored.

## Install via Conda / Pixi

- Conda (users): `conda install -c conda-forge -c shloknatarajan clinpgx-lookup`
- Pixi (users): add channel then add package
  - In `pixi.toml`: `channels = ["conda-forge", "shloknatarajan"]`
  - Install: `pixi add clinpgx-lookup`

## Release (publish to Anaconda.org)

This repo includes a minimal conda recipe at `conda.recipe/meta.yaml`. Build and upload using Pixi tasks:

Prerequisites (one-time):
- `pixi global install conda-build anaconda-client`
- Create an Anaconda.org token (Settings → Access), then export it:
  - `export ANACONDA_API_TOKEN=<your_token>`

Build (optional: set a release version):
- Optionally set `PKG_VERSION` (falls back to `0.1.0`):
  - `export PKG_VERSION=0.1.1`
- Build the package:
  - `pixi run build-conda`
- See the artifact path:
  - `pixi run build-conda-output`

Upload to Anaconda.org (user: `shloknatarajan`):
- `pixi run upload-conda`

Verify from a fresh environment:
- `conda create -n test-clinpgx -c conda-forge -c shloknatarajan clinpgx-lookup`
- `conda activate test-clinpgx && clinpgx-lookup --help`
