# convert file content into text

from io import BytesIO
from pypdf import PdfReader
from docx import Document

def extract_text(filename: str, content: bytes) -> str:
    """
    Extract plain text from a document based on its file type.

    Supported format:
    - .txt : UTF-8 text file
    - .pdf  : Extracts text from each page using pypdf
    - .docx : Extracts text from paragraphs using python-docx

    Args:
        filename: Original filename (used to infer document type).
        content: Raw file bytes.

    Returns:
        Extracted plain text content. If the format is unsupported or
        extraction fails, returns a best-effort UTF-8 decoded string.
    """
    name = filename.lower()

    if name.endswith(".txt"):
        return content.decode("utf-8", errors="ignore")
    
    if name.endswith(".pdf"):
        reader = PdfReader(BytesIO(content))
        pages = []
        for p in reader.pages:
            pages.append(p.extract_text() or "")
        return "\n".join(pages)
    
    if name.endswith(".docx"):
        doc = Document(BytesIO(content))
        return "\n".join([p.text for p in doc.paragraphs])
    
    #fallback
    return content.decode("utf-8", errors="ignore")