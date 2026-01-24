from typing import List

def chunk_text(text: str, chunk_size: int =900, overlap: int =100) -> List[str]:
    """
    Splits the input text into chunks of specified size with a given overlap.

    Args:
        text: The input text to be chunked.
        chunk_size: The maximum size of each chunk.
        overlap: The number of overlapping characters between consecutive chunks.

    Returns:
        A list of text chunks.
    """
    text = text.strip()
    if not text:
        return []
    
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end]
        chunks.append(chunk)
        if end == len(text):
            break
        start = max(0, end - overlap)

    return chunks