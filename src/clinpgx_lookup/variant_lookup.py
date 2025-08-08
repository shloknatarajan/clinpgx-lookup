"""
ClinPGx Variant Lookup

Goal: variant term (e.g., rsID, synonym, formal name) -> PharmGKB Variant ID(s)

Sources: data/variants/variants.tsv
Name columns used:
- primary: Variant Name
- lists: Synonyms
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

from .lookup_utils import NameIndex, lookup_ids, load_or_build_index_from_resource


def _load_index() -> NameIndex:
    return load_or_build_index_from_resource(
        resource_relpath="data/variants/variants.tsv",
        cache_basename="variants_name_index.pkl",
        id_column="Variant ID",
        primary_name_columns=["Variant Name"],
        list_name_columns=["Synonyms"],
    )


def lookup_variant_ids(
    variant_term: str,
    *,
    threshold: float = 0.6,
    top_k: int = 5,
    index: NameIndex | None = None,
) -> Tuple[List[str], List[str], List[float]]:
    if index is None:
        index = _load_index()
    ids, matched_names, scores = lookup_ids(variant_term, index=index, threshold=threshold, top_k=top_k)
    return ids, matched_names, scores


def variant_lookup(variant_term: str, threshold: float, top_k: int) -> Tuple[List[str], List[str], List[float]]:
    return lookup_variant_ids(variant_term, threshold=threshold, top_k=top_k)


def main() -> None:
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m clinpgx_lookup.variant_lookup <variant term> [threshold] [top_k]")
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
    ids, matched_names, scores = lookup_variant_ids(term, threshold=threshold, top_k=top_k)
    for acc, name, sc in zip(ids, matched_names, scores):
        print(f"{acc}\t{name}\t{sc:.3f}")


if __name__ == "__main__":
    main()
