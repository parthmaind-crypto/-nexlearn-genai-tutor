"""
Quick standalone test to run on your own machine before touching Streamlit.
Confirms the one untested link: real MiniLM download + embed + FAISS build.
Run: python local_test.py
"""
import sys
sys.path.insert(0, ".")
import rag_engine

print("1. Loading embedder (downloads ~90MB model on first run)...")
embedder = rag_engine.get_embedder()
print("   OK")

print("2. Building index from course_content/...")
index, chunks = rag_engine.build_index("course_content")
print(f"   OK - {index.ntotal} vectors, {len(chunks)} chunks, dim={index.d}")

print("3. Testing retrieval...")
results = rag_engine.retrieve("What is a VPC?", index, chunks)
for r in results:
    print(f"   [{r['source']}] {r['text'][:70]}...")

print("\nAll checks passed. rag_engine.py is confirmed working end-to-end (minus Groq generation).")
print("Next: get a Groq key at https://console.groq.com/keys and test generate_answer().")
