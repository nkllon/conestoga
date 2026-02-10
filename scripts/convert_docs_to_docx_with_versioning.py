#!/usr/bin/env python3
"""
Convert markdown documents to DOCX format with semantic versioning.

Each regeneration creates a new version following semantic versioning principles:
- MAJOR: Major structural changes or breaking changes
- MINOR: Content additions or significant modifications
- PATCH: Minor corrections, formatting changes, or regenerations

Version history is tracked in docs/docx/versions.json
"""

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime  # Changed UTC to timezone.utc for compatibility
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent.resolve()
DOCS_DIR = ROOT_DIR / "docs"
OUT_DIR = DOCS_DIR / "docx"
VERSIONS_FILE = OUT_DIR / "versions.json"
UTC = UTC


def discover_docs_to_convert() -> list[str]:
    """
    Discover the set of markdown documents to convert to DOCX.

    Standard config: convert all top-level docs/*.md so new docs are automatically included.
    """
    docs: list[str] = []
    if DOCS_DIR.exists():
        for p in DOCS_DIR.glob("*.md"):
            if p.is_file():
                docs.append(p.name)
    return sorted(set(docs))


DOCS_TO_CONVERT = discover_docs_to_convert()


def calculate_file_hash(file_path: Path) -> str:
    """Calculate SHA256 hash of file content."""
    with open(file_path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def load_versions() -> dict:
    """Load version history from JSON file."""
    if VERSIONS_FILE.exists():
        with open(VERSIONS_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_versions(versions: dict) -> None:
    """Save version history to JSON file."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(VERSIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(versions, f, indent=2, ensure_ascii=False)


def parse_version(version_str: str) -> tuple[int, int, int]:
    """Parse semantic version string to tuple (major, minor, patch)."""
    parts = version_str.split(".")
    return (int(parts[0]), int(parts[1]), int(parts[2]))


def format_version(major: int, minor: int, patch: int) -> str:
    """Format version tuple to semantic version string."""
    return f"{major}.{minor}.{patch}"


def get_next_version(doc_name: str, current_hash: str, versions: dict) -> tuple[str, str]:
    """
    Determine next version based on semantic versioning.

    Returns: (version_string, version_type)
    - PATCH: Same content hash (regeneration without changes)
    - MINOR: Different content hash (content changed)
    - MAJOR: Manual major version bump (not auto-detected)
    """
    if doc_name not in versions:
        # First version
        return "1.0.0", "initial"

    doc_versions = versions[doc_name]
    if not doc_versions.get("history"):
        return "1.0.0", "initial"

    # Get latest version
    latest = doc_versions["history"][-1]
    latest_hash = latest.get("content_hash", "")
    latest_version = latest.get("version", "1.0.0")
    major, minor, patch = parse_version(latest_version)

    if current_hash == latest_hash:
        # Same content - increment patch (regeneration)
        patch += 1
        version_type = "patch"
    else:
        # Content changed - increment minor
        minor += 1
        patch = 0
        version_type = "minor"

    return format_version(major, minor, patch), version_type


def add_version_history(
    doc_name: str,
    version: str,
    content_hash: str,
    file_path: Path,
    version_type: str,
    versions: dict,
) -> None:
    """Add version entry to history."""
    if doc_name not in versions:
        versions[doc_name] = {"source_file": str(file_path.relative_to(ROOT_DIR)), "history": []}

    version_entry = {
        "version": version,
        "content_hash": content_hash,
        "generated_at": datetime.now(UTC).isoformat(),
        "version_type": version_type,
        "docx_file": f"{Path(doc_name).stem}_v{version}.docx",
    }

    versions[doc_name]["history"].append(version_entry)
    versions[doc_name]["latest_version"] = version
    versions[doc_name]["latest_docx"] = version_entry["docx_file"]


def preprocess_mermaid(md_path: Path) -> Path | None:
    """
    Pre-process markdown to convert mermaid diagrams to SVG.

    Returns path to processed markdown file, or None if no processing needed.
    """
    mermaid_script = ROOT_DIR / "scripts" / "convert_mermaid_to_svg.py"
    if not mermaid_script.exists():
        return None

    # Check if mmdc is available
    try:
        result = subprocess.run(["mmdc", "--version"], capture_output=True, text=True, timeout=5)
        if result.returncode != 0:
            return None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None

    # Run mermaid conversion
    result = subprocess.run(
        [
            sys.executable,
            str(mermaid_script),
            "--file",
            str(md_path),
            "--diagrams-dir",
            str(DOCS_DIR / "diagrams"),
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        # Mermaid conversion failed, but continue with original file
        return None

    # Check if processed file was created
    processed_path = md_path.parent / f".{md_path.name}.processed"
    if processed_path.exists():
        return processed_path

    return None


def convert_with_python_docx(src: Path, dst: Path) -> bool:
    """Convert markdown to DOCX using python-docx."""
    try:
        # Pre-process mermaid diagrams if needed
        processed_src = preprocess_mermaid(src)
        if processed_src:
            src = processed_src

        # Import converter module
        converter_path = ROOT_DIR / "scripts" / "docx_converter.py"
        import importlib.util

        spec = importlib.util.spec_from_file_location("docx_converter", converter_path)
        docx_converter = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(docx_converter)

        # Convert markdown to DOCX
        docx_converter.convert_markdown_to_docx(src, dst)

        # Clean up processed file if it was created
        if processed_src and processed_src.exists():
            processed_src.unlink()

        return True
    except ImportError as e:
        print("Error: python-docx required. Install with: pip install python-docx")
        print(f"Details: {e}")
        return False
    except Exception as e:
        print(f"Error converting with python-docx: {e}")
        import traceback

        traceback.print_exc()
        return False


def add_version_metadata_to_docx(docx_path: Path, version: str, version_type: str) -> None:
    """
    Add version metadata to DOCX file using python-docx.
    This adds version info as a custom property and in the document core properties.
    """
    try:
        from docx import Document
        from docx.opc.coreprops import CoreProperties  # noqa: F401

        doc = Document(str(docx_path))

        # Add version info to core properties
        core_props = doc.core_properties
        core_props.comments = f"Version {version} ({version_type})"

        # Add version as custom property if possible
        # Note: python-docx doesn't directly support custom properties,
        # but we can add it to comments/title
        if not core_props.title or "Version" not in core_props.title:
            if core_props.title:
                core_props.title = f"{core_props.title} (v{version})"
            else:
                core_props.title = f"Document Version {version}"

        doc.save(str(docx_path))
    except ImportError:
        # python-docx not available, skip metadata addition
        pass
    except Exception as e:
        print(f"Warning: Could not add version metadata: {e}")


def main() -> int:
    """Main conversion function with versioning."""
    parser = argparse.ArgumentParser(
        description="Convert markdown docs to DOCX with semantic versioning."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force regeneration even if content hash is unchanged (will bump PATCH).",
    )
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Check for python-docx
    try:
        from docx import Document  # noqa: F401
    except ImportError:
        print("Error: python-docx required. Install with: pip install python-docx")
        return 1

    print("Using python-docx for conversion with semantic versioning...")

    # Load existing versions
    versions = load_versions()

    converted_count = 0
    skipped_unchanged = 0

    for doc_name in DOCS_TO_CONVERT:
        src = DOCS_DIR / doc_name
        if not src.exists():
            print(f"Warning: {src} not found, skipping")
            continue

        # Calculate content hash
        content_hash = calculate_file_hash(src)

        # Determine next version
        version, version_type = get_next_version(doc_name, content_hash, versions)

        # Systemic guardrail: do not churn versions for unchanged content unless forced.
        if (
            not args.force
            and doc_name in versions
            and versions[doc_name].get("history")
            and version_type == "patch"
        ):
            latest = versions[doc_name]["history"][-1]
            latest_docx = latest.get("docx_file")
            if latest_docx and (OUT_DIR / latest_docx).exists():
                skipped_unchanged += 1
                continue

        # Generate versioned output filename
        docx_filename = f"{src.stem}_v{version}.docx"
        dst = OUT_DIR / docx_filename

        print(f"Converting: {doc_name} -> {docx_filename} (v{version}, {version_type})")

        # Convert with python-docx
        if convert_with_python_docx(src, dst):
            # Add version metadata
            add_version_metadata_to_docx(dst, version, version_type)

            # Update version history
            add_version_history(doc_name, version, content_hash, src, version_type, versions)

            converted_count += 1
        else:
            print(f"Error: Failed to convert {doc_name}")
            return 1

    # Save version history
    save_versions(versions)

    print(f"\nDOCX conversion complete. Converted {converted_count} documents.")
    if skipped_unchanged:
        print(f"Skipped unchanged: {skipped_unchanged} documents (use --force to regenerate).")
    print(f"Version history saved to: {VERSIONS_FILE.relative_to(ROOT_DIR)}")
    print(f"Output directory: {OUT_DIR.relative_to(ROOT_DIR)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
