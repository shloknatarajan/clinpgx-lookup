from __future__ import annotations

import re
import difflib
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple, Optional, Iterator
import os
from contextlib import contextmanager, nullcontext
from importlib.resources import files, as_file

import pandas as pd


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
    name_to_ids: Dict[str, set]
    candidates: List[str]

    @classmethod
    def build_from_tsv(
        cls,
        tsv_path: Path,
        *,
        id_column: str,
        primary_name_columns: Sequence[str],
        list_name_columns: Sequence[str] | None = None,
    ) -> "NameIndex":
        if list_name_columns is None:
            list_name_columns = []

        df = pd.read_csv(tsv_path, sep="\t", dtype=str, keep_default_na=False, na_values=[""])
        if id_column not in df.columns:
            raise ValueError(f"Expected column '{id_column}' in {tsv_path}")

        name_to_ids: Dict[str, set] = {}

        for _, row in df.iterrows():
            acc = row.get(id_column, "").strip()
            if not acc:
                continue

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
        return cls(name_to_ids=name_to_ids, candidates=candidates)

    def save(self, pkl_path: Path) -> None:
        pkl_path.parent.mkdir(parents=True, exist_ok=True)
        pd.to_pickle({"name_to_ids": self.name_to_ids, "candidates": self.candidates}, pkl_path)

    @classmethod
    def load_or_build(
        cls,
        *,
        tsv_path: Path,
        pkl_path: Path,
        id_column: str,
        primary_name_columns: Sequence[str],
        list_name_columns: Sequence[str] | None = None,
    ) -> "NameIndex":
        if pkl_path.exists():
            obj = pd.read_pickle(pkl_path)
            if isinstance(obj, dict) and "name_to_ids" in obj and "candidates" in obj:
                return cls(name_to_ids=obj["name_to_ids"], candidates=obj["candidates"])
        idx = cls.build_from_tsv(
            tsv_path,
            id_column=id_column,
            primary_name_columns=primary_name_columns,
            list_name_columns=list_name_columns,
        )
        try:
            idx.save(pkl_path)
        except Exception:
            pass
        return idx


def lookup_ids(
    query: str,
    *,
    index: NameIndex,
    threshold: float = 0.6,
    top_k: int = 5,
) -> tuple[list[str], list[float]]:
    if not isinstance(query, str) or not query.strip():
        return [], []

    norm_q = normalize_name(query)
    if norm_q in index.name_to_ids:
        ids = sorted(index.name_to_ids[norm_q])[:top_k]
        return ids, [1.0] * len(ids)

    scored: List[tuple[str, float]] = []
    for cand in index.candidates:
        s = similarity(norm_q, cand)
        if s >= threshold:
            scored.append((cand, s))

    if not scored:
        return [], []

    id_to_best: Dict[str, float] = {}
    for cand, s in scored:
        for acc in index.name_to_ids.get(cand, ()):  # cand is normalized
            if acc not in id_to_best or s > id_to_best[acc]:
                id_to_best[acc] = s

    items = sorted(id_to_best.items(), key=lambda kv: (-kv[1], kv[0]))
    top = items[: max(0, top_k)]
    ids = [acc for acc, _ in top]
    scores = [float(score) for _, score in top]
    return ids, scores


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
) -> NameIndex:
    cache_dir = _default_cache_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)
    pkl_path = cache_dir / cache_basename

    # Try load cached
    if pkl_path.exists():
        obj = pd.read_pickle(pkl_path)
        if isinstance(obj, dict) and "name_to_ids" in obj and "candidates" in obj:
            return NameIndex(name_to_ids=obj["name_to_ids"], candidates=obj["candidates"])

    # Build from resource TSV
    with open_resource_tsv(resource_relpath) as tsv_path:
        idx = NameIndex.build_from_tsv(
            tsv_path=tsv_path,
            id_column=id_column,
            primary_name_columns=primary_name_columns,
            list_name_columns=list_name_columns,
        )
    try:
        idx.save(pkl_path)
    except Exception:
        pass
    return idx
