# NexLearn — GenAI-Powered Adaptive Learning Companion

A personal rebuild of the Semat NexLearn MVP (GenAI Product Internship, Summer 2026),
using free/open-source tools in place of the original paid infrastructure.

## What's included (all 5 original MVP features)

| Feature | Original | This rebuild |
|---|---|---|
| AI Tutor Bot | GPT-4o + LangChain + FAISS, RAG-grounded | Groq (Llama 3.1, free) + FAISS + sentence-transformers |
| Adaptive Quiz Engine | Python/FastAPI, difficulty auto-adjust | Same logic, in Streamlit |
| Progress Dashboard | React.js + Chart.js | Streamlit + Plotly |
| LMS Integration | Live Moodle REST API sync | Mocked static course structure (same data shape) |
| Instructor Analytics | Metabase + SQL | Streamlit + Plotly, same SQL queries under the hood |

Data layer: SQLite instead of PostgreSQL/RDS (same schema shape, zero-config).

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open the local URL Streamlit prints (usually http://localhost:8501).

You'll need a **free Groq API key** for the AI Tutor Bot:
1. Go to https://console.groq.com
2. Sign up (no credit card required)
3. Create an API key
4. Paste it into the sidebar text box when the app is running

The Adaptive Quiz, Progress Dashboard, LMS Integration, and Instructor Analytics
tabs all work without an API key.

## Deploy for free (shareable public link)

**Streamlit Community Cloud** (recommended — same platform pattern as your
IT Risk & Control Assessment Agent):

1. Push this folder to a public GitHub repo
2. Go to https://share.streamlit.io
3. Sign in with GitHub, click "New app"
4. Point it at your repo, select `app.py` as the entry point
5. Deploy — you'll get a public `*.streamlit.app` URL to share
6. (Optional) Under app settings → Secrets, you can pre-fill the Groq key
   so you don't have to paste it in each time — but keep the manual entry
   as the default so it's clear the key isn't hardcoded/exposed

## Architecture notes (for interview reference)

- **Indexing (one-time):** course content in `course_content/*.txt` is chunked
  (~400 words, 60-word overlap), embedded with `all-MiniLM-L6-v2`, and stored
  in a FAISS `IndexFlatL2` index.
- **Retrieval:** a learner's question is embedded the same way, and FAISS
  returns the top-4 closest chunks by L2 distance.
- **Generation:** retrieved chunks + a domain-locked system prompt + the
  question are sent to Groq's Llama 3.1 model, which generates the grounded answer.
- **Adaptive quiz logic:** 3 consecutive correct answers at the current
  difficulty → promote; recent accuracy below 50% → demote. Pure Python,
  no LLM involved — matches the original design.
- **Instructor Analytics:** aggregates quiz attempts and tutor queries across
  all learners in the SQLite DB — same shape of query Metabase would run
  against PostgreSQL in the original.

## What's different from the original (be upfront about this in interviews)

- GPT-4o → Groq/Llama 3.1 (cost — Groq's free tier is generous and fast)
- FastAPI+React (two services) → Streamlit (one Python app, faster to build solo)
- PostgreSQL/RDS → SQLite (zero-config, fine for a personal demo)
- Real Moodle sync → mocked static data (no real Moodle instance to connect to)
- 200-question bank → ~24 sample questions (easily expandable — same structure)

These are honest, defensible engineering tradeoffs for a solo personal rebuild,
not corners cut carelessly — worth saying exactly that if asked.
