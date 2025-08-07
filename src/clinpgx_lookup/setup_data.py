from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional
import argparse
import sys

from .lookup_utils import _default_cache_dir


def prepare_data(source_dir: Optional[str] = None) -> Path:
    """Copy TSVs into the user cache so the package runs offline.

    If `source_dir` is None, tries to locate a local `data/` directory relative
    to the current working directory. The structure under `data/` should match
    the repository: drugs/drugs.tsv, genes/genes.tsv, variants/variants.tsv, phenotypes/phenotypes.tsv
    """
    cache = _default_cache_dir() / "data"
    cache.mkdir(parents=True, exist_ok=True)

    if source_dir is None:
        # Common local locations to check
        for candidate in (Path.cwd() / "data", Path(__file__).resolve().parents[2] / "data"):
            if candidate.is_dir():
                source_dir = str(candidate)
                break
    if source_dir is None:
        raise FileNotFoundError("No source data directory provided and none found nearby.")

    src = Path(source_dir)
    if not src.is_dir():
        raise FileNotFoundError(f"Source data directory not found: {src}")

    # Copy expected subtrees
    subdirs = ["drugs", "genes", "variants", "phenotypes"]
    copied_count = 0
    missing_dirs: list[str] = []
    for sd in subdirs:
        s = src / sd
        if s.is_dir():
            d = cache / sd
            d.mkdir(parents=True, exist_ok=True)
            for f in s.glob("*.tsv"):
                shutil.copy2(f, d / f.name)
                copied_count += 1
        else:
            missing_dirs.append(sd)

    if copied_count == 0:
        raise FileNotFoundError(
            "No TSV files were copied. Ensure your --source directory contains subfolders "
            "drugs/, genes/, variants/, phenotypes/ with .tsv files."
        )

    return cache


def main(argv: Optional[list[str]] = None) -> None:
    p = argparse.ArgumentParser(description="Prepare ClinPGx TSV data for offline use")
    p.add_argument("--source", help="Path to local data directory (contains drugs/, genes/, variants/, phenotypes/)")
    args = p.parse_args(argv)

    try:
        dest = prepare_data(args.source)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        print("\nExpected layout under --source:")
        print("  data/")
        print("    drugs/drugs.tsv")
        print("    genes/genes.tsv")
        print("    variants/variants.tsv")
        print("    phenotypes/phenotypes.tsv")
        print("\nIf you already have these TSVs somewhere, pass --source to that directory.")
        print("Alternatively, set CLINPGX_DATA_DIR to a folder containing the 'data/' tree.")
        raise SystemExit(2)

    print()
    print("ClinPGx data cached and ready ✅")
    print(f"Location: {dest}")
    print()
    print("Next steps:")
    print("  - Run a quick lookup:")
    print("      clinpgx-lookup drug \"abacavir\"")
    print("      clinpgx-lookup gene CYP2D6")
    print()
    print("Advanced:")
    print("  - Override cache location: export CLINPGX_CACHE_DIR=/custom/cache")
    print("  - Use a shared data dir:   export CLINPGX_DATA_DIR=/shared/path/with/data")
    print()
    print("Tips:")
    print("  - You can re-run this command any time to refresh cached TSVs.")
    print("  - Indices are built on first lookup and cached for speed.")


if __name__ == "__main__":
    main()
