"""
ClinPGx Phenotype Lookup

Goal: phenotype name -> PharmGKB phenotype accession id(s)

Sources: data/phenotypes/phenotypes.tsv
Name columns used:
- primary: Name
- lists: Alternate Names
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

from .lookup_utils import NameIndex, lookup_ids, load_or_build_index_from_resource


def _load_index() -> NameIndex:
    return load_or_build_index_from_resource(
        resource_relpath="data/phenotypes/phenotypes.tsv",
        cache_basename="phenotypes_name_index.pkl",
        id_column="PharmGKB Accession Id",
        primary_name_columns=["Name"],
        list_name_columns=["Alternate Names"],
    )


def lookup_phenotype_ids(
    phenotype_term: str,
    *,
    threshold: float = 0.6,
    top_k: int = 5,
    index: NameIndex | None = None,
) -> Tuple[List[str], List[float]]:
    if index is None:
        index = _load_index()
    return lookup_ids(phenotype_term, index=index, threshold=threshold, top_k=top_k)


def phenotype_lookup(phenotype_term: str, threshold: float, top_k: int) -> Tuple[List[str], List[float]]:
    return lookup_phenotype_ids(phenotype_term, threshold=threshold, top_k=top_k)


def main() -> None:
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m clinpgx_lookup.phenotype_lookup <phenotype term> [threshold] [top_k]")
        raise SystemExit(1)
    term = " ".join(sys.argv[1:])
    try:
        maybe_k = int(sys.argv[-1])
        maybe_t = float(sys.argv[-2])
        term = " ".join(sys.argv[1:-2])
        threshold = maybe_t
        top_k = maybe_k
    except Exception:
        threshold = 0.6
        top_k = 5
    ids, scores = lookup_phenotype_ids(term, threshold=threshold, top_k=top_k)
    for acc, sc in zip(ids, scores):
        print(f"{acc}\t{sc:.3f}")


if __name__ == "__main__":
    main()
