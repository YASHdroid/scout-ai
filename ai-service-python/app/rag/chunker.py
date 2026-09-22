def chunk_text(text: str, chunk_size: int = 1000):
    chunks = []

    for i in range(0, len(text), chunk_size):
        chunk = text[i:i + chunk_size].replace("\x00", "").strip()

        if chunk:
            chunks.append(chunk)

    return chunks
