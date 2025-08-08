"""
Data validation utilities for PharmGKB data integrity and structure verification.

This module provides functionality to validate the structure and integrity of
PharmGKB data files used for term normalization.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import warnings

import pandas as pd
from pydantic import BaseModel, Field, ValidationError


class DatasetSchema(BaseModel):
    """Schema definition for PharmGKB dataset validation."""
    
    required_columns: List[str] = Field(..., description="Required columns that must be present")
    optional_columns: List[str] = Field(default_factory=list, description="Optional columns")
    id_column: str = Field(..., description="Primary ID column name")
    name_columns: List[str] = Field(..., description="Columns containing searchable names")
    min_rows: int = Field(default=1, description="Minimum number of rows expected")
    

class ValidationResult(BaseModel):
    """Result of data validation."""
    
    is_valid: bool = Field(..., description="Whether validation passed")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    file_path: str = Field(..., description="Path to validated file")
    row_count: int = Field(default=0, description="Number of rows in dataset")
    checksum: Optional[str] = Field(default=None, description="File checksum for integrity")


# Dataset schemas for each PharmGKB data type
DATASET_SCHEMAS: Dict[str, DatasetSchema] = {
    "drugs": DatasetSchema(
        required_columns=["PharmGKB Accession Id", "Name"],
        optional_columns=["Generic Names", "Trade Names", "Brand Mixtures", "Type", 
                         "Cross-references", "SMILES", "InChI"],
        id_column="PharmGKB Accession Id",
        name_columns=["Name", "Generic Names", "Trade Names", "Brand Mixtures"],
        min_rows=100  # Expect at least 100 drugs
    ),
    "genes": DatasetSchema(
        required_columns=["PharmGKB Accession Id", "Name", "Symbol"],
        optional_columns=["Alternate Names", "Alternate Symbols", "Is VIP", 
                         "Has Variant Annotation", "Cross-references"],
        id_column="PharmGKB Accession Id",
        name_columns=["Name", "Symbol", "Alternate Names", "Alternate Symbols"],
        min_rows=50  # Expect at least 50 genes
    ),
    "phenotypes": DatasetSchema(
        required_columns=["PharmGKB Accession Id", "Name"],
        optional_columns=["Alternate Names", "Cross-references", "Type"],
        id_column="PharmGKB Accession Id", 
        name_columns=["Name", "Alternate Names"],
        min_rows=50  # Expect at least 50 phenotypes
    ),
    "variants": DatasetSchema(
        required_columns=["Variant ID", "Variant Name"],
        optional_columns=["Synonyms", "Gene", "Location", "Type"],
        id_column="Variant ID",
        name_columns=["Variant Name", "Synonyms"],
        min_rows=100  # Expect at least 100 variants
    )
}


def calculate_file_checksum(file_path: Path) -> str:
    """Calculate SHA-256 checksum of a file."""
    hash_sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()


def validate_dataset_structure(
    df: pd.DataFrame, 
    schema: DatasetSchema, 
    file_path: Path
) -> ValidationResult:
    """
    Validate the structure of a PharmGKB dataset against its schema.
    
    Args:
        df: DataFrame to validate
        schema: Expected schema for the dataset
        file_path: Path to the source file
        
    Returns:
        ValidationResult with validation status and details
    """
    result = ValidationResult(
        is_valid=True,
        file_path=str(file_path),
        row_count=len(df),
        checksum=calculate_file_checksum(file_path)
    )
    
    # Check required columns
    missing_required = set(schema.required_columns) - set(df.columns)
    if missing_required:
        result.errors.append(f"Missing required columns: {missing_required}")
        result.is_valid = False
        
    # Check ID column exists and has unique values
    if schema.id_column in df.columns:
        null_ids = df[schema.id_column].isnull().sum()
        if null_ids > 0:
            result.errors.append(f"Found {null_ids} null values in ID column '{schema.id_column}'")
            result.is_valid = False
            
        duplicate_ids = df[schema.id_column].duplicated().sum()
        if duplicate_ids > 0:
            result.errors.append(f"Found {duplicate_ids} duplicate values in ID column '{schema.id_column}'")
            result.is_valid = False
    else:
        result.errors.append(f"ID column '{schema.id_column}' not found")
        result.is_valid = False
        
    # Check minimum row count
    if len(df) < schema.min_rows:
        result.warnings.append(f"Dataset has {len(df)} rows, expected at least {schema.min_rows}")
        
    # Check name columns have some non-null values
    for name_col in schema.name_columns:
        if name_col in df.columns:
            null_count = df[name_col].isnull().sum()
            if null_count == len(df):
                result.warnings.append(f"Name column '{name_col}' is entirely null")
            elif null_count > len(df) * 0.8:  # More than 80% null
                result.warnings.append(f"Name column '{name_col}' is mostly null ({null_count}/{len(df)} rows)")
                
    # Check for unexpected columns (informational)
    all_expected = set(schema.required_columns + schema.optional_columns)
    unexpected = set(df.columns) - all_expected
    if unexpected:
        result.warnings.append(f"Found unexpected columns: {unexpected}")
        
    return result


def validate_data_file(file_path: Path, dataset_type: str) -> ValidationResult:
    """
    Validate a single PharmGKB data file.
    
    Args:
        file_path: Path to the TSV file to validate
        dataset_type: Type of dataset ('drugs', 'genes', 'phenotypes', 'variants')
        
    Returns:
        ValidationResult with validation status and details
    """
    if dataset_type not in DATASET_SCHEMAS:
        return ValidationResult(
            is_valid=False,
            errors=[f"Unknown dataset type: {dataset_type}"],
            file_path=str(file_path)
        )
        
    if not file_path.exists():
        return ValidationResult(
            is_valid=False,
            errors=[f"File does not exist: {file_path}"],
            file_path=str(file_path)
        )
        
    try:
        # Load the dataset
        df = pd.read_csv(file_path, sep='\t', low_memory=False)
        
        # Validate against schema
        schema = DATASET_SCHEMAS[dataset_type]
        return validate_dataset_structure(df, schema, file_path)
        
    except Exception as e:
        return ValidationResult(
            is_valid=False,
            errors=[f"Failed to load or validate file: {str(e)}"],
            file_path=str(file_path)
        )


def validate_data_directory(data_dir: Path) -> Dict[str, ValidationResult]:
    """
    Validate all PharmGKB data files in a directory.
    
    Args:
        data_dir: Directory containing PharmGKB data subdirectories
        
    Returns:
        Dictionary mapping dataset type to validation result
    """
    results = {}
    
    for dataset_type in DATASET_SCHEMAS.keys():
        file_path = data_dir / dataset_type / f"{dataset_type}.tsv"
        results[dataset_type] = validate_data_file(file_path, dataset_type)
        
    return results


def print_validation_summary(results: Dict[str, ValidationResult]) -> None:
    """Print a summary of validation results."""
    print("PharmGKB Data Validation Summary")
    print("=" * 40)
    
    total_files = len(results)
    valid_files = sum(1 for r in results.values() if r.is_valid)
    
    print(f"Files validated: {total_files}")
    print(f"Valid files: {valid_files}")
    print(f"Files with errors: {total_files - valid_files}")
    print()
    
    for dataset_type, result in results.items():
        status = "✓" if result.is_valid else "✗"
        print(f"{status} {dataset_type:12} ({result.row_count:,} rows)")
        
        if result.errors:
            for error in result.errors:
                print(f"    ERROR: {error}")
                
        if result.warnings:
            for warning in result.warnings:
                print(f"    WARNING: {warning}")
                
        if result.checksum:
            print(f"    Checksum: {result.checksum[:16]}...")
        print()