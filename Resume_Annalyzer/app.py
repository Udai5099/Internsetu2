# app.py (improved)
import streamlit as st
import plotly.graph_objects as go
from typing import List, Dict
import json
import io
from analyzer import full_analysis_pipeline

# Must be called before any other Streamlit calls that create UI
st.set_page_config(page_title="AI Resume Analyzer", layout="wide")

def _render_score_gauge(score: int):
    if score >= 75:
        color = "#28a745"  # Green
    elif score >= 50:
        color = "#ffc107"  # Yellow
    else:
        color = "#dc3545"  # Red

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number={"suffix": "%", "font": {"size": 40}},
        gauge={
            'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': "darkblue"},
            'bar': {'color': color},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "gray",
        },
        title={'text': "ATS Compatibility Score", 'font': {'size': 24}}
    ))
    fig.update_layout(height=300, margin=dict(l=20, r=20, t=50, b=20))
    st.plotly_chart(fig, use_container_width=True)

def _create_skill_badges(skills: List[str]) -> str:
    if not skills:
        return "No specific skills detected."
    badges = [
        f'<span style="background-color: #e3f2fd; color: #1976d2; padding: 5px 10px; border-radius: 15px; margin: 3px; display: inline-block; font-weight: 500;">{skill}</span>'
        for skill in skills
    ]
    return " ".join(badges)

def _render_analysis(result: Dict[str, any]):
    analysis = result["basic_analysis"]
    ats_score = result.get("ats_score", 0)
    ai_recommendations = result.get("ai_recommendations", {}) or {}
    ai_available = result.get("ai_available", False)

    st.markdown("---")
    st.markdown("## 📊 Resume Analysis Results")

    # ATS Score Gauge with contextual messages
    _render_score_gauge(ats_score)
    if ats_score >= 75:
        st.success(f"🎉 Excellent! Your resume scored {ats_score}%, indicating strong ATS compatibility.")
    elif ats_score >= 50:
        st.warning(f"⚠️ Good score of {ats_score}%. There's some room for improvement to better align with ATS requirements.")
    else:
        st.error(f"❌ Score of {ats_score}%. Your resume may need significant optimization for ATS compatibility.")

    st.markdown("---")

    # AI-Powered Feedback Section
    st.markdown("### 🤖 AI-Powered Feedback")
    if not ai_available:
        st.info("AI analysis is temporarily unavailable. The basic analysis below is still available.")
    else:
        summary = ai_recommendations.get("summaryParagraph", "No summary available.")
        st.markdown(f"> {summary}")  # Display summary as a blockquote
        st.markdown("<br>", unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 🚀 Recommended Career Paths")
            jobs = ai_recommendations.get("jobRecommendations", [])
            if jobs:
                for job in jobs:
                    st.success(f"• **{job}**")
            else:
                st.write("No recommendations provided.")

        with col2:
            st.markdown("#### 🧠 Skills to Learn Next")
            suggestions = ai_recommendations.get("learningSuggestions", [])
            if suggestions:
                for suggestion in suggestions:
                    st.info(f"• {suggestion}")
            else:
                st.write("No suggestions provided.")

    st.markdown("---")

    # Additional Metrics Section
    st.markdown("### 📈 Additional Metrics")
    metrics_col1, metrics_col2, metrics_col3 = st.columns(3)

    with metrics_col1:
        word_count = analysis.get("_word_count", 0)
        st.metric("Word Count", f"{word_count:,}")
        if 300 <= word_count <= 800:
            st.success("✅ Optimal length")
        elif word_count < 300:
            st.warning("⚠️ Too short")
        else:
            st.warning("⚠️ Too long")

    with metrics_col2:
        quant_achievements = analysis.get("_quant_achievements", 0)
        st.metric("Quantifiable Achievements", quant_achievements)
        if quant_achievements >= 3:
            st.success("✅ Strong metrics")
        elif quant_achievements >= 1:
            st.info("ℹ️ Good start")
        else:
            st.warning("⚠️ Add more metrics")

    with metrics_col3:
        exp_val = analysis.get('experience_level', 0.0)
        st.metric("Detected Experience", f"{exp_val:.1f} years")
        if exp_val == 0.0:
            st.warning("⚠️ Experience not detected")
        else:
            st.success("✅ Experience found")

    st.markdown("#### 💼 Skills Found")
    st.markdown(_create_skill_badges(analysis.get("skills_found", [])), unsafe_allow_html=True)

    # Raw AI JSON for debugging (collapsible)
    with st.expander("Show raw AI JSON output (for debugging)"):
        st.json(ai_recommendations)

    # Provide a downloadable JSON report
    report = {
        "resume_text": result.get("resume_text", ""),
        "basic_analysis": analysis,
        "ats_score": ats_score,
        "ai_recommendations": ai_recommendations
    }
    buf = io.BytesIO()
    buf.write(json.dumps(report, indent=2).encode("utf-8"))
    buf.seek(0)
    st.download_button("📥 Download analysis (JSON)", data=buf, file_name="resume_analysis.json", mime="application/json")

def page_resume_analyzer():
    st.title("📄 AI Resume Analyzer")
    st.write("Upload your resume to get an ATS score and AI-powered feedback.")

    # Use a form so file upload + analyze are one atomic action
    with st.form(key="analyze_form"):
        uploaded_file = st.file_uploader("Upload Your Resume", type=["pdf", "docx", "doc"])
        submitted = st.form_submit_button(label="Analyze Resume")

    if submitted:
        if not uploaded_file:
            st.error("Please upload a resume file before clicking Analyze.")
            return

        with st.spinner("Analyzing your resume... 🤖"):
            try:
                result = full_analysis_pipeline(uploaded_file)
            except Exception as e:
                st.error(f"Unexpected error during analysis: {e}")
                return

        if not result.get("success"):
            st.error(f"Analysis failed: {result.get('error_message', 'Unknown error')}")
            return

        # save to session so results persist across reruns
        st.session_state["last_analysis"] = result
        _render_analysis(result)

    # If already analyzed earlier in the session, show it
    elif "last_analysis" in st.session_state:
        st.markdown("### 🔁 Previously analyzed (cached in session)")
        _render_analysis(st.session_state["last_analysis"])

if __name__ == "__main__":
    page_resume_analyzer()
