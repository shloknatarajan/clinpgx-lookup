
import pandas as pd
from typing import List, Optional
from difflib import SequenceMatcher

def general_search(df: pd.DataFrame, query: str, column_name: str, id_column: str, threshold: float = 0.8, top_k: int = 5, keep_columns: Optional[List[str]] = None) -> List[str]:
    """
    Takes a dataframe and returns the top_k matches for the query based on the column_name and id_column.

    Args:
        df (pd.DataFrame): The dataframe to search.
        query (str): The query to search for.
        column_name (str): The name of the column to search in.
        threshold (float, optional): The threshold for the fuzzy match. Defaults to 0.8.
        top_k (int, optional): The number of top matches to return. Defaults to 5.
        keep_columns (List[str], optional): List of column names to keep in results. If None, keeps all columns.
    """
    if df.empty or query.strip() == "":
        return []
    
    query_lower = query.lower().strip()
    matches = []
    
    for idx, row in df.iterrows():
        if pd.isna(row[column_name]):
            continue
            
        text = str(row[column_name]).lower().strip()
        similarity = calc_similarity(query_lower, text)
        
        if similarity >= threshold:
            row_dict = row.to_dict()
            if keep_columns is not None:
                row_dict = {col: row_dict.get(col) for col in keep_columns if col in row_dict}
            row_dict['score'] = similarity
            matches.append(row_dict)
    
    matches.sort(key=lambda x: x['score'], reverse=True)
    return matches
    
def calc_similarity(query: str, text: str) -> float:
    return SequenceMatcher(None, query.lower().strip(), text.lower().strip()).ratio()