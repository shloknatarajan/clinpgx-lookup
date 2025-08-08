"""
ClinPGx Lookup - Fuzzy term lookup for PharmGKB data

This package provides fast, fuzzy string matching for PharmGKB terms across
drugs, genes, phenotypes, variants, and alleles. It uses token-sorted similarity
matching with configurable thresholds and intelligent caching for optimal performance.

Main Classes:
    ClinPGxTermLookup: Unified interface for all entity types
    
Usage Examples:
    Basic lookup:
    >>> from clinpgx_lookup import ClinPGxTermLookup
    >>> lookup = ClinPGxTermLookup()
    >>> matches = lookup.search("drug", "abacavir")
    >>> print(f"Found: {matches[0].id} (score: {matches[0].score:.3f})")
    
    With custom parameters:
    >>> matches = lookup.search("gene", "cyp2d", threshold=0.7, top_k=3)
    
    Legacy functions (for backward compatibility):
    >>> from clinpgx_lookup import drug_lookup
    >>> ids, scores = drug_lookup("fluoxetine")

Performance Features:
    - Intelligent caching with automatic cache invalidation
    - Progress bars for initial index building
    - Memory-efficient lazy loading
    - Fast exact match detection
    - Optimized fuzzy search with early termination

Data Validation:
    - Built-in PharmGKB data structure validation
    - File integrity checking with checksums
    - Detailed error reporting and warnings
"""

from .term_lookup import ClinPGxTermLookup, ClinPGxMatch
from .drug_lookup import lookup_drug_ids, drug_lookup
from .gene_lookup import lookup_gene_ids, gene_lookup
from .phenotype_lookup import lookup_phenotype_ids, phenotype_lookup
from .variant_lookup import lookup_variant_ids, variant_lookup
from .allele_lookup import lookup_allele_ids, allele_lookup

# Version info
__version__ = "0.1.0"
__author__ = "Shlok Natarajan"
__email__ = "shlok.natarajan@gmail.com"

__all__ = [
    "ClinPGxTermLookup",
    "ClinPGxMatch",
    "lookup_drug_ids",
    "drug_lookup", 
    "lookup_gene_ids",
    "gene_lookup",
    "lookup_phenotype_ids",
    "phenotype_lookup",
    "lookup_variant_ids",
    "variant_lookup",
    "lookup_allele_ids",
    "allele_lookup",
    "__version__",
    "__author__", 
    "__email__",
]

