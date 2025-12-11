import streamlit as st
import plotly.graph_objects as go
from typing import List, Dict
from analyzer import full_analysis_pipeline

st.set_page_config(page_title="AI Resume Analyzer", layout="wide")

if "theme" not in st.session_state:
    st.session_state["theme"] = "dark"

def toggle_theme():
    st.session_state["theme"] = (
        "light" if st.session_state["theme"] == "dark" else "dark"
    )

def apply_theme():
    theme = st.session_state["theme"]

    if theme == "dark":
        st.markdown("""
            <style>
                body, .stApp { background-color: #0e0f11 !important; color: white !important; }
                .metric-box, .card { background:#1b1c1f !important; padding:18px; border-radius:12px; }
            </style>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
            <style>
                body, .stApp { background-color: #ffffff !important; color: black !important; }
                .metric-box, .card { background:#f5f5f5 !important; padding:18px; border-radius:12px; }
            </style>
        """, unsafe_allow_html=True)

apply_theme()

current = st.session_state["theme"]
is_light = "checked" if current == "light" else ""

st.markdown(f"""
<div style="position:fixed; top:20px; right:30px; z-index:9999;">
  <label class="switch">
    <input type="checkbox" id="themeToggle" {is_light}>
    <span class="slider round"></span>
  </label>
</div>

<style>
.switch {{
  position: relative;
  display: inline-block;
  width: 52px;
  height: 28px;
}}
.switch input {{
  display: none;
}}
.slider {{
  position: absolute;
  cursor: pointer;
  background-color: #ccc;
  border-radius: 34px;
  top: 0; left: 0; right: 0; bottom: 0;
  transition: .4s;
}}
.slider:before {{
  position: absolute;
  content: "";
  height: 22px; width: 22px;
  left: 4px; bottom: 3px;
  background-color: white;
  border-radius: 50%;
  transition: .4s;
}}
input:checked + .slider {{
  background-color: #2196F3;
}}
input:checked + .slider:before {{
  transform: translateX(24px);
}}
</style>

<script>
window.addEventListener("load", function() {{
    const checkbox = window.parent.document.querySelector("#themeToggle");
    checkbox.onclick = function() {{
        window.parent.postMessage({{toggleTheme: true}}, "*");
    }};
}});
</script>
""", unsafe_allow_html=True)

params = st.experimental_get_query_params()
if "toggleTheme" in params:
    toggle_theme()
    st.experimental_set_query_params()
    st.rerun()
def _render_score_gauge(score: int):
    color = "#28a745" if score >= 75 else "#ffc107" if score >= 50 else "#dc3545"

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number={"suffix": "%", "font": {"size": 40}},
        gauge={'axis': {'range': [None, 100]}, 'bar': {'color': color}},
        title={'text': "ATS Compatibility Score", 'font': {'size': 24}},
    ))

    fig.update_layout(height=300)
    st.plotly_chart(fig, use_container_width=True, key=f"gauge_{score}")

def _create_skill_badges(skills: List[str]) -> str:
    if not skills:
        return "No skills detected."
    return " ".join(
        f'<span style="background:#e3f2fd;color:#1976d2;padding:6px 12px;border-radius:12px;margin:4px;display:inline-block;">{s}</span>'
        for s in skills
    )

def _render_analysis(result: Dict[str, any]):
    analysis = result["basic_analysis"]
    ats_score = result["ats_score"]
    ai = result.get("ai_recommendations", {})

    st.markdown("## 📊 Resume Analysis")
    _render_score_gauge(ats_score)

    # ATS Summary
    if ats_score >= 75:
        st.success(f"Excellent score ({ats_score}%).")
    elif ats_score >= 50:
        st.warning(f"Moderate score ({ats_score}%). Some optimization needed.")
    else:
        st.error(f"Low score ({ats_score}%). Significant improvements required.")

    st.markdown("---")
    st.subheader("🤖 AI Insights")
    st.markdown(f"> {ai.get('summaryParagraph', 'No AI summary available.')}")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🚀 Career Recommendations")
        for j in ai.get("jobRecommendations", []):
            st.success(f"• {j}")

    with col2:
        st.markdown("### 🧠 Learning Suggestions")
        for s in ai.get("learningSuggestions", []):
            st.info(f"• {s}")

    st.markdown("---")
    st.subheader("📈 Metrics")

    colA, colB, colC = st.columns(3)
    colA.metric("Word Count", analysis["_word_count"])
    colB.metric("Achievements", analysis["_quant_achievements"])
    colC.metric("Experience", f"{analysis['experience_level']} yrs")
    st.markdown("### 💼 Skills Found")
    st.markdown(_create_skill_badges(analysis["skills_found"]), unsafe_allow_html=True)

def page_resume_analyzer():
    st.title("📄 AI Resume Analyzer")

    uploaded = st.file_uploader("Upload Resume", type=["pdf", "docx", "doc"])

    if st.button("Analyze Resume"):
        if not uploaded:
            st.error("Please upload a resume first.")
            return

        with st.spinner("Analyzing..."):
            result = full_analysis_pipeline(uploaded)

        if not result.get("success"):
            st.error(result.get("error_message", "Unknown error"))
            return

        st.session_state["analysis"] = result

    if "analysis" in st.session_state:
        _render_analysis(st.session_state["analysis"])

if __name__ == "__main__":
    page_resume_analyzer()
