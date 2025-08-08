"""
Unified ClinPGx Term Lookup

This module provides a unified interface for fuzzy matching terms against PharmGKB
datasets including drugs, genes, phenotypes, variants, and alleles. It uses 
token-sorted string similarity with configurable thresholds and caching for
optimal performance.

Classes:
    ClinPGxTermLookup: Main class for performing term lookups across all entity types
    
Functions:
    main: Command-line interface for the lookup tool
    
Example:
    Basic usage:
    >>> from clinpgx_lookup import ClinPGxTermLookup
    >>> lookup = ClinPGxTermLookup()
    >>> matches = lookup.search("drug", "abacavir", threshold=0.6, top_k=5)
    >>> print(f"Found {len(matches)} matches: [m.id for m in matches]")
    
    Command-line usage:
    $ clinpgx-lookup drug "abacavir"
    PA448710    1.000
    
    $ clinpgx-lookup gene "CYP2D6" 0.8 3
    PA128    1.000
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

from .lookup_utils import NameIndex, lookup_ids, load_or_build_index_from_resource
from dataclasses import dataclass

@dataclass
class ClinPGxMatch:
    id: str
    name: str
    score: float

class ClinPGxTermLookup:
    """
    Unified term lookup with per-type cached indices.
    
    This class provides a single interface for looking up PharmGKB identifiers
    across multiple entity types (drugs, genes, phenotypes, variants, alleles).
    It uses fuzzy string matching with configurable similarity thresholds and
    maintains cached indices for optimal performance.
    
    The lookup process:
    1. Normalizes input terms (lowercase, remove special chars, token sort)
    2. Attempts exact match first for best performance
    3. Falls back to fuzzy matching using string similarity
    4. Returns top-k results sorted by similarity score
    
    Attributes:
        _indices: Dictionary mapping entity types to their NameIndex instances
        
    Example:
        >>> lookup = ClinPGxTermLookup()
        >>> matches = lookup.search("drug", "fluoxetine")
        >>> print(f"Found {len(matches)} matches")
        
        >>> # Search with custom parameters
        >>> matches = lookup.search("gene", "cyp", threshold=0.7, top_k=10)
        
        >>> # Disable caching to force fresh data load for this search
        >>> matches = lookup.search("drug", "aspirin", cache=False)
    """

    def __init__(self) -> None:
        """Initialize the lookup engine with empty indices cache."""
        self._indices: Dict[str, NameIndex] = {}

    def _canonical_type(self, entity_type: str) -> str:
        """
        Normalize entity type string to canonical form.
        
        Args:
            entity_type: Entity type string (case insensitive, accepts plurals)
            
        Returns:
            Canonical entity type string
            
        Raises:
            ValueError: If entity_type is not recognized
            
        Example:
            >>> lookup = ClinPGxTermLookup()
            >>> lookup._canonical_type("DRUGS")  # "drug"
            >>> lookup._canonical_type("Genes")  # "gene"
        """
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
            raise ValueError(
                f"entity_type must be one of: {', '.join(sorted(set(alias.values())))}. "
                f"Got: '{entity_type}'"
            )
        return alias[t]

    def _get_index(self, entity_type: str, *, use_cache: bool = True) -> NameIndex:
        """
        Get or create NameIndex for the specified entity type.
        
        This method lazy-loads indices on first access, building them from 
        PharmGKB TSV files and caching for subsequent use.
        
        Args:
            entity_type: Type of entity to get index for
            use_cache: Whether to use cached indices (default True). If False, 
                      forces rebuild of indices from source data files.
            
        Returns:
            NameIndex instance for the entity type
            
        Raises:
            ValueError: If entity_type is not supported
            FileNotFoundError: If required data files are not found
        """
        et = self._canonical_type(entity_type)
        if use_cache and et in self._indices:
            return self._indices[et]

        # Configure dataset columns per type
        if et == "drug":
            idx = load_or_build_index_from_resource(
                resource_relpath="data/drugs/drugs.tsv",
                cache_basename="drugs_name_index.pkl",
                id_column="PharmGKB Accession Id",
                primary_name_columns=["Name"],
                list_name_columns=["Generic Names", "Trade Names", "Brand Mixtures"],
                force_rebuild=not use_cache,
            )
        elif et == "gene":
            idx = load_or_build_index_from_resource(
                resource_relpath="data/genes/genes.tsv",
                cache_basename="genes_name_index.pkl",
                id_column="PharmGKB Accession Id",
                primary_name_columns=["Name", "Symbol"],
                list_name_columns=["Alternate Names", "Alternate Symbols"],
                force_rebuild=not use_cache,
            )
        elif et == "phenotype":
            idx = load_or_build_index_from_resource(
                resource_relpath="data/phenotypes/phenotypes.tsv",
                cache_basename="phenotypes_name_index.pkl",
                id_column="PharmGKB Accession Id",
                primary_name_columns=["Name"],
                list_name_columns=["Alternate Names"],
                force_rebuild=not use_cache,
            )
        elif et == "variant":
            idx = load_or_build_index_from_resource(
                resource_relpath="data/variants/variants.tsv",
                cache_basename="variants_name_index.pkl",
                id_column="Variant ID",
                primary_name_columns=["Variant Name"],
                list_name_columns=["Synonyms"],
                force_rebuild=not use_cache,
            )
        elif et == "allele":
            idx = load_or_build_index_from_resource(
                resource_relpath="data/variants/variants.tsv",
                cache_basename="alleles_name_index.pkl",
                id_column="Variant ID",
                primary_name_columns=["Variant Name"],
                list_name_columns=["Synonyms"],
                force_rebuild=not use_cache,
            )
        else:
            raise AssertionError("Unhandled entity type")

        if use_cache:
            self._indices[et] = idx
        return idx

    def clear_cache(self, entity_type: str = None) -> None:
        """
        Clear cached indices for improved memory management.
        
        Args:
            entity_type: Specific entity type to clear cache for. If None, clears all caches.
            
        Example:
            >>> lookup = ClinPGxTermLookup()
            >>> lookup.clear_cache("drug")  # Clear only drug cache
            >>> lookup.clear_cache()        # Clear all caches
        """
        if entity_type is None:
            self._indices.clear()
        else:
            et = self._canonical_type(entity_type)
            self._indices.pop(et, None)

    def search(
        self,
        entity_type: str,
        term: str,
        *,
        threshold: float = 0.6,
        top_k: int = 5,
        cache: bool = True,
    ) -> List[ClinPGxMatch]:
        """
        Search for PharmGKB IDs matching the given term.
        
        Performs fuzzy string matching against normalized entity names, returning
        the most similar matches above the specified threshold.
        
        Args:
            entity_type: Type of entity to search ('drug', 'gene', 'phenotype', 'variant', 'allele')
            term: Search term (will be normalized automatically)
            threshold: Minimum similarity score (0.0-1.0). Higher values = more strict matching
            top_k: Maximum number of results to return
            cache: Whether to use cached indices (default True). If False, forces rebuild from source data
            
        Returns:
            List of ClinPGxMatch objects with id, name, and score attributes
            
        Example:
            >>> lookup = ClinPGxTermLookup()
            >>> matches = lookup.search("drug", "aspirin", threshold=0.8)
            >>> for match in matches:
            ...     print(f"{match.id}: {match.name} ({match.score:.3f})")
            PA448515: aspirin (1.000)
            
            >>> # Search genes with relaxed threshold
            >>> matches = lookup.search("gene", "cyp2d", threshold=0.5, top_k=3)
            
            >>> # Force rebuild from source data for this search
            >>> matches = lookup.search("drug", "aspirin", cache=False)
        """
        idx = self._get_index(entity_type, use_cache=cache)
        ids, matched_names, scores = lookup_ids(term, index=idx, threshold=threshold, top_k=top_k)
        return [ClinPGxMatch(id=id_, name=name, score=score) 
                for id_, name, score in zip(ids, matched_names, scores)]


def main() -> None:
    """
    Command-line interface for ClinPGx term lookup.
    
    Usage:
        clinpgx-lookup <entity_type> <term> [threshold] [top_k]
        
    Args:
        entity_type: One of 'drug', 'gene', 'phenotype', 'variant', 'allele'
        term: Search term (can be multiple words)
        threshold: Minimum similarity score (0.0-1.0), default 0.6
        top_k: Maximum results to return, default 5
        
    Examples:
        clinpgx-lookup drug "abacavir"
        clinpgx-lookup gene "CYP2D6" 0.8
        clinpgx-lookup drug "fluoxetine" 0.7 10
    """
    import sys
    if len(sys.argv) < 3:
        print("Usage: clinpgx-lookup <entity_type> <term...> [threshold] [top_k]")
        print()
        print("Arguments:")
        print("  entity_type  One of: drug, gene, phenotype, variant, allele")
        print("  term         Search term (can be multiple words)")
        print("  threshold    Minimum similarity score (0.0-1.0), default 0.6")
        print("  top_k        Maximum results to return, default 5")
        print()
        print("Examples:")
        print("  clinpgx-lookup drug abacavir")
        print("  clinpgx-lookup gene 'CYP2D6' 0.8")  
        print("  clinpgx-lookup drug fluoxetine 0.7 10")
        raise SystemExit(1)
    
    entity_type = sys.argv[1]
    args = sys.argv[2:]
    
    # Parse arguments: try to extract threshold and top_k from end
    try:
        maybe_k = int(args[-1])
        maybe_t = float(args[-2])
        term = " ".join(args[:-2])
        threshold = maybe_t
        top_k = maybe_k
    except (ValueError, IndexError):
        term = " ".join(args)
        threshold = 0.6
        top_k = 5

    try:
        lookup = ClinPGxTermLookup()
        ids, scores = lookup.search(entity_type, term, threshold=threshold, top_k=top_k)
        
        if not ids:
            print(f"No matches found for '{term}' in {entity_type} data (threshold={threshold})")
            raise SystemExit(1)
            
        for acc, sc in zip(ids, scores):
            print(f"{acc}\t{sc:.3f}")
            
    except ValueError as e:
        print(f"Error: {e}")
        raise SystemExit(1)
    except FileNotFoundError as e:
        print(f"Data not found: {e}")
        print("Run 'clinpgx-setup --help' to set up data files.")
        raise SystemExit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
