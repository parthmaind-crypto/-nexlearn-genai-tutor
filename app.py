"""
NexLearn MVP Rebuild
A GenAI-powered adaptive learning companion — free/open-source recreation
of the original Semat NexLearn MVP.

Run locally:  streamlit run app.py
Deploy free:  push to GitHub -> deploy on Streamlit Community Cloud
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta, date

import db
import rag_engine
from quiz_bank import QUESTION_BANK, DIFFICULTY_ORDER, get_next_difficulty, get_hint

st.set_page_config(page_title="NexLearn", page_icon="🎓", layout="wide")
db.init_db()

# ---------------------------------------------------------------------------
# Sidebar: learner identity + API key + navigation
# ---------------------------------------------------------------------------
st.sidebar.title("🎓 NexLearn")
st.sidebar.caption("GenAI-powered adaptive learning companion")

groq_api_key = st.sidebar.text_input(
    "Groq API Key", type="password",
    help="Free key from console.groq.com — powers the AI Tutor Bot."
)

learner_name = st.sidebar.text_input("Your name", value="Parth")
segment = st.sidebar.selectbox("Segment", ["Student", "Working Professional", "L&D Manager"])
course = st.sidebar.selectbox("Enrolled Course", ["AWS Solutions Architect", "Docker Zero to Hero", "Kubernetes Fundamentals"])

if learner_name:
    learner_id = db.get_or_create_learner(learner_name, segment, course)
else:
    learner_id = None

page = st.sidebar.radio(
    "Navigate",
    ["🤖 AI Tutor Bot", "📝 Adaptive Quiz", "📊 Progress Dashboard", "📚 LMS Integration", "👨‍🏫 Instructor Analytics"]
)

topic_map = {
    "AWS Solutions Architect": "AWS VPC",
    "Docker Zero to Hero": "Docker Networking",
    "Kubernetes Fundamentals": "Kubernetes",
}
current_topic = topic_map[course]

# ---------------------------------------------------------------------------
# Load / build the FAISS index once, cache across reruns
# ---------------------------------------------------------------------------
@st.cache_resource
def get_index():
    return rag_engine.load_or_build_index()

# ===========================================================================
# PAGE 1 — AI Tutor Bot
# ===========================================================================
if page == "🤖 AI Tutor Bot":
    st.header("🤖 AI Tutor Bot")
    st.caption(f"Domain-locked to your enrolled course: **{course}**. RAG-grounded — answers come only from course content.")

    if not groq_api_key:
        st.warning("Enter a free Groq API key in the sidebar to use the tutor. Get one at console.groq.com — no credit card needed.")
    elif not learner_id:
        st.warning("Enter your name in the sidebar first.")
    else:
        index, all_chunks = get_index()

        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []

        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
                if msg["role"] == "assistant" and "sources" in msg:
                    st.caption(f"📄 Sources: {', '.join(msg['sources'])}")

        user_query = st.chat_input("Ask a question about your course...")
        if user_query:
            st.session_state.chat_history.append({"role": "user", "content": user_query})
            with st.chat_message("user"):
                st.write(user_query)

            with st.chat_message("assistant"):
                with st.spinner("Retrieving course content and generating answer..."):
                    try:
                        answer, sources, retrieved = rag_engine.ask_tutor(
                            user_query, index, all_chunks, groq_api_key
                        )
                        st.write(answer)
                        st.caption(f"📄 Sources: {', '.join(sources)}")
                        db.log_tutor_query(learner_id, user_query, sources[0] if sources else "unknown")
                        st.session_state.chat_history.append(
                            {"role": "assistant", "content": answer, "sources": sources}
                        )
                        with st.expander("🔍 See retrieved chunks (RAG debug view)"):
                            for i, chunk in enumerate(retrieved):
                                st.markdown(f"**Chunk {i+1}** — *{chunk['source']}*")
                                st.text(chunk["text"][:300] + "...")
                    except Exception as e:
                        st.error(f"Error calling Groq API: {e}")

        st.divider()
        st.caption("💡 Try asking: \"Explain the difference between a Public Subnet and Private Subnet\" or \"Why can't my container reach the internet?\"")

# ===========================================================================
# PAGE 2 — Adaptive Quiz Engine
# ===========================================================================
elif page == "📝 Adaptive Quiz":
    st.header("📝 Adaptive Quiz Engine")
    st.caption(f"Topic: **{current_topic}** — difficulty auto-adjusts to your performance (3 correct in a row → harder; below 50% → easier + hint)")

    if not learner_id:
        st.warning("Enter your name in the sidebar first.")
    else:
        if "quiz_difficulty" not in st.session_state:
            st.session_state.quiz_difficulty = "Easy"
        if "current_q" not in st.session_state:
            st.session_state.current_q = None
        if "answered" not in st.session_state:
            st.session_state.answered = False

        recent = db.get_recent_quiz_attempts(learner_id, current_topic, limit=3)
        st.session_state.quiz_difficulty = get_next_difficulty(recent, st.session_state.quiz_difficulty)

        diff_color = {"Easy": "🟢", "Medium": "🟡", "Hard": "🔴"}
        st.subheader(f"{diff_color[st.session_state.quiz_difficulty]} Difficulty: {st.session_state.quiz_difficulty}")

        import random
        if st.session_state.current_q is None:
            pool = QUESTION_BANK[current_topic][st.session_state.quiz_difficulty]
            st.session_state.current_q = random.choice(pool)
            st.session_state.answered = False

        q = st.session_state.current_q
        st.write(f"**{q['q']}**")
        choice = st.radio("Choose an answer:", q["options"], key=f"radio_{id(q)}", index=None)

        col1, col2 = st.columns([1, 4])
        with col1:
            submit = st.button("Submit Answer", disabled=st.session_state.answered)

        if submit and choice is not None:
            correct = q["options"].index(choice) == q["answer"]
            st.session_state.answered = True
            db.log_quiz_attempt(learner_id, current_topic, st.session_state.quiz_difficulty, correct)

            if correct:
                st.success("✅ Correct!")
            else:
                st.error(f"❌ Not quite. Correct answer: **{q['options'][q['answer']]}**")
                st.info(f"💡 Hint for next time: {get_hint(current_topic, st.session_state.quiz_difficulty)}")

        if st.session_state.answered:
            if st.button("Next Question →"):
                st.session_state.current_q = None
                st.rerun()

# ===========================================================================
# PAGE 3 — Progress Dashboard
# ===========================================================================
elif page == "📊 Progress Dashboard":
    st.header("📊 Progress Dashboard")

    if not learner_id:
        st.warning("Enter your name in the sidebar first.")
    else:
        history = db.get_learner_quiz_history(learner_id)
        activity_dates = db.get_learner_activity_dates(learner_id)

        col1, col2, col3 = st.columns(3)
        total_attempts = len(history)
        correct_attempts = sum(1 for h in history if h["correct"])
        accuracy = (correct_attempts / total_attempts * 100) if total_attempts else 0

        col1.metric("Quiz Questions Attempted", total_attempts)
        col2.metric("Accuracy", f"{accuracy:.0f}%")
        col3.metric("Active Days", len(activity_dates))

        st.divider()

        if history:
            df = pd.DataFrame([dict(h) for h in history])
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df["attempt_no"] = range(1, len(df) + 1)
            df["score"] = df["correct"].cumsum() / df["attempt_no"] * 100

            st.subheader("Accuracy Over Time")
            fig = px.line(df, x="attempt_no", y="score", markers=True,
                          labels={"attempt_no": "Question #", "score": "Cumulative Accuracy (%)"})
            fig.update_layout(height=350)
            st.plotly_chart(fig, use_container_width=True)

            st.subheader("Performance by Topic")
            topic_summary = df.groupby("topic")["correct"].agg(["count", "sum"]).reset_index()
            topic_summary["accuracy_%"] = (topic_summary["sum"] / topic_summary["count"] * 100).round(0)
            topic_summary.columns = ["Topic", "Attempts", "Correct", "Accuracy %"]
            st.dataframe(topic_summary, use_container_width=True)
        else:
            st.info("No quiz attempts yet — head to the Adaptive Quiz tab to get started.")

        st.subheader("🔥 Activity Heatmap (last 30 days)")
        today = date.today()
        days = [(today - timedelta(days=i)).isoformat() for i in range(29, -1, -1)]
        activity_set = set(activity_dates)
        heat_df = pd.DataFrame({
            "date": days,
            "active": [1 if d in activity_set else 0 for d in days]
        })
        fig2 = px.bar(heat_df, x="date", y="active", height=200)
        fig2.update_layout(showlegend=False, yaxis=dict(showticklabels=False, title=""), xaxis=dict(title=""))
        st.plotly_chart(fig2, use_container_width=True)

        streak = 0
        for i in range(30):
            d = (today - timedelta(days=i)).isoformat()
            if d in activity_set:
                streak += 1
            else:
                break
        st.metric("🔥 Current Streak", f"{streak} day(s)")

# ===========================================================================
# PAGE 4 — LMS Integration (mocked — stands in for Moodle REST API sync)
# ===========================================================================
elif page == "📚 LMS Integration":
    st.header("📚 LMS Integration")
    st.caption("In the original build this synced live from Semat's Moodle LMS via REST API. Here it's mocked with static course structure — same data shape a real sync would return.")

    mock_courses = {
        "AWS Solutions Architect": [
            {"module": "Module 1: IAM Fundamentals", "status": "✅ Complete"},
            {"module": "Module 2: EC2 & Compute", "status": "✅ Complete"},
            {"module": "Module 3: S3 & Storage", "status": "🔄 In Progress"},
            {"module": "Module 4: VPC Networking", "status": "⬜ Not Started"},
        ],
        "Docker Zero to Hero": [
            {"module": "Module 1: Docker Basics", "status": "✅ Complete"},
            {"module": "Module 2: Images & Dockerfiles", "status": "✅ Complete"},
            {"module": "Module 3: Container Networking", "status": "🔄 In Progress"},
        ],
        "Kubernetes Fundamentals": [
            {"module": "Module 1: Cluster Architecture", "status": "✅ Complete"},
            {"module": "Module 2: Core Concepts", "status": "🔄 In Progress"},
        ],
    }

    st.subheader(f"Course: {course}")
    df = pd.DataFrame(mock_courses[course])
    st.table(df)
    st.caption("Synced from: Semat Moodle LMS (mocked) · Last sync: just now")

# ===========================================================================
# PAGE 5 — Instructor Analytics
# ===========================================================================
elif page == "👨‍🏫 Instructor Analytics":
    st.header("👨‍🏫 Instructor Analytics Panel")
    st.caption("Cohort-level view across all learners — mirrors the original Metabase-powered panel.")

    quiz_data = db.get_all_quiz_attempts()
    tutor_data = db.get_all_tutor_queries()
    learners = db.get_all_learners()

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Learners", len(learners))
    col2.metric("Total Quiz Attempts", len(quiz_data))
    col3.metric("Total Tutor Queries", len(tutor_data))

    st.divider()

    if quiz_data:
        st.subheader("Cohort Quiz Scores by Topic")
        qdf = pd.DataFrame([dict(r) for r in quiz_data])
        topic_perf = qdf.groupby("topic")["correct"].agg(["count", "mean"]).reset_index()
        topic_perf["mean"] = (topic_perf["mean"] * 100).round(0)
        topic_perf.columns = ["Topic", "Attempts", "Avg Accuracy %"]
        fig = px.bar(topic_perf, x="Topic", y="Avg Accuracy %", color="Topic", height=350)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No quiz data yet across the cohort.")

    if tutor_data:
        st.subheader("🔥 AI Tutor Query Heatmap (by topic — darker = more confusion)")
        tdf = pd.DataFrame([dict(r) for r in tutor_data])
        topic_counts = tdf["topic_guess"].value_counts().reset_index()
        topic_counts.columns = ["Source File", "Query Count"]
        fig2 = px.bar(topic_counts, x="Source File", y="Query Count", color="Query Count",
                      color_continuous_scale="Reds", height=300)
        st.plotly_chart(fig2, use_container_width=True)

        st.subheader("Recent Tutor Queries (raw log)")
        st.dataframe(tdf[["name", "segment", "query", "topic_guess", "timestamp"]].head(20),
                     use_container_width=True)
    else:
        st.info("No tutor queries logged yet across the cohort.")

    st.divider()
    st.subheader("⚠️ Learner Risk Flags")
    st.caption("Learners with fewer than 2 active sessions in the last 7 days")
    if learners:
        risk_rows = []
        for l in learners:
            dates = db.get_learner_activity_dates(l["id"])
            recent = [d for d in dates if datetime.fromisoformat(d) > datetime.now() - timedelta(days=7)]
            if len(recent) < 2:
                risk_rows.append({"Learner": l["name"], "Segment": l["segment"],
                                   "Active Days (last 7)": len(recent), "Flag": "🔴 At Risk"})
        if risk_rows:
            st.dataframe(pd.DataFrame(risk_rows), use_container_width=True)
        else:
            st.success("No learners currently flagged as at-risk.")
