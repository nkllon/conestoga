#!/usr/bin/env python3
"""
Build a deterministic, checked-in retrieval index over repo artifacts.

Output: viewer/repo_artifacts_index.json

Design goals:
- Deterministic ordering and chunking
- Pure-Python (no external embedding/index services)
- Safe for provenance/traceability (stores path + line ranges + sha256)
"""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Iterator, Sequence
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_OUT_ENV = os.environ.get("REPO_INDEX_OUT")
if _OUT_ENV:
    _env_path = Path(_OUT_ENV)
    OUT = _env_path if _env_path.is_absolute() else ROOT / _OUT_ENV
else:
    OUT = ROOT / "viewer" / "repo_artifacts_index.json"


def as_repo_relative(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


DEFAULT_SOURCE_CACHE_DIR = ".cache/source_artifacts"


INCLUDE_DIRS = [
    "ontology",
    "docs",
    "scripts",
    "src",
]

INCLUDE_FILES = [
    "README.md",
]

EXCLUDE_DIR_PREFIXES = [
    ".venv/",
    ".git/",
    ".kiro/",
    "node_modules/",
    ".mypy_cache/",
    ".pytest_cache/",
    "__pycache__/",
    "build/",
    "dist/",
]

EXCLUDE_EXACT = {
    "artifacts.zip",
    "artifacts.tar.gz",
    "uv.lock",
    "package-lock.json",
    as_repo_relative(OUT),
}

EXCLUDE_EXTS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".zip",
    ".tar",
    ".gz",
    ".pyc",
    ".DS_Store",
}


def should_include(rel: str) -> bool:
    if rel in EXCLUDE_EXACT:
        return False
    for p in EXCLUDE_DIR_PREFIXES:
        if rel.startswith(p):
            return False
    ext = Path(rel).suffix.lower()
    if ext in EXCLUDE_EXTS:
        return False
    return True


def iter_files() -> list[str]:
    files: list[str] = []

    for f in INCLUDE_FILES:
        p = ROOT / f
        if p.exists() and p.is_file():
            rel = p.relative_to(ROOT).as_posix()
            if should_include(rel):
                files.append(rel)

    for d in INCLUDE_DIRS:
        base = ROOT / d
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if not p.is_file():
                continue
            rel = p.relative_to(ROOT).as_posix()
            if should_include(rel):
                files.append(rel)

    # Optional: include local source-artifact cache
    include_cache = os.environ.get("REPO_INDEX_INCLUDE_SOURCE_CACHE", "0").strip() == "1"
    cache_dir_raw = (
        os.environ.get("REPO_SOURCE_CACHE_DIR", DEFAULT_SOURCE_CACHE_DIR).strip()
        or DEFAULT_SOURCE_CACHE_DIR
    )
    if include_cache:
        cache_dir = Path(cache_dir_raw)
        cache_dir = cache_dir if cache_dir.is_absolute() else (ROOT / cache_dir)
        try:
            cache_dir.relative_to(ROOT)
        except Exception:
            pass
        else:
            if cache_dir.exists():
                for p in cache_dir.rglob("*"):
                    if not p.is_file():
                        continue
                    rel = p.relative_to(ROOT).as_posix()
                    if should_include(rel):
                        files.append(rel)

    return sorted(set(files))


def chunk_lines(
    lines: Sequence[str], chunk_size: int, overlap: int
) -> Iterator[tuple[int, int, str]]:
    """
    Yields (start_line, end_line, text) where line numbers are 1-based inclusive.
    """

    n = len(lines)
    if n == 0:
        return
    i = 0
    while i < n:
        start = i
        end = min(n, i + chunk_size)
        text = "".join(lines[start:end])
        yield (start + 1, end, text)
        if end >= n:
            break
        i = max(0, end - overlap)


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def read_text_file(path: Path) -> list[str]:
    # Binary handling: include metadata-only stubs for selected binary formats.
    ext = path.suffix.lower()
    if ext in {".docx", ".pdf"}:
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        size = len(data)
        text = f"[BINARY:{ext}] sha256={digest} size_bytes={size} path={path.name}\n"
        return [text]

    # Normalize newlines for deterministic chunking.
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []

    if not text.endswith("\n"):
        text += "\n"
    return [ln + "\n" for ln in text.splitlines()]


def main() -> int:
    chunk_size = int(os.environ.get("REPO_INDEX_CHUNK_LINES", "80"))
    overlap = int(os.environ.get("REPO_INDEX_CHUNK_OVERLAP", "12"))

    # Internal-only entities to exclude from published index
    INTERNAL_ONLY_ENTITIES: list[str] = []

    chunks = []
    for rel in iter_files():
        p = ROOT / rel
        lines = read_text_file(p)
        for start_line, end_line, text in chunk_lines(
            lines, chunk_size=chunk_size, overlap=overlap
        ):
            # Skip chunks that mention internal-only entities
            if any(entity in text for entity in INTERNAL_ONLY_ENTITIES):
                continue
            chunks.append(
                {
                    "path": rel,
                    "start_line": start_line,
                    "end_line": end_line,
                    "sha256": sha256_text(text),
                    "text": text,
                }
            )

    payload = {"version": 1, "chunks": chunks}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {as_repo_relative(OUT)} with {len(chunks)} chunks from {len(iter_files())} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
