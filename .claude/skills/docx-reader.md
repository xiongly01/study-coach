---
type: skill
tags: [document, docx, parsing]
requires: []
---

# docx-reader

Read `.docx` files and convert to AI-readable markdown format.

## Capability

Parse Microsoft Word documents (`.docx`) and extract structured text content:
- Paragraphs with preserved formatting (bold, italic)
- Lists (ordered and unordered)
- Tables (converted to markdown tables)
- Headers and document structure

## Prerequisites

```bash
pip install python-docx
```

## Usage

```python
from docx import Document

def read_docx(file_path: str) -> str:
    """Read docx and return markdown-formatted text."""
    doc = Document(file_path)
    return _doc_to_markdown(doc)

def read_docx_from_bytes(data: bytes) -> str:
    """Read docx from bytes and return markdown-formatted text."""
    from io import BytesIO
    doc = Document(BytesIO(data))
    return _doc_to_markdown(doc)

def _doc_to_markdown(doc) -> str:
    """Convert python-docx Document to markdown string."""
    lines = []
    
    for para in doc.paragraphs:
        text = _format_paragraph(para)
        if text:
            lines.append(text)
    
    # Convert tables
    for table in doc.tables:
        lines.append(_table_to_markdown(table))
    
    return "\n\n".join(lines)

def _format_paragraph(para) -> str:
    """Format a paragraph with inline formatting preserved."""
    text = ""
    for run in para.runs:
        run_text = run.text
        if run.bold:
            run_text = f"**{run_text}**"
        if run.italic:
            run_text = f"*{run_text}*"
        text += run_text
    
    # Handle list items
    if para.style.name.startswith("List"):
        return f"- {text}"
    
    return text

def _table_to_markdown(table) -> str:
    """Convert a table to markdown format."""
    rows = []
    for i, row in enumerate(table.rows):
        cells = [cell.text.strip() for cell in row.cells]
        rows.append("| " + " | ".join(cells) + " |")
        if i == 0:
            rows.append("| " + " | ".join(["---"] * len(cells)) + " |")
    return "\n".join(rows)
```

## Output Format

Returns a markdown string containing:
- Paragraphs as plain text
- Bold text as `**bold**`
- Italic text as `*italic*`
- Lists as `- item` or `1. item`
- Tables as markdown tables

## Notes

- Does NOT extract embedded images
- Does NOT handle complex formatting (colors, fonts, spacing)
- Designed for text extraction suitable for AI context consumption
