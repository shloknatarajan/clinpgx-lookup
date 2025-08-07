"""
Unified ClinPGx Term Lookup

Provides a single class to look up PharmGKB IDs across entity types:
- drug, gene, phenotype, variant, allele

Usage:
- from clinpgx_lookup.term_lookup import ClinPGxTermLookup
- lookup = ClinPGxTermLookup()
- ids, scores = lookup.search("drug", "abacavir", threshold=0.6, top_k=5)
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

from .lookup_utils import NameIndex, lookup_ids, load_or_build_index_from_resource


class ClinPGxTermLookup:
    """Unified term lookup with per-type cached indices."""

    def __init__(self) -> None:
        self._indices: Dict[str, NameIndex] = {}

    def _canonical_type(self, entity_type: str) -> str:
        t = (entity_type or "").strip().lower()
        # Accept plurals and aliases
        alias = {
            "drug": "drug",
            "drugs": "drug",
            "gene": "gene",
            "genes": "gene",
            "phenotype": "phenotype",
            "phenotypes": "phenotype",
            "variant": "variant",
            "variants": "variant",
            "allele": "allele",
            "alleles": "allele",
        }
        if t not in alias:
            raise ValueError("entity_type must be one of: drug, gene, phenotype, variant, allele")
        return alias[t]

    def _get_index(self, entity_type: str) -> NameIndex:
        et = self._canonical_type(entity_type)
        if et in self._indices:
            return self._indices[et]

        # Configure dataset columns per type
        if et == "drug":
            idx = load_or_build_index_from_resource(
                resource_relpath="data/drugs/drugs.tsv",
                cache_basename="drugs_name_index.pkl",
                id_column="PharmGKB Accession Id",
                primary_name_columns=["Name"],
                list_name_columns=["Generic Names", "Trade Names", "Brand Mixtures"],
            )
        elif et == "gene":
            idx = load_or_build_index_from_resource(
                resource_relpath="data/genes/genes.tsv",
                cache_basename="genes_name_index.pkl",
                id_column="PharmGKB Accession Id",
                primary_name_columns=["Name", "Symbol"],
                list_name_columns=["Alternate Names", "Alternate Symbols"],
            )
        elif et == "phenotype":
            idx = load_or_build_index_from_resource(
                resource_relpath="data/phenotypes/phenotypes.tsv",
                cache_basename="phenotypes_name_index.pkl",
                id_column="PharmGKB Accession Id",
                primary_name_columns=["Name"],
                list_name_columns=["Alternate Names"],
            )
        elif et == "variant":
            idx = load_or_build_index_from_resource(
                resource_relpath="data/variants/variants.tsv",
                cache_basename="variants_name_index.pkl",
                id_column="Variant ID",
                primary_name_columns=["Variant Name"],
                list_name_columns=["Synonyms"],
            )
        elif et == "allele":
            idx = load_or_build_index_from_resource(
                resource_relpath="data/variants/variants.tsv",
                cache_basename="alleles_name_index.pkl",
                id_column="Variant ID",
                primary_name_columns=["Variant Name"],
                list_name_columns=["Synonyms"],
            )
        else:
            raise AssertionError("Unhandled entity type")

        self._indices[et] = idx
        return idx

    def search(
        self,
        entity_type: str,
        term: str,
        *,
        threshold: float = 0.6,
        top_k: int = 5,
    ) -> Tuple[List[str], List[float]]:
        idx = self._get_index(entity_type)
        return lookup_ids(term, index=idx, threshold=threshold, top_k=top_k)


def main() -> None:
    import sys
    if len(sys.argv) < 3:
        print("Usage: python -m clinpgx_lookup.term_lookup <entity_type> <term...> [threshold] [top_k]")
        raise SystemExit(1)
    entity_type = sys.argv[1]
    args = sys.argv[2:]
    try:
        maybe_k = int(args[-1])
        maybe_t = float(args[-2])
        term = " ".join(args[:-2])
        threshold = maybe_t
        top_k = maybe_k
    except Exception:
        term = " ".join(args)
        threshold = 0.6
        top_k = 5

    lookup = ClinPGxTermLookup()
    ids, scores = lookup.search(entity_type, term, threshold=threshold, top_k=top_k)
    for acc, sc in zip(ids, scores):
        print(f"{acc}\t{sc:.3f}")


if __name__ == "__main__":
    main()
