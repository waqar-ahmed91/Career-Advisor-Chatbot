import os
import chromadb
from sentence_transformers import SentenceTransformer
from chromadb.utils import embedding_functions
from PyPDF2 import PdfReader

chroma_client = chromadb.PersistentClient(path="chroma_db")
embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)
chroma_client.delete_collection("career_kb")
collection = chroma_client.get_or_create_collection("career_kb", embedding_function=embedding_fn)


def read_file(path):
    ext = path.split(".")[-1].lower()
    if ext == "pdf":
        reader = PdfReader(path)
        return "\n".join(page.extract_text() for page in reader.pages if page.extract_text())
    else:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

def chunk_text(text, chunk_size=500, overlap=100):
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
    return chunks

doc_id = 0
for filename in os.listdir("knowledge_base"):
    path = os.path.join("knowledge_base", filename)
    if os.path.isfile(path) and filename.endswith((".txt", ".md", ".pdf")):
        print(f"Processing: {filename}")
        content = read_file(path)
        chunks = chunk_text(content)

        if chunks:
            collection.add(
                documents=chunks,
                metadatas=[{"source": filename}] * len(chunks),
                ids=[f"kb-{doc_id + i}" for i in range(len(chunks))]
            )
            doc_id += len(chunks)

print(f" Loaded {doc_id} chunks into the knowledge base.")
print(f" Collection now contains: {collection.count()} chunks.")

