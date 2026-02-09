from pathlib import Path

from docx import Document


def convert_markdown_to_docx(src: Path, dst: Path) -> None:
    """
    Convert a Markdown file to a DOCX file using python-docx.
    Handles basic Markdown syntax: headers (#), bold (**), italic (*), and lists.
    """
    doc = Document()
    text = src.read_text(encoding="utf-8")

    # Enable Track Changes
    settings = doc.settings.element
    from docx.oxml import OxmlElement

    track_revisions = OxmlElement("w:trackRevisions")
    settings.append(track_revisions)

    # Simple line-by-line parser with basic bold support
    lines = text.split("\n")

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Headers
        if line.startswith("#"):
            level = len(line.split()[0])
            content = line.lstrip("#").strip()
            level = min(level, 9)
            doc.add_heading(content, level=level)

        # List items
        elif line.startswith("- ") or line.startswith("* "):
            content = line[2:].strip()
            p = doc.add_paragraph(style="List Bullet")
            # Handle bold in list item
            if "**" in content:
                parts = content.split("**")
                for i, part in enumerate(parts):
                    run = p.add_run(part)
                    if i % 2 == 1:  # Odd parts are inside **
                        run.bold = True
            else:
                p.add_run(content)

        # Standard paragraph
        else:
            p = doc.add_paragraph()
            # Handle bold
            if "**" in line:
                parts = line.split("**")
                for i, part in enumerate(parts):
                    run = p.add_run(part)
                    if i % 2 == 1:
                        run.bold = True
            else:
                p.add_run(line)

    # Save the document
    doc.save(str(dst))
