from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import argparse
import sys
from importlib.resources import files


REQUIRED = {
    # Paths are relative to the "data" root for external dirs
    "drugs": ("drugs/drugs.tsv", ["PharmGKB Accession Id", "Name"]),
    "genes": ("genes/genes.tsv", ["PharmGKB Accession Id", "Name", "Symbol"]),
    "variants": ("variants/variants.tsv", ["Variant ID", "Variant Name"]),
    "phenotypes": ("phenotypes/phenotypes.tsv", ["PharmGKB Accession Id", "Name"]),
}


def _default_cache_dir() -> Path:
    root = os.environ.get("CLINPGX_CACHE_DIR")
    if root:
        return Path(root)
    return Path.home() / ".cache" / "clinpgx_lookup"


def _header_ok(path: Path, expected_any: List[str]) -> bool:
    try:
        with path.open("r", encoding="utf-8") as f:
            first = f.readline().rstrip("\n\r")
    except Exception:
        return False
    headers = first.split("\t") if first else []
    # For genes we allow either Name or Symbol to be present along with ID
    if "PharmGKB Accession Id" in expected_any:
        need_id = "PharmGKB Accession Id" in headers
        need_name_or_symbol = ("Name" in headers) or ("Symbol" in headers)
        return need_id and need_name_or_symbol
    else:
        return all(h in headers for h in expected_any)


@dataclass
class Location:
    label: str
    base: Optional[Path]


def _locations(source: Optional[str]) -> List[Location]:
    locs: List[Location] = []
    if source:
        locs.append(Location("--source", Path(source)))
    # Packaged resources (not shipped by default, but we check anyway)
    locs.append(Location("package", None))
    # Env var base dir
    env = os.environ.get("CLINPGX_DATA_DIR")
    if env:
        locs.append(Location("CLINPGX_DATA_DIR", Path(env)))
    # User cache
    locs.append(Location("cache", _default_cache_dir() / "data"))
    # Dev repo (two parents above package dir)
    dev_root = Path(__file__).resolve().parents[2] / "data"
    locs.append(Location("repo", dev_root))
    return locs


def check_layout(source: Optional[str] = None) -> Tuple[bool, List[str]]:
    messages: List[str] = []
    ok_any = False
    for loc in _locations(source):
        messages.append(f"Checking: {loc.label}")
        all_ok = True
        for key, (rel, expected) in REQUIRED.items():
            if loc.base is None and loc.label == "package":
                # resolve package resource
                try:
                    res = files("clinpgx_lookup").joinpath("data").joinpath(rel)
                    exists = res.is_file()
                    path_str = str(res)
                    # Cannot open to read headers without as_file; skip header check for package
                    hdr_ok = True
                except Exception:
                    exists = False
                    path_str = "<package resource not found>"
                    hdr_ok = False
            else:
                # For external dirs, base should be the data root
                p = (loc.base / rel) if loc.base else None
                exists = p.is_file() if p else False
                path_str = str(p) if p else "<unset>"
                hdr_ok = _header_ok(p, expected) if exists else False

            status = "OK" if (exists and hdr_ok) else ("MISSING" if not exists else "HEADER?")
            messages.append(f"  - {key:11s}: {status:8s}  {path_str}")
            all_ok = all_ok and exists and hdr_ok
        if all_ok:
            messages.append(f"-> Layout valid in {loc.label}")
            ok_any = True
            break
        else:
            messages.append("")

    if not ok_any:
        messages.append("No complete data layout found.")
    return ok_any, messages


def main(argv: Optional[List[str]] = None) -> None:
    p = argparse.ArgumentParser(description="Check availability and layout of ClinPGx TSV data")
    p.add_argument("--source", help="Path to a data directory containing drugs/ genes/ variants/ phenotypes/", default=None)
    args = p.parse_args(argv)
    ok, msgs = check_layout(args.source)
    print("\n".join(msgs))
    if not ok:
        print()
        print("To prepare data in your cache, run:")
        print("  clinpgx-setup --source /path/to/data")
        print()
        print("Or point to a shared data folder via env var:")
        print("  export CLINPGX_DATA_DIR=/shared/path/with/data")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
