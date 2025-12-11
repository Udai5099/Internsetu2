# app.py (Improved UI + Dark/Light Toggle + Fixes)
import streamlit as st
import plotly.graph_objects as go
from typing import List, Dict
import json
import io
from analyzer import full_analysis_pipeline

st.set_page_config(page_title="AI Resume Analyzer", layout="wide")

if "theme" not in st.session_state:
    st.session_state["theme"] = "dark"

def toggle_theme():
    st.session_state["theme"] = "light" if st.session_state["theme"] == "dark" else "dark"

def apply_theme():
    if st.session_state["theme"] == "dark":
        st.markdown("""
        <style>
            body, .stApp { background-color: #0e0f11 !important; color: white !important; }
            .metric-box, .card { background:#1b1c1f; padding:18px; border-radius:12px; }
            .toggle-container { position: absolute; top: 20px; right: 30px; }
        </style>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <style>
            body, .stApp { background-color: #ffffff !important; color: #000000 !important; }
            .metric-box, .card { background:#f5f5f5; padding:18px; border-radius:12px; }
            .toggle-container { position: absolute; top: 20px; right: 30px; }
        </style>
        """, unsafe_allow_html=True)

apply_theme()

st.markdown("""
<div class="toggle-container">
    <label class="switch">
      <input type="checkbox" id="themeToggle">
      <span class="slider round"></span>
    </label>
</div>

<style>
.switch {
  position: relative;
  display: inline-block;
  width: 52px;
  height: 28px;
}
.switch input { display:none; }
.slider {
  position: absolute;
  cursor: pointer;
  background-color: #ccc;
  border-radius: 34px;
  top: 0; left: 0; right: 0; bottom: 0;
  transition: .4s;
}
.slider:before {
  position: absolute;
  content: "";
  height: 22px; width: 22px;
  left: 4px; bottom: 3px;
  background-color: white;
  transition: .4s;
  border-radius: 50%;
}
input:checked + .slider {
  background-color: #2196F3;
}
input:checked + .slider:before {
  transform: translateX(24px);
}
</style>

<script>
const themeToggle = window.parent.document.querySelector("#themeToggle");
themeToggle.checked = (%s === "light");

themeToggle.onclick = function() {
    window.parent.postMessage({toggle: true}, "*");
};
</script>
""" % ("'light'" if st.session_state["theme"] == "light" else "'dark'"),
unsafe_allow_html=True)

# Listen for toggle events
msg = st.experimental_get_query_params()
if "toggle" in msg:
    toggle_theme()
    st.experimental_set_query_params()  # clear message
    st.rerun()


def _render_score_gauge(score: int):
    color = "#28a745" if score >= 75 else "#ffc107" if score >= 50 else "#dc3545"

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number={"suffix": "%", "font": {"size": 40}},
        gauge={'axis': {'range': [None, 100]}, 'bar': {'color': color}},
        title={'text': "ATS Compatibility Score", 'font': {'size': 24}}
    ))

    fig.update_layout(height=300)
    st.plotly_chart(fig, use_container_width=True, key=f"gauge_{score}")

# -----------------------------------------------------------
# Skill Badges
# -----------------------------------------------------------
def _create_skill_badges(skills: List[str]) -> str:
    if not skills:
        return "No skills detected."
    return " ".join([
        f'<span style="background:#e3f2fd;color:#1976d2;padding:6px 12px;border-radius:12px;margin:4px;display:inline-block;">{s}</span>'
        for s in skills
    ])

def _render_analysis(result: Dict[str, any]):
    analysis = result["basic_analysis"]
    ats_score = result["ats_score"]
    ai = result.get("ai_recommendations", {})

    st.markdown("## 📊 Resume Analysis")

    # Gauge
    _render_score_gauge(ats_score)

    # Score Message
    if ats_score >= 75: st.success(f"Excellent score ({ats_score}%).")
    elif ats_score >= 50: st.warning(f"Moderate score ({ats_score}%). Improve for better ATS results.")
    else: st.error(f"Low score ({ats_score}%). Significant optimization needed.")

    st.markdown("---")
    st.subheader("🤖 AI Insights")

    st.markdown(f"> {ai.get('summaryParagraph', 'No AI summary available.')}")
    st.markdown("")

    colA, colB = st.columns(2)
    with colA:
        st.markdown("### 🚀 Career Recommendations")
        for j in ai.get("jobRecommendations", []):
            st.success("• " + j)

    with colB:
        st.markdown("### 🧠 Learning Suggestions")
        for s in ai.get("learningSuggestions", []):
            st.info("• " + s)

    st.markdown("---")
    st.subheader("📈 Metrics")

    col1, col2, col3 = st.columns(3)
    col1.metric("Word Count", analysis["_word_count"])
    col2.metric("Achievements", analysis["_quant_achievements"])
    col3.metric("Experience", f"{analysis['experience_level']} yrs")

    st.markdown("### 💼 Skills Found")
    st.markdown(_create_skill_badges(analysis["skills_found"]), unsafe_allow_html=True)

def page_resume_analyzer():
    st.title("📄 AI Resume Analyzer")

    uploaded = st.file_uploader("Upload Resume", type=["pdf", "docx", "doc"])

    if st.button("Analyze Resume"):
        if not uploaded:
            st.error("Upload a resume first.")
            return

        with st.spinner("Analyzing..."):
            result = full_analysis_pipeline(uploaded)

        if not result.get("success"):
            st.error(result["error_message"])
            return

        st.session_state["analysis"] = result

    if "analysis" in st.session_state:
        _render_analysis(st.session_state["analysis"])


if __name__ == "__main__":
    page_resume_analyzer()
