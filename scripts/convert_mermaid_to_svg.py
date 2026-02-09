#!/usr/bin/env python3
"""
Convert mermaid code blocks in markdown files to SVG images.

Extracts mermaid diagrams from markdown files, converts them to SVG using mermaid-cli (mmdc),
and replaces the code blocks with markdown image references. SVGs are stored in docs/diagrams/
with content-hash-based filenames for deterministic builds.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent.resolve()
DOCS_DIR = ROOT_DIR / "docs"
DIAGRAMS_DIR = DOCS_DIR / "diagrams"


def check_mmdc_available() -> bool:
    """Check if mermaid-cli (mmdc) is available."""
    try:
        result = subprocess.run(["mmdc", "--version"], capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def calculate_content_hash(content: str) -> str:
    """Calculate SHA256 hash of content for deterministic naming."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:12]


def extract_mermaid_blocks(markdown_content: str) -> list[tuple[int, int, str]]:
    """
    Extract mermaid code blocks from markdown.

    Returns list of (start_pos, end_pos, mermaid_content) tuples.
    """
    pattern = r"```mermaid\n(.*?)```"
    matches = []
    for match in re.finditer(pattern, markdown_content, re.DOTALL):
        start = match.start()
        end = match.end()
        content = match.group(1).strip()
        matches.append((start, end, content))
    return matches


def convert_mermaid_to_svg(mermaid_content: str, output_path: Path) -> bool:
    """
    Convert mermaid content to SVG using mmdc.

    Returns True if conversion succeeded, False otherwise.
    """
    try:
        # Create temporary mermaid file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".mmd", delete=False) as tmp_file:
            tmp_file.write(mermaid_content)
            tmp_mmd = Path(tmp_file.name)

        # Run mmdc conversion
        result = subprocess.run(
            [
                "mmdc",
                "-i",
                str(tmp_mmd),
                "-o",
                str(output_path),
                "-b",
                "transparent",
                "-t",
                "default",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Clean up temp file
        tmp_mmd.unlink()

        if result.returncode == 0 and output_path.exists():
            return True
        else:
            print(f"Warning: mmdc conversion failed: {result.stderr}", file=sys.stderr)
            return False
    except Exception as e:
        print(f"Error running mmdc: {e}", file=sys.stderr)
        return False


def process_markdown_file(md_path: Path, diagrams_dir: Path) -> tuple[str, list[Path]]:
    """
    Process a markdown file, converting mermaid blocks to SVG.

    Returns (updated_markdown_content, list_of_generated_svg_paths).
    """
    with open(md_path, encoding="utf-8") as f:
        content = f.read()

    mermaid_blocks = extract_mermaid_blocks(content)
    if not mermaid_blocks:
        return content, []

    # Ensure diagrams directory exists
    diagrams_dir.mkdir(parents=True, exist_ok=True)

    generated_svgs = []
    offset = 0

    for start, end, mermaid_content in mermaid_blocks:
        # Generate deterministic filename
        content_hash = calculate_content_hash(mermaid_content)
        doc_name = md_path.stem
        svg_filename = f"{doc_name}_diagram_{content_hash}.svg"
        svg_path = diagrams_dir / svg_filename

        # Convert mermaid to SVG
        # We check existence to avoid re-generating if possible, but mmdc is fast enough usually
        # To be purely deterministic we should probably always regen or check hash.
        # This basic impl overwrites.
        if convert_mermaid_to_svg(mermaid_content, svg_path):
            generated_svgs.append(svg_path)

            # Replace mermaid block with image reference
            # Use relative path from docs/ directory (assuming docs/diagrams/)
            # If MD file is in docs/, rel path is diagrams/file.svg
            # If MD file is in docs/subdir/, rel path might need adjustment.
            # Assuming docs/*.md structure mostly.

            try:
                # Calculate relative path from the markdown file to the svg
                relative_svg_path = os.path.relpath(svg_path, md_path.parent)
            except Exception:
                # Fallback to simple relative if in same tree
                relative_svg_path = f"diagrams/{svg_filename}"

            image_markdown = f"![Diagram]({relative_svg_path})\n"

            # Adjust positions for previous replacements
            adj_start = start + offset
            adj_end = end + offset

            # Replace the block
            content = content[:adj_start] + image_markdown + content[adj_end:]

            # Update offset for next replacement
            offset += len(image_markdown) - (adj_end - adj_start)
        else:
            print(
                f"Warning: Failed to convert mermaid diagram in {md_path.name}, "
                "keeping original block",
                file=sys.stderr,
            )

    return content, generated_svgs


def main() -> int:
    """Main conversion function."""

    parser = argparse.ArgumentParser(
        description="Convert mermaid diagrams in markdown files to SVG images."
    )
    parser.add_argument(
        "--docs-dir",
        type=Path,
        default=DOCS_DIR,
        help="Directory containing markdown files (default: docs/)",
    )
    parser.add_argument(
        "--diagrams-dir",
        type=Path,
        default=DIAGRAMS_DIR,
        help="Directory for generated SVG files (default: docs/diagrams/)",
    )
    parser.add_argument(
        "--file",
        type=Path,
        help="Process a specific markdown file (default: process all docs/*.md)",
    )
    parser.add_argument(
        "--check-only", action="store_true", help="Only check if mmdc is available, don't convert"
    )
    args = parser.parse_args()

    # Check for mmdc availability
    if not check_mmdc_available():
        print(
            "Warning: mermaid-cli (mmdc) not found. "
            "Install with: npm install -g @mermaid-js/mermaid-cli",
            file=sys.stderr,
        )
        if args.check_only:
            return 1
        print("Continuing without mermaid conversion...", file=sys.stderr)
        return 0

    if args.check_only:
        print("✓ mermaid-cli (mmdc) is available")
        return 0

    # Determine files to process
    if args.file:
        md_files = [args.file]
    else:
        md_files = list(args.docs_dir.glob("*.md"))

    if not md_files:
        print(f"No markdown files found in {args.docs_dir}")
        return 0

    total_converted = 0
    total_svgs = 0

    for md_path in sorted(md_files):
        if not md_path.is_file():
            continue

        updated_content, generated_svgs = process_markdown_file(md_path, args.diagrams_dir)

        if generated_svgs:
            # Write updated markdown to temporary file (caller will use it)
            # For now, we'll write to a temp file that the DOCX converter can use
            temp_md = md_path.parent / f".{md_path.name}.processed"
            with open(temp_md, "w", encoding="utf-8") as f:
                f.write(updated_content)

            total_converted += 1
            total_svgs += len(generated_svgs)
            print(f"Converted {len(generated_svgs)} diagram(s) in {md_path.name}")

    if total_converted > 0:
        print(
            f"\n✓ Converted {total_svgs} mermaid diagram(s) to SVG across {total_converted} file(s)"
        )
        print(f"SVG files stored in: {args.diagrams_dir.relative_to(ROOT_DIR)}")
    else:
        print("No mermaid diagrams found to convert")

    return 0


if __name__ == "__main__":
    sys.exit(main())
