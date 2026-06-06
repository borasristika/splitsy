"""Extract selectable text from a PDF using pypdf."""
import os
from pypdf import PdfReader


def extract_text(path: str) -> str:
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    reader = PdfReader(path)
    return "\n".join((page.extract_text() or "") for page in reader.pages)
