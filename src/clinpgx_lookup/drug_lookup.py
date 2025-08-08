"""
ClinPGx Drug Lookup

Goal: drug name: str --> best matching PharmGKB accession id(s)

Inputs
- drug_name: str
- threshold: float (0.0-1.0) minimum similarity to keep
- top_k: int number of IDs to return

Outputs
- ids: list[str] of PharmGKB accession IDs
- scores: list[float] corresponding similarity scores (0.0-1.0)

Implementation notes
- Builds a lightweight name index from `data/drugs/drugs.tsv` covering
  primary names and common synonym columns (generic/trade/mixtures).
- Uses difflib SequenceMatcher for a simple, dependency-free similarity.
- Caches the processed index to a pickle for faster subsequent loads.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

from .lookup_utils import NameIndex, lookup_ids, load_or_build_index_from_resource


def _load_index() -> NameIndex:
    return load_or_build_index_from_resource(
        resource_relpath="data/drugs/drugs.tsv",
        cache_basename="drugs_name_index.pkl",
        id_column="PharmGKB Accession Id",
        primary_name_columns=["Name"],
        list_name_columns=["Generic Names", "Trade Names", "Brand Mixtures"],
    )


def lookup_drug_ids(
    drug_name: str,
    *,
    threshold: float = 0.6,
    top_k: int = 5,
    index: NameIndex | None = None,
) -> Tuple[List[str], List[str], List[float]]:
    if index is None:
        index = _load_index()
    ids, matched_names, scores = lookup_ids(drug_name, index=index, threshold=threshold, top_k=top_k)
    return ids, matched_names, scores


def drug_lookup(drug_name: str, threshold: float, top_k: int) -> Tuple[List[str], List[str], List[float]]:
    return lookup_drug_ids(drug_name, threshold=threshold, top_k=top_k)


def main() -> None:
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m clinpgx_lookup.drug_lookup <drug name> [threshold] [top_k]")
        raise SystemExit(1)

    name = " ".join(sys.argv[1:])
    try:
        maybe_k = int(sys.argv[-1])
        maybe_t = float(sys.argv[-2])
        name_parts = sys.argv[1:-2]
        name = " ".join(name_parts)
        threshold = maybe_t
        top_k = maybe_k
    except Exception:
        threshold = 0.6
        top_k = 5

    ids, matched_names, scores = lookup_drug_ids(name, threshold=threshold, top_k=top_k)
    for acc, name, sc in zip(ids, matched_names, scores):
        print(f"{acc}\t{name}\t{sc:.3f}")


if __name__ == "__main__":
    main()
