#!/usr/bin/env python3
"""
Stage build outputs into a predictable directory for CI artifact publishing.

Default output directory: datacenter-builds-artifacts/

This is intentionally *not* a OneDrive uploader. It creates a stable local folder
that CI can then publish/upload to the desired destination.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _ensure_within_repo(p: Path) -> None:
    # Prevent accidental deletion of paths outside the repo.
    try:
        p.resolve().relative_to(ROOT)
    except Exception as e:  # pragma: no cover
        raise SystemExit(f"Refusing to write outside repo root: {p}") from e


def _copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def main() -> int:
    ap = argparse.ArgumentParser(description="Stage build artifacts into a local directory.")
    ap.add_argument(
        "--out-dir",
        default=str(ROOT / "dist"),  # Adapted default for Conestoga
        help="Output directory for staged artifacts (must be under repo root).",
    )
    ap.add_argument(
        "--clean",
        action="store_true",
        help="Delete existing staged directory before staging.",
    )
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    if not out_dir.is_absolute():
        out_dir = (ROOT / out_dir).resolve()

    _ensure_within_repo(out_dir)

    if args.clean and out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Stage viewer outputs/indexes if they exist
    for rel in ["viewer/graph.json", "viewer/repo_artifacts_index.json"]:
        src = ROOT / rel
        if src.exists():
            _copy_file(src, out_dir / rel)

    # Stage key docs and docx conversions
    docs_dir = ROOT / "docs"
    if docs_dir.exists():
        # DOCX outputs (versioned + registry)
        docx_dir = docs_dir / "docx"
        if docx_dir.exists():
            versions = docx_dir / "versions.json"
            if versions.exists():
                _copy_file(versions, out_dir / "docs" / "docx" / "versions.json")
            # Only stage *versioned* snapshots.
            for p in sorted(docx_dir.glob("*_v*.docx")):
                if not p.exists():
                    continue
                _copy_file(p, out_dir / "docs" / "docx" / p.name)

        # Mermaid SVG diagrams
        diagrams_dir = docs_dir / "diagrams"
        if diagrams_dir.exists():
            for p in sorted(diagrams_dir.glob("*.svg")):
                if not p.exists():
                    continue
                _copy_file(p, out_dir / "docs" / "diagrams" / p.name)

    # Stage python artifacts from dist/ if they exist (created by uv build)
    # Note: If out-dir IS dist, we don't need to copy, but usually build tools might
    # output elsewhere or we want to consolidate everything.
    # For now assuming 'dist' is the target and uv build outputs to it directly,
    # but strictly speaking this script might be used to aggregate *everything* into
    # a release folder.

    print(f"Staged artifacts at: {out_dir.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
