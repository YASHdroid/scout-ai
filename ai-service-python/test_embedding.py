import pymupdf
from sentence_transformers import SentenceTransformer
from db import conn

# Open PDF
pdf = pymupdf.open("main.pdf")

text = ""

for page in pdf:
    text += page.get_text()


# Split text into chunks
def chunk_text(text, chunk_size=1000):
    chunks = []

    for i in range(0, len(text), chunk_size):
        chunks.append(text[i:i + chunk_size])

    return chunks


chunks = chunk_text(text)

print("Number of chunks:", len(chunks))


# Load embedding model
model = SentenceTransformer("all-MiniLM-L6-v2")


# Connect to database cursor
cursor = conn.cursor()


# Store chunks + embeddings
for i, chunk in enumerate(chunks):

    embedding = model.encode(chunk)

    cursor.execute(
        """
        INSERT INTO document_chunks
        (document_id, chunk_index, chunk_text, embedding)
        VALUES (%s, %s, %s, %s::vector)
        """,
        (
            1,
            i,
            chunk,
            str(embedding.tolist())
        )
    )


conn.commit()

print("All chunks and embeddings stored successfully!")

cursor.close()
conn.close()