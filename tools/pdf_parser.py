from pathlib import Path


def extract_text(file_path: str | Path) -> str:
    """Extract all text from a PDF using PyMuPDF."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise RuntimeError("PyMuPDF (fitz) is required: pip install pymupdf")

    doc = fitz.open(str(file_path))
    pages = []
    for page in doc:
        pages.append(page.get_text())
    doc.close()
    return "\n".join(pages)
