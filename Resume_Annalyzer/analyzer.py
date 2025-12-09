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
    found_skills = set()
    for skill in PREDEFINED_SKILLS:
        pattern = r"(?i)\b" + re.escape(skill) + r"\b"
        if re.search(pattern, text):
            found_skills.add(skill)
    return sorted(found_skills)

def _parse_years_of_experience(text: str) -> Optional[float]:
    candidates: List[float] = []
    patterns = [
        re.compile(r"(?i)\b(\d{1,2})\s*\+?\s*(?:years?|yrs?|yoe)\b"),
        re.compile(r"(?i)(\d{1,2})\s*to\s*(\d{1,2})\s*years"),
        re.compile(r"(?i)experience[^\n.]{0,20}(\d{1,2})\s*years")
    ]
    for pat in patterns:
        for m in pat.finditer(text):
            nums = [float(g) for g in m.groups() if g.isdigit()]
            if nums:
                candidates.append(max(nums))
    return max(candidates) if candidates else 0.0

def _detect_quantifiable_achievements(text: str) -> int:
    count = 0
    count += len(re.findall(r"\b\d+\s*%", text))
    count += len(re.findall(r"\$\s?\d+[\d,]*(?:k|m|b)?", text))
    count += len(re.findall(
        r"\b(increased|reduced|improved|boosted|saved|grew|decreased)\b.{0,40}\b\d+\b",
        text, flags=re.IGNORECASE
    ))
    return count

# ------------------- Resume Analysis ----------------------
def analyze_resume(resume_text: str) -> Dict[str, Any]:
    normalized = _normalize_text(resume_text)
    lowercase_text = normalized.lower()

    return {
        "skills_found": _find_skills(lowercase_text),
        "experience_level": _parse_years_of_experience(lowercase_text),
        "_word_count": len(normalized.split()),
        "_quant_achievements": _detect_quantifiable_achievements(lowercase_text)
    }

# ------------------- ATS Score ----------------------
def generate_ats_score(analysis_dict: Dict[str, Any]) -> int:
    total_points = 0.0

    skills_found = analysis_dict.get("skills_found", [])
    skill_ratio = len(skills_found) / len(PREDEFINED_SKILLS)
    total_points += 55 * skill_ratio

    quant_count = analysis_dict.get("_quant_achievements", 0)
    total_points += min(quant_count, 4) * 5

    word_count = analysis_dict.get("_word_count", 0)
    if 300 <= word_count <= 800:
        total_points += 20
    else:
        distance = abs(word_count - 550)
        penalty = min(20, distance * 0.05)
        total_points += max(0, 20 - penalty)

    if analysis_dict.get("experience_level", 0) >= 1:
        total_points += 5

    return int(min(100, max(0, total_points)))

# ------------------- Gemini Recommendations ----------------------
def generate_gemini_recommendations(resume_text: str) -> Dict[str, Any]:
    try:
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            st.error("❌ GEMINI_API_KEY missing in environment variables.")
            return {}
        client = genai.Client(
            api_key=api_key
        )

        response = client.models.generate_content(
            model="gemini-pro",
            contents=f"""
            Analyze this resume and return ONLY JSON.

            Resume:
            {resume_text}

            JSON format:
            {{
                "summaryParagraph": "string",
                "jobRecommendations": ["string", "string", "string"],
                "learningSuggestions": ["string", "string", "string"]
            }}
            """
        )

        return json.loads(response.text)

    except json.JSONDecodeError:
        st.error("⚠ Gemini returned invalid JSON.")
        return {}

    except Exception as e:
        st.error(f"⚠ Gemini API Error: {e}")
        return {}

# ------------------- Full Pipeline ----------------------
def full_analysis_pipeline(uploaded_file: UploadedFile) -> Dict[str, Any]:
    result = {"success": False}

    try:
        resume_text = extract_text_from_file(uploaded_file)
        basic_analysis = analyze_resume(resume_text)
        ats_score = generate_ats_score(basic_analysis)
        ai_recommendations = generate_gemini_recommendations(resume_text)

        result.update({
            "success": True,
            "resume_text": resume_text,
            "basic_analysis": basic_analysis,
            "ats_score": ats_score,
            "ai_recommendations": ai_recommendations,
            "ai_available": bool(ai_recommendations)
        })

    except Exception as e:
        result["error_message"] = str(e)

    return result





