import os
import hashlib
from typing import List
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings


#Storing in chroma in this format: 
# {
#     "id": <unique SHA1 hash>,
#     "document": <text chunk>,
#     "embedding": <vector array>,
#     "metadata": {
#          "source": "<pdf filename>"
#     }
# }

# -------- CONFIG -------- #
CHROMA_DIR = "./chromadb_store"
COLLECTION_NAME = "pdf_chunks"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

CHUNK_SIZE = 500
CHUNK_OVERLAP = 100


# -------- HELPERS -------- #
def extract_text_from_pdf(path: str) -> str:
    reader = PdfReader(path)
    text = []
    for page in reader.pages:
        content = page.extract_text()
        if content:
            text.append(content)
    return "\n".join(text)


def chunk_text(text: str, chunk_size: int, overlap: int) -> List[str]:
    chunks = []
    start = 0
    length = len(text)

    while start < length:
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk.strip())
        if end >= length:
            break
        start = end - overlap

    # filter tiny chunks
    return [c for c in chunks if len(c) > 20]


def chunk_id(chunk: str) -> str:
    """Generate stable unique ID for each chunk."""
    return hashlib.sha1(chunk.encode("utf-8")).hexdigest()


def embed(texts: List[str]):
    model = SentenceTransformer(EMBEDDING_MODEL)
    return model.encode(texts, convert_to_numpy=True)


def init_chroma():
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    try:
        return client.get_collection(COLLECTION_NAME)
    except:
        return client.create_collection(COLLECTION_NAME)


# -------- MAIN FUNCTION -------- #
def ingest_pdf(pdf_path: str):
    print(f"[+] Reading {pdf_path}...")
    text = extract_text_from_pdf(pdf_path)

    print("[+] Chunking text...")
    chunks = chunk_text(text, CHUNK_SIZE, CHUNK_OVERLAP)
    print(f"[+] Created {len(chunks)} chunks.")

    print("[+] Embedding chunks...")
    embeddings = embed(chunks)

    ids = [chunk_id(c) for c in chunks]
    metadatas = [{"source": os.path.basename(pdf_path)} for _ in chunks]

    collection = init_chroma()

    print("[+] Storing in ChromaDB...")
    collection.upsert(
        ids=ids,
        documents=chunks,
        embeddings=embeddings.tolist(),
        metadatas=metadatas
    )

    print("[✓] Done. Stored in:", CHROMA_DIR)



