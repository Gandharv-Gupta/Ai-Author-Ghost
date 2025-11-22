
from sentence_transformers import SentenceTransformer
import chromadb

CHROMA_DIR = "./chromadb_store"
COLLECTION_NAME = "pdf_chunks"
model = SentenceTransformer("all-MiniLM-L6-v2")

def embed_query(query):
    return model.encode(query).tolist()

def query_chroma(query_text, k=1):
    # Load DB
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    collection = client.get_collection(COLLECTION_NAME)

    # Create embedding
    query_embedding = embed_query(query_text)

    # Search relevant docs
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=k
    )

    return results


# if __name__ == "__main__":
#     query = input("Ask something about the book: ")
#     results = query_chroma(query, k=1)

#     print("\n🔍 Most relevant chunk:\n")
#     print(results["documents"][0][0])
