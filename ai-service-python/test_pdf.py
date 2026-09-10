import pymupdf


# Open PDF
pdf = pymupdf.open("main.pdf")


# Extract text from all pages
text = ""

for page in pdf:
    text += page.get_text()


# Split text into chunks
def chunk_text(text, chunk_size=1000):
    chunks = []

    for i in range(0, len(text), chunk_size):
        chunks.append(text[i:i + chunk_size])

    return chunks


# Create chunks
chunks = chunk_text(text)


# Print number of chunks
print("Number of chunks:", len(chunks))


# Print first 200 characters of each chunk
for i, chunk in enumerate(chunks):
    print(f"\n--- Chunk {i + 1} ---")
    print(chunk[:200])