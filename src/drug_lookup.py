import csv
import os
from typing import Optional, Tuple
from difflib import SequenceMatcher

# Increase CSV field size limit to handle large fields
csv.field_size_limit(1000000)


def find_drug_accession(drug_name: str, threshold: float = 0.6) -> Optional[str]:
    """
    Find the PharmGKB accession ID for a drug using fuzzy string matching.
    
    Args:
        drug_name: The drug name to search for (generic name or trade name)
        threshold: Minimum similarity score (0.0 to 1.0) for a match to be considered
        
    Returns:
        PharmGKB accession ID if a probable match is found, None otherwise
    """
    if not drug_name or not isinstance(drug_name, str):
        return None
    
    # Get the path to the drugs.tsv file relative to this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    tsv_path = os.path.join(project_root, 'data', 'drugs', 'drugs.tsv')
    
    if not os.path.exists(tsv_path):
        return None
    
    drug_name_lower = drug_name.lower().strip()
    best_match = None
    best_score = 0.0
    
    try:
        with open(tsv_path, 'r', encoding='utf-8') as file:
            reader = csv.reader(file, delimiter='\t')
            next(reader)  # Skip header row
            
            for row in reader:
                if len(row) < 4:
                    continue
                
                accession_id = row[0]
                name = row[1] if row[1] else ""
                generic_names = row[2] if row[2] else ""
                trade_names = row[3] if row[3] else ""
                
                # Collect all possible names to check
                names_to_check = []
                
                # Add main name
                if name:
                    names_to_check.append(name.lower().strip())
                
                # Add generic names (comma-separated)
                if generic_names:
                    for gen_name in generic_names.split(','):
                        names_to_check.append(gen_name.lower().strip())
                
                # Add trade names (comma-separated)
                if trade_names:
                    for trade_name in trade_names.split(','):
                        names_to_check.append(trade_name.lower().strip())
                
                # Check similarity with each name
                for check_name in names_to_check:
                    if not check_name:
                        continue
                    
                    # Exact match gets highest priority
                    if check_name == drug_name_lower:
                        return accession_id
                    
                    # Calculate similarity score
                    similarity = SequenceMatcher(None, drug_name_lower, check_name).ratio()
                    
                    if similarity > best_score:
                        best_score = similarity
                        best_match = accession_id
    
    except Exception:
        return None
    
    # Return the best match if it meets the threshold
    if best_score >= threshold:
        return best_match
    
    return None


def find_drug_with_score(drug_name: str, threshold: float = 0.6) -> Optional[Tuple[str, float]]:
    """
    Find the PharmGKB accession ID for a drug with the similarity score.
    
    Args:
        drug_name: The drug name to search for
        threshold: Minimum similarity score for a match to be considered
        
    Returns:
        Tuple of (accession_id, similarity_score) if found, None otherwise
    """
    if not drug_name or not isinstance(drug_name, str):
        return None
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    tsv_path = os.path.join(project_root, 'data', 'drugs', 'drugs.tsv')
    
    if not os.path.exists(tsv_path):
        return None
    
    drug_name_lower = drug_name.lower().strip()
    best_match = None
    best_score = 0.0
    
    try:
        with open(tsv_path, 'r', encoding='utf-8') as file:
            reader = csv.reader(file, delimiter='\t')
            next(reader)  # Skip header row
            
            for row in reader:
                if len(row) < 4:
                    continue
                
                accession_id = row[0]
                name = row[1] if row[1] else ""
                generic_names = row[2] if row[2] else ""
                trade_names = row[3] if row[3] else ""
                
                names_to_check = []
                
                if name:
                    names_to_check.append(name.lower().strip())
                
                if generic_names:
                    for gen_name in generic_names.split(','):
                        names_to_check.append(gen_name.lower().strip())
                
                if trade_names:
                    for trade_name in trade_names.split(','):
                        names_to_check.append(trade_name.lower().strip())
                
                for check_name in names_to_check:
                    if not check_name:
                        continue
                    
                    if check_name == drug_name_lower:
                        return (accession_id, 1.0)
                    
                    similarity = SequenceMatcher(None, drug_name_lower, check_name).ratio()
                    
                    if similarity > best_score:
                        best_score = similarity
                        best_match = accession_id
    
    except Exception:
        return None
    
    if best_score >= threshold:
        return (best_match, best_score)
    
    return None