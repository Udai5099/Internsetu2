# app.py (Dark/Light Theme Toggle Added)
import streamlit as st
import plotly.graph_objects as go
from typing import List, Dict
import json
import io
from analyzer import full_analysis_pipeline

st.set_page_config(page_title="AI Resume Analyzer", layout="wide")

if "theme" not in st.session_state:
    st.session_state["theme"] = "dark"   # default

def toggle_theme():
    st.session_state["theme"] = "light" if st.session_state["theme"] == "dark" else "dark"

def apply_theme():
    if st.session_state["theme"] == "dark":
        st.markdown("""
            <style>
                body, .stApp { background-color: #0e0f11 !important; color: white !important; }
                .stMetric, .stMarkdown, .stText { color: white !important; }
                .card { background-color:#1b1c1f; padding:20px; border-radius:12px; }
            </style>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
            <style>
                body, .stApp { background-color: #ffffff !important; color: #000000 !important; }
                .card { background-color:#f5f5f5; padding:20px; border-radius:12px; }
            </style>
        """, unsafe_allow_html=True)

apply_theme()

def _render_score_gauge(score: int):
    color = "#28a745" if score >= 75 else "#ffc107" if score >= 50 else "#dc3545"
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number={"suffix": "%", "font": {"size": 40}},
        gauge={
            'axis': {'range': [None, 100]},
            'bar': {'color': color},
            'bgcolor': "white",
        },
        title={'text': "ATS Compatibility Score", 'font': {'size': 24}}
    ))
    fig.update_layout(height=300)
    st.plotly_chart(fig, use_container_width=True)

def _create_skill_badges(skills: List[str]) -> str:
    if not skills: 
        return "No skills found."
    return " ".join([
        f'<span style="background:#e3f2fd;color:#1976d2;padding:6px 12px;border-radius:12px;margin:4px;display:inline-block;">{s}</span>'
        for s in skills
    ])

def _render_analysis(result: Dict[str, any]):
    analysis = result["basic_analysis"]
    ats_score = result.get("ats_score", 0)
    ai_recommendations = result.get("ai_recommendations", {}) or {}

    st.markdown("---")
    st.subheader("📊 Resume Analysis Results")

    # Score Gauge
    _render_score_gauge(ats_score)

    # Feedback Message
    if ats_score >= 75:
        st.success(f"Excellent score ({ats_score}%).")
    elif ats_score >= 50:
        st.warning(f"Moderate score ({ats_score}%). Could be improved.")
    else:
        st.error(f"Low score ({ats_score}%). Major improvements needed.")

    st.markdown("---")

    # AI Feedback
    st.subheader("🤖 AI-Powered Insights")
    summary = ai_recommendations.get("summaryParagraph", "AI summary not available.")
    st.markdown(f"> {summary}")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🚀 Recommended Career Paths")
        for j in ai_recommendations.get("jobRecommendations", []):
            st.success("• " + j)

    with col2:
        st.markdown("### 🧠 Learning Suggestions")
        for s in ai_recommendations.get("learningSuggestions", []):
            st.info("• " + s)

    st.markdown("---")

    # Extra Metrics
    st.subheader("📈 Additional Metrics")
    colA, colB, colC = st.columns(3)

    with colA:
        wc = analysis["_word_count"]
        st.metric("Word Count", wc)

    with colB:
        qa = analysis["_quant_achievements"]
        st.metric("Achievements Count", qa)

    with colC:
        exp = analysis["experience_level"]
        st.metric("Experience Detected", f"{exp} years")

    # Skills
    st.subheader("💼 Skills Found")
    st.markdown(_create_skill_badges(analysis["skills_found"]), unsafe_allow_html=True)

def page_resume_analyzer():
    # THEME TOGGLE (Top Right)
    col_t1, col_t2 = st.columns([6, 1])
    with col_t2:
        if st.button("🌙 / ☀️"):
            toggle_theme()
            st.rerun()

    st.title("📄 AI Resume Analyzer")
    st.write("Upload your resume to generate a full ATS score and receive AI insights.")

    uploaded_file = st.file_uploader("Upload Resume", type=["pdf", "docx", "doc"])

    if st.button("Analyze Resume"):
        if not uploaded_file:
            st.error("Please upload a resume before analyzing.")
            return

        with st.spinner("Analyzing..."):
            result = full_analysis_pipeline(uploaded_file)

        if not result.get("success"):
            st.error(result.get("error_message", "Unknown error"))
            return

        st.session_state["analysis"] = result
        _render_analysis(result)

    if "analysis" in st.session_state:
        st.markdown("### 🔁 Last Analysis")
        _render_analysis(st.session_state["analysis"])

if __name__ == "__main__":
    page_resume_analyzer()

