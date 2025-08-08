from __future__ import annotations

import re
import difflib
import mmap
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple, Optional, Iterator, Union
import os
import time
import warnings
from contextlib import contextmanager, nullcontext
from importlib.resources import files, as_file

import pandas as pd
try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False
    # Fallback progress indicator
    class tqdm:
        def __init__(self, iterable=None, desc="", total=None, disable=False):
            self.iterable = iterable
            self.desc = desc
            self.total = total or (len(iterable) if hasattr(iterable, '__len__') else None)
            self.n = 0
            self.disable = disable
            if not disable and desc:
                print(f"{desc}...")
        
        def __iter__(self):
            for item in self.iterable:
                yield item
                self.update(1)
        
        def update(self, n=1):
            self.n += n
        
        def __enter__(self):
            return self
        
        def __exit__(self, *args):
            if not self.disable:
                print(f"Completed: {self.desc}")


def normalize_name(name: str) -> str:
    if not isinstance(name, str):
        return ""
    s = name.strip().lower()
    s = (
        s.replace("\u2019", "'")
        .replace("\u2018", "'")
        .replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u00ae", "")
        .replace("\u2122", "")
    )
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def token_sort(text: str) -> str:
    tokens = [t for t in normalize_name(text).split(" ") if t]
    tokens.sort()
    return " ".join(tokens)


def similarity(a: str, b: str) -> float:
    aa = token_sort(a)
    bb = token_sort(b)
    if not aa or not bb:
        return 0.0
    return difflib.SequenceMatcher(None, aa, bb).ratio()


def split_synonyms(field: str | float | None) -> List[str]:
    if field is None or not isinstance(field, str):
        return []
    text = field.strip()
    if not text:
        return []
    text = text.replace('""', '"').strip('"')
    parts = re.split(r"[,;/|]", text)
    names: List[str] = []
    for p in parts:
        p = p.strip().strip('"').strip()
        if p:
            names.append(p)
    return names


@dataclass
class NameIndex:
    """Optimized name index with lazy loading and caching support."""
    name_to_ids: Dict[str, set]
    candidates: List[str]
    id_to_primary_name: Dict[str, str]
    _metadata: Optional[Dict[str, Union[str, int, float]]] = None

    def __post_init__(self):
        """Initialize metadata if not provided."""
        if self._metadata is None:
            self._metadata = {
                'created_at': time.time(),
                'total_names': len(self.name_to_ids),
                'total_candidates': len(self.candidates),
                'version': '1.0'
            }

    @property
    def metadata(self) -> Dict[str, Union[str, int, float]]:
        """Get index metadata."""
        return self._metadata or {}

    def get_stats(self) -> Dict[str, Union[str, int]]:
        """Get human-readable statistics about the index."""
        return {
            'Total unique names': len(self.name_to_ids),
            'Total candidates': len(self.candidates),
            'Average IDs per name': round(sum(len(ids) for ids in self.name_to_ids.values()) / len(self.name_to_ids), 2) if self.name_to_ids else 0,
            'Created': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.metadata.get('created_at', 0))),
        }

    @classmethod
    def build_from_tsv(
        cls,
        tsv_path: Path,
        *,
        id_column: str,
        primary_name_columns: Sequence[str],
        list_name_columns: Sequence[str] | None = None,
        show_progress: bool = True,
    ) -> "NameIndex":
        if list_name_columns is None:
            list_name_columns = []

        start_time = time.time()
        if show_progress and not os.environ.get('CLINPGX_QUIET'):
            print(f"Loading data from {tsv_path.name}...")
        
        # Read with progress indication for large files
        try:
            df = pd.read_csv(tsv_path, sep="\t", dtype=str, keep_default_na=False, na_values=[""])
        except Exception as e:
            raise ValueError(f"Failed to read TSV file {tsv_path}: {e}")
        
        if id_column not in df.columns:
            raise ValueError(f"Expected column '{id_column}' in {tsv_path}")

        name_to_ids: Dict[str, set] = {}
        id_to_primary_name: Dict[str, str] = {}
        
        # Progress bar for index building
        desc = f"Building index from {tsv_path.name}"
        disable_progress = os.environ.get('CLINPGX_QUIET') or not show_progress
        
        with tqdm(df.iterrows(), desc=desc, total=len(df), disable=disable_progress) as pbar:
            for _, row in pbar:
                acc = row.get(id_column, "").strip()
                if not acc:
                    continue

                # Store the primary name (first non-empty name from primary_name_columns)
                primary_name = None
                for col in primary_name_columns:
                    if col in df.columns:
                        val = row.get(col)
                        if isinstance(val, str) and val.strip():
                            if primary_name is None:
                                primary_name = val.strip()
                                break
                
                if primary_name:
                    id_to_primary_name[acc] = primary_name

                all_names: List[str] = []
                for col in primary_name_columns:
                    if col in df.columns:
                        val = row.get(col)
                        if isinstance(val, str) and val.strip():
                            all_names.append(val.strip())

                for col in list_name_columns:
                    if col in df.columns:
                        all_names.extend(split_synonyms(row.get(col)))

                seen = set()
                for nm in all_names:
                    norm = normalize_name(nm)
                    if not norm or norm in seen:
                        continue
                    seen.add(norm)
                    name_to_ids.setdefault(norm, set()).add(acc)

        candidates = sorted(name_to_ids.keys())
        
        # Performance timing
        build_time = time.time() - start_time
        metadata = {
            'created_at': time.time(),
            'total_names': len(name_to_ids),
            'total_candidates': len(candidates),
            'build_time_seconds': round(build_time, 2),
            'source_file': str(tsv_path.name),
            'version': '1.0'
        }
        
        if show_progress and not os.environ.get('CLINPGX_QUIET'):
            print(f"Index built in {build_time:.2f}s: {len(name_to_ids)} unique names, {len(candidates)} candidates")
        
        return cls(name_to_ids=name_to_ids, candidates=candidates, id_to_primary_name=id_to_primary_name, _metadata=metadata)

    def save(self, pkl_path: Path) -> None:
        """Save index to pickle file with metadata."""
        pkl_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "name_to_ids": self.name_to_ids,
            "candidates": self.candidates,
            "id_to_primary_name": self.id_to_primary_name,
            "metadata": self._metadata
        }
        pd.to_pickle(data, pkl_path)
        
        if not os.environ.get('CLINPGX_QUIET'):
            size_mb = pkl_path.stat().st_size / (1024 * 1024)
            print(f"Index saved to {pkl_path.name} ({size_mb:.1f} MB)")

    @classmethod
    def load_or_build(
        cls,
        *,
        tsv_path: Path,
        pkl_path: Path,
        id_column: str,
        primary_name_columns: Sequence[str],
        list_name_columns: Sequence[str] | None = None,
        force_rebuild: bool = False,
        show_progress: bool = True,
    ) -> "NameIndex":
        """Load index from cache or build from TSV with improved caching logic."""
        
        # Check if we should use cached version
        if not force_rebuild and pkl_path.exists():
            try:
                if not os.environ.get('CLINPGX_QUIET') and show_progress:
                    print(f"Loading cached index from {pkl_path.name}...")
                
                start_time = time.time()
                obj = pd.read_pickle(pkl_path)
                
                if isinstance(obj, dict) and "name_to_ids" in obj and "candidates" in obj:
                    # Check if TSV is newer than cache
                    if tsv_path.exists():
                        tsv_mtime = tsv_path.stat().st_mtime
                        pkl_mtime = pkl_path.stat().st_mtime
                        
                        if tsv_mtime > pkl_mtime:
                            if not os.environ.get('CLINPGX_QUIET') and show_progress:
                                print(f"TSV file is newer than cache, rebuilding...")
                        elif "id_to_primary_name" not in obj:
                            if not os.environ.get('CLINPGX_QUIET') and show_progress:
                                print(f"Cache missing id_to_primary_name field, rebuilding...")
                        else:
                            load_time = time.time() - start_time
                            metadata = obj.get("metadata", {})
                            
                            if not os.environ.get('CLINPGX_QUIET') and show_progress:
                                print(f"Index loaded in {load_time:.2f}s")
                                if metadata.get('build_time_seconds'):
                                    speedup = metadata['build_time_seconds'] / load_time
                                    print(f"Cache speedup: {speedup:.1f}x faster than building from scratch")
                            
                            return cls(
                                name_to_ids=obj["name_to_ids"],
                                candidates=obj["candidates"],
                                id_to_primary_name=obj.get("id_to_primary_name", {}),
                                _metadata=metadata
                            )
            except Exception as e:
                if show_progress and not os.environ.get('CLINPGX_QUIET'):
                    print(f"Failed to load cached index: {e}")
                    print("Rebuilding from TSV...")
        
        # Build from TSV
        idx = cls.build_from_tsv(
            tsv_path,
            id_column=id_column,
            primary_name_columns=primary_name_columns,
            list_name_columns=list_name_columns,
            show_progress=show_progress,
        )
        
        # Save to cache
        try:
            idx.save(pkl_path)
        except Exception as e:
            if show_progress and not os.environ.get('CLINPGX_QUIET'):
                warnings.warn(f"Failed to save index cache: {e}")
        
        return idx


def lookup_ids(
    query: str,
    *,
    index: NameIndex,
    threshold: float = 0.6,
    top_k: int = 5,
    exact_match_first: bool = True,
) -> tuple[list[str], list[str], list[float]]:
    """
    Optimized lookup with early termination and exact match prioritization.
    
    Args:
        query: Search term
        index: Name index to search
        threshold: Minimum similarity score (0.0-1.0)
        top_k: Maximum number of results
        exact_match_first: Whether to prioritize exact matches
        
    Returns:
        Tuple of (IDs, matched_names, similarity_scores)
    """
    if not isinstance(query, str) or not query.strip():
        return [], []

    norm_q = normalize_name(query)
    
    # Fast path: exact match with smart prioritization
    if norm_q in index.name_to_ids:
        ids = list(index.name_to_ids[norm_q])
        
        # For exact matches, find the shortest name associated with each ID
        # This helps prioritize single drugs (shorter names) over combination drugs
        id_to_shortest_match = {}
        for acc in ids:
            shortest_len = float('inf')
            shortest_name = norm_q
            
            # Check all candidate names that contain this ID
            for cand_name in index.candidates:
                if acc in index.name_to_ids.get(cand_name, set()):
                    if len(cand_name) < shortest_len:
                        shortest_len = len(cand_name)
                        shortest_name = cand_name
            
            id_to_shortest_match[acc] = (shortest_len, shortest_name)
        
        # Sort by: shortest associated name length, then by ID for reproducibility
        sorted_items = sorted(
            id_to_shortest_match.items(), 
            key=lambda x: (x[1][0], x[0])
        )
        
        ids = [acc for acc, _ in sorted_items[:top_k]]
        # Return the primary names from the TSV instead of the normalized query
        matched_names = [index.id_to_primary_name.get(acc, norm_q) for acc in ids]
        
        return ids, matched_names, [1.0] * len(ids)

    # Optimized fuzzy search with early termination
    scored: List[tuple[str, float]] = []
    best_score = 0.0
    
    # Use a more efficient search strategy for large candidate lists
    for cand in index.candidates:
        # Early termination optimization: skip candidates that are very different in length
        if abs(len(norm_q) - len(cand)) > max(len(norm_q), len(cand)) * (1 - threshold):
            continue
            
        s = similarity(norm_q, cand)
        if s >= threshold:
            scored.append((cand, s))
            best_score = max(best_score, s)
            
            # Early termination: if we found perfect matches and have enough results
            if s == 1.0 and len(scored) >= top_k:
                break

    if not scored:
        return [], [], []

    # Aggregate by ID and keep best score and matched name per ID
    id_to_best: Dict[str, Tuple[float, str]] = {}
    for cand, s in scored:
        for acc in index.name_to_ids.get(cand, ()):
            if acc not in id_to_best or s > id_to_best[acc][0]:
                id_to_best[acc] = (s, cand)

    # Sort by score (desc), prioritize shorter drug names (single drugs over combinations), then by ID (asc) for reproducible results
    items = sorted(id_to_best.items(), key=lambda kv: (-kv[1][0], len(kv[1][1].replace(" ", "")), kv[0]))
    top = items[:max(0, top_k)]
    
    ids = [acc for acc, _ in top]
    matched_names = [name for _, (_, name) in top]
    scores = [float(score) for _, (score, _) in top]
    return ids, matched_names, scores


# -------- Resource and cache helpers --------

def _default_cache_dir() -> Path:
    root = os.environ.get("CLINPGX_CACHE_DIR")
    if root:
        return Path(root)
    return Path.home() / ".cache" / "clinpgx_lookup"


@contextmanager
def open_resource_tsv(relpath: str) -> Iterator[Path]:
    """Yield a real filesystem Path for a TSV resource.

    Resolution order:
    1) Package data: clinpgx_lookup/<relpath>
    2) Env var: CLINPGX_DATA_DIR/<relpath>
    3) User cache: ~/.cache/clinpgx_lookup/<relpath>
    4) Dev repo relative: project_root/<relpath>
    """
    # 1) Packaged resource
    try:
        res = files("clinpgx_lookup").joinpath(relpath)
        if res.is_file():
            with as_file(res) as p:
                yield p
                return
    except Exception:
        pass

    # 2) Env var
    base = os.environ.get("CLINPGX_DATA_DIR")
    if base:
        # If relpath starts with 'data/', drop it for external dirs
        rel_sub = relpath.split("data/", 1)[-1]
        p = Path(base) / rel_sub
        if p.is_file():
            with nullcontext(p):
                yield p
                return

    # 3) User cache dir
    rel_sub = relpath.split("data/", 1)[-1]
    p = _default_cache_dir() / "data" / rel_sub
    if p.is_file():
        with nullcontext(p):
            yield p
            return

    # 4) Dev repo (two parents up from package dir)
    dev_root = Path(__file__).resolve().parents[2]
    p = dev_root / relpath
    if p.is_file():
        with nullcontext(p):
            yield p
            return

    # If nothing found, raise
    raise FileNotFoundError(f"Unable to locate resource TSV: {relpath}")


def load_or_build_index_from_resource(
    *,
    resource_relpath: str,
    cache_basename: str,
    id_column: str,
    primary_name_columns: Sequence[str],
    list_name_columns: Sequence[str] | None = None,
    force_rebuild: bool = False,
    show_progress: bool = None,
) -> NameIndex:
    """
    Load or build index from resource with improved caching and progress indication.
    
    Args:
        resource_relpath: Path to TSV resource relative to data root
        cache_basename: Basename for cache file
        id_column: Column containing unique IDs
        primary_name_columns: Primary name columns to index
        list_name_columns: Columns containing delimited synonym lists
        force_rebuild: Whether to force rebuild even if cache exists
        show_progress: Whether to show progress bars (None = auto-detect)
        
    Returns:
        NameIndex instance
    """
    if show_progress is None:
        show_progress = not os.environ.get('CLINPGX_QUIET')
        
    cache_dir = _default_cache_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)
    pkl_path = cache_dir / cache_basename

    # Build from resource TSV using enhanced load_or_build
    with open_resource_tsv(resource_relpath) as tsv_path:
        idx = NameIndex.load_or_build(
            tsv_path=tsv_path,
            pkl_path=pkl_path,
            id_column=id_column,
            primary_name_columns=primary_name_columns,
            list_name_columns=list_name_columns,
            force_rebuild=force_rebuild,
            show_progress=show_progress,
        )
    
    return idx
