from typing import Dict, Any, List, Optional
import re
from streamlit.runtime.uploaded_file_manager import UploadedFile
import streamlit as st
import google.genai as genai
import json
import os
from pdf_parser import extract_text_from_file, TextExtractionError

# ------------------- Skills ----------------------
PREDEFINED_SKILLS = [
    "Python", "Java", "JavaScript", "SQL", "C++", "Project Management",
    "Data Analysis", "Machine Learning", "Deep Learning", "NLP",
    "Communication", "Leadership", "AWS", "Azure", "GCP", "Docker", "Kubernetes",
]

def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()

def _find_skills(text: str) -> List[str]:
    return sorted({s for s in PREDEFINED_SKILLS if re.search(rf"(?i)\b{s}\b", text)})

def _parse_years_of_experience(text: str) -> Optional[float]:
    patterns = [
        r"(?i)\b(\d{1,2})\s*\+?\s*(years?|yrs?|yoe)\b",
        r"(?i)(\d{1,2})\s*to\s*(\d{1,2})\s*years",
        r"(?i)experience.{0,20}(\d{1,2})\s*years"
    ]
    candidates = []
    for p in patterns:
        for m in re.finditer(p, text):
            nums = [float(g) for g in m.groups() if g and g.isdigit()]
            if nums:
                candidates.append(max(nums))
    return max(candidates) if candidates else 0.0

def _detect_quantifiable_achievements(text: str) -> int:
    return (
        len(re.findall(r"\b\d+\s*%", text)) +
        len(re.findall(r"\$\s?\d[\d,]*(k|m|b)?", text, flags=re.IGNORECASE)) +
        len(re.findall(r"\b(increased|reduced|improved|boosted|saved|grew|decreased)\b.{0,40}\d+", text, flags=re.IGNORECASE))
    )

# ------------------- Resume Analysis ----------------------
def analyze_resume(resume_text: str) -> Dict[str, Any]:
    normalized = _normalize_text(resume_text)
    lc = normalized.lower()

    return {
        "skills_found": _find_skills(lc),
        "experience_level": _parse_years_of_experience(lc),
        "_word_count": len(normalized.split()),
        "_quant_achievements": _detect_quantifiable_achievements(lc)
    }

# ------------------- ATS Score ----------------------
def generate_ats_score(analysis: Dict[str, Any]) -> int:
    score = 0

    score += 55 * (len(analysis["skills_found"]) / len(PREDEFINED_SKILLS))
    score += min(analysis["_quant_achievements"], 4) * 5

    wc = analysis["_word_count"]
    if 300 <= wc <= 800:
        score += 20
    else:
        penalty = min(20, abs(wc - 550) * 0.05)
        score += max(0, 20 - penalty)

    if analysis["experience_level"] >= 1:
        score += 5

    return int(max(0, min(100, score)))

# ------------------- Gemini Recommendations ----------------------
def generate_gemini_recommendations(resume_text: str) -> Dict[str, Any]:
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            st.error("❌ GEMINI_API_KEY missing in environment variables.")
            return {}

        client = genai.Client(api_key=api_key)

        prompt = f"""
        Act as a career expert. Analyze this resume and return ONLY valid JSON:

        Resume:
        {resume_text}

        JSON format:
        {{
            "summaryParagraph": "string",
            "jobRecommendations": ["string", "string", "string"],
            "learningSuggestions": ["string", "string", "string"]
        }}
        """

        # ⭐ Correct new API call ⭐
        response = client.models.text.generate(
            model="gemini-1.0-pro",
            prompt=prompt
        )

        output = response.result_text  # ⭐ Correct field ⭐
        return json.loads(output)

    except json.JSONDecodeError:
        st.error("⚠ Gemini returned invalid JSON.")
        return {}

    except Exception as e:
        st.error(f"⚠ Gemini API Error: {e}")
        return {}

# ------------------- Full Pipeline ----------------------
def full_analysis_pipeline(uploaded_file: UploadedFile) -> Dict[str, Any]:
    try:
        resume_text = extract_text_from_file(uploaded_file)

        analysis = analyze_resume(resume_text)
        ats_score = generate_ats_score(analysis)
        ai_output = generate_gemini_recommendations(resume_text)

        return {
            "success": True,
            "resume_text": resume_text,
            "basic_analysis": analysis,
            "ats_score": ats_score,
            "ai_recommendations": ai_output,
            "ai_available": bool(ai_output)
        }

    except Exception as e:
        return {"success": False, "error_message": str(e)}
