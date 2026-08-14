"""
RAG Engine for NexLearn AI Tutor Bot
--------------------------------------
Mirrors the original Semat NexLearn architecture, with free/open-source swaps:
  - Embeddings: sentence-transformers (all-MiniLM-L6-v2) [same as original]
  - Vector store: FAISS IndexFlatL2 [same as original]
  - Generation: Groq API (Llama 3.1) instead of OpenAI GPT-4o (free tier)
"""

import os
import glob
import pickle
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from groq import Groq

CHUNK_SIZE = 400        # tokens (approx, using words as a proxy)
CHUNK_OVERLAP = 60
TOP_K = 4
INDEX_PATH = "faiss_index.bin"
CHUNKS_PATH = "chunks.pkl"

_embedder = None


def get_embedder():
    """Lazy-load the embedding model (cached across calls)."""
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedder


def chunk_text(text, source, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """Simple word-based chunking with overlap, tagged by topic (first line) and source file."""
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk_words = words[start:end]
        chunks.append({
            "text": " ".join(chunk_words),
            "source": source
        })
        if end == len(words):
            break
        start += chunk_size - overlap
    return chunks


def build_index(content_dir="course_content"):
    """
    Indexing step (done once, ahead of time):
    1. Read all course content files
    2. Chunk them
    3. Embed each chunk
    4. Build a FAISS IndexFlatL2 and persist it to disk
    """
    embedder = get_embedder()
    all_chunks = []

    for filepath in glob.glob(os.path.join(content_dir, "*.txt")):
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()
        # split on double newline into topic sections for cleaner chunks
        sections = [s.strip() for s in text.split("\n\n") if s.strip()]
        for section in sections:
            all_chunks.extend(chunk_text(section, os.path.basename(filepath)))

    texts = [c["text"] for c in all_chunks]
    embeddings = embedder.encode(texts, show_progress_bar=False, convert_to_numpy=True)
    embeddings = embeddings.astype("float32")

    dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)

    faiss.write_index(index, INDEX_PATH)
    with open(CHUNKS_PATH, "wb") as f:
        pickle.dump(all_chunks, f)

    return index, all_chunks


def load_or_build_index(content_dir="course_content"):
    if os.path.exists(INDEX_PATH) and os.path.exists(CHUNKS_PATH):
        index = faiss.read_index(INDEX_PATH)
        with open(CHUNKS_PATH, "rb") as f:
            all_chunks = pickle.load(f)
        return index, all_chunks
    return build_index(content_dir)


def retrieve(query, index, all_chunks, top_k=TOP_K):
    """
    Retrieval step (the 'R' in RAG):
    Embed the query, search FAISS for the closest chunks by L2 distance.
    """
    embedder = get_embedder()
    query_vec = embedder.encode([query], convert_to_numpy=True).astype("float32")
    distances, indices = index.search(query_vec, top_k)
    results = [all_chunks[i] for i in indices[0] if i < len(all_chunks)]
    return results


SYSTEM_PROMPT = """You are the NexLearn AI Tutor, an assistant for Semat Technologies' \
technology courses (AWS, Docker, Kubernetes). You must answer ONLY using the course \
content provided below in the context. Do not use outside knowledge. If the context \
does not contain the answer, say you don't have that topic in the enrolled course \
material yet, and suggest the learner check with their instructor.

Structure your answer clearly (use a short analogy if helpful), and end with a one-line \
"Check your understanding" follow-up question related to the topic.

COURSE CONTEXT:
{context}
"""


def generate_answer(query, retrieved_chunks, groq_api_key, model="llama-3.1-8b-instant"):
    """
    Augmentation + Generation step:
    Bundle retrieved chunks into a domain-locked system prompt, call the LLM.
    """
    context = "\n\n---\n\n".join([c["text"] for c in retrieved_chunks])
    system_prompt = SYSTEM_PROMPT.format(context=context)

    client = Groq(api_key=groq_api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query},
        ],
        temperature=0.3,
        max_tokens=600,
    )
    return response.choices[0].message.content


def ask_tutor(query, index, all_chunks, groq_api_key):
    """Full pipeline: retrieve -> augment -> generate. Returns (answer, sources_used)."""
    retrieved = retrieve(query, index, all_chunks)
    answer = generate_answer(query, retrieved, groq_api_key)
    sources = list(set([c["source"] for c in retrieved]))
    return answer, sources, retrieved
