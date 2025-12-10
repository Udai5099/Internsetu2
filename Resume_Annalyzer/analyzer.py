from typing import Dict, Any, List, Optional
import re
from streamlit.runtime.uploaded_file_manager import UploadedFile
import streamlit as st
import google.genai as genai
import json
import os
from pdf_parser import extract_text_from_file, TextExtractionError

# ------------------- Skills ----------------------
PREDEFINED_SKILLS: List[str] = [
    "Python", "Java", "JavaScript", "SQL", "C++", "Project Management",
    "Data Analysis", "Machine Learning", "Deep Learning", "NLP",
    "Communication", "Leadership", "AWS", "Azure", "GCP", "Docker", "Kubernetes",
]

def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()

def _find_skills(text: str) -> List[str]:
    found = set()
    for skill in PREDEFINED_SKILLS:
        if re.search(rf"(?i)\b{re.escape(skill)}\b", text):
            found.add(skill)
    return sorted(found)

def _parse_years_of_experience(text: str) -> Optional[float]:
    patterns = [
        r"(?i)\b(\d{1,2})\s*\+?\s*(years?|yrs?|yoe)\b",
        r"(?i)(\d{1,2})\s*to\s*(\d{1,2})\s*years",
        r"(?i)experience.{0,20}(\d{1,2})\s*years"
    ]
    candidates = []
    for pat in patterns:
        for m in re.finditer(pat, text):
            nums = [float(g) for g in m.groups() if g and g.isdigit()]
            if nums:
                candidates.append(max(nums))
    return max(candidates) if candidates else 0.0

def _detect_quantifiable_achievements(text: str) -> int:
    count = 0
    count += len(re.findall(r"\b\d+\s*%", text))
    count += len(re.findall(r"\$\s?\d[\d,]*(k|m|b)?", text, flags=re.IGNORECASE))
    count += len(re.findall(
        r"\b(increased|reduced|improved|boosted|saved|grew|decreased)\b.{0,40}\d+",
        text,
        flags=re.IGNORECASE
    ))
    return count

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
    score = 0.0

    skills = analysis.get("skills_found", [])
    score += 55 * (len(skills) / len(PREDEFINED_SKILLS))

    score += min(analysis.get("_quant_achievements", 0), 4) * 5

    wc = analysis.get("_word_count", 0)
    if 300 <= wc <= 800:
        score += 20
    else:
        penalty = min(20, abs(wc - 550) * 0.05)
        score += max(0, 20 - penalty)

    if analysis.get("experience_level", 0) >= 1:
        score += 5

    return int(max(0, min(100, score)))

# ------------------- Gemini Recommendations ----------------------
def generate_gemini_recommendations(resume_text: str) -> Dict[str, Any]:
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            st.error("❌ GEMINI_API_KEY missing in environment variables.")
            return {}

        # New GenAI client (correct)
        client = genai.Client(api_key=api_key)

        prompt = f"""
        Act as a career expert. Analyze this resume and return ONLY valid JSON.

        Resume:
        {resume_text}

        JSON format:
        {{
            "summaryParagraph": "string",
            "jobRecommendations": ["string", "string", "string"],
            "learningSuggestions": ["string", "string", "string"]
        }}
        """

        # Correct API call
        response = client.models.generate(
            model="gemini-1.0-pro",   # Free-tier safe model
            input=prompt
        )

        # Extract text
        output = response.text.strip()

        return json.loads(output)

    except json.JSONDecodeError:
        st.error("⚠ Gemini returned invalid JSON output.")
        return {}

    except Exception as e:
        st.error(f"⚠ Gemini API Error: {e}")
        return {}

# ------------------- Full Pipeline ----------------------
def full_analysis_pipeline(uploaded_file: UploadedFile) -> Dict[str, Any]:
    result = {"success": False}

    try:
        resume_text = extract_text_from_file(uploaded_file)

        basic = analyze_resume(resume_text)
        ats = generate_ats_score(basic)
        ai = generate_gemini_recommendations(resume_text)

        result.update({
            "success": True,
            "resume_text": resume_text,
            "basic_analysis": basic,
            "ats_score": ats,
            "ai_recommendations": ai,
            "ai_available": bool(ai)
        })

    except Exception as e:
        result["error_message"] = str(e)

    return result
