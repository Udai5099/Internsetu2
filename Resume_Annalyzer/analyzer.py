from typing import Dict, Any, List, Optional
import re
from streamlit.runtime.uploaded_file_manager import UploadedFile
import streamlit as st
import google.generativeai as genai
import json

# This assumes you have a pdf_parser.py file
from pdf_parser import extract_text_from_file, TextExtractionError

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
    return sorted(list(found_skills))

def _parse_years_of_experience(text: str) -> Optional[float]:
    candidates: List[float] = []
    patterns = [
        re.compile(r"(?i)\b(\d{1,2})\s*\+?\s*(?:years?|yrs?|yoe)\b"),
        re.compile(r"(?i)(\d{1,2})\s*to\s*(\d{1,2})\s*years"),
        re.compile(r"(?i)experience[^\n.]{0,20}(\d{1,2})\s*years")
    ]
    for pat in patterns:
        for m in pat.finditer(text):
            nums = [float(g) for g in m.groups() if g and g.isdigit()]
            if nums:
                candidates.append(max(nums))
    return max(candidates) if candidates else 0.0

# ADDED BACK: Function to detect quantifiable achievements for ATS score
def _detect_quantifiable_achievements(text: str) -> int:
    count = 0
    # Percentages like 20%
    count += len(re.findall(r"\b\d+\s*%", text))
    # Monetary gains/savings like $1M, $200k
    count += len(re.findall(r"\$\s?\d+[\d,]*(?:k|m|b)?", text, flags=re.IGNORECASE))
    # Action verbs followed by numbers: increased 20, reduced 15, improved 30
    count += len(re.findall(r"\b(increased|reduced|improved|boosted|saved|grew|decreased)\b[^\n%$]{0,40}\b\d+\b", text, flags=re.IGNORECASE))
    return count

def analyze_resume(resume_text: str) -> Dict[str, Any]:
    normalized = _normalize_text(resume_text)
    lowercase_text = normalized.lower()
    return {
        "skills_found": _find_skills(lowercase_text),
        "experience_level": _parse_years_of_experience(lowercase_text),
        "_word_count": len(normalized.split()),
        # ADDED BACK: Quantifiable achievements data
        "_quant_achievements": _detect_quantifiable_achievements(lowercase_text)
    }

# ADDED BACK: Function to generate the ATS score
def generate_ats_score(analysis_dict: Dict[str, Any]) -> int:
    total_points = 0.0
    
    # Skills coverage: up to 55 points
    skills_found = analysis_dict.get("skills_found", [])
    skill_ratio = len(skills_found) / len(PREDEFINED_SKILLS)
    total_points += 55.0 * skill_ratio

    # Quantifiable achievements: up to 20 points
    quant_count = analysis_dict.get("_quant_achievements", 0)
    total_points += min(quant_count, 4) * 5.0

    # Length: ideal between 300 and 800 words -> up to 20 points
    word_count = analysis_dict.get("_word_count", 0)
    if 300 <= word_count <= 800:
        total_points += 20.0
    elif word_count > 0:
        distance = 300 - word_count if word_count < 300 else word_count - 800
        penalty = min(20.0, distance * 0.05)
        total_points += max(0.0, 20.0 - penalty)

    # Experience present: +5 points if detected
    if analysis_dict.get("experience_level", 0.0) >= 1.0:
        total_points += 5.0

    return int(round(max(0.0, min(100.0, total_points))))

def generate_gemini_recommendations(resume_text: str) -> Dict[str, Any]:
    try:
        api_key = st.secrets.get("GEMINI_API_KEY")
        if not api_key:
            st.error("GEMINI_API_KEY not found in Streamlit secrets.")
            return {}
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")

        prompt = f"""
        Act as an expert career coach.
        Analyze the resume text below and return ONLY valid JSON.

        Resume:
        {resume_text}

        JSON format to return:
        {{
          "summaryParagraph": "string",
          "jobRecommendations": ["string", "string", "string"],
          "learningSuggestions": ["string", "string", "string"]
        }}
        """

        response = model.generate_content(prompt)

        # Extract text safely
        raw_text = response.text or "{}"

        # Try to convert JSON
        return json.loads(raw_text)

    except Exception as e:
        st.error(f"Error calling Gemini API: {e}")
        return {}


def full_analysis_pipeline(uploaded_file: UploadedFile) -> Dict[str, Any]:
    result = {'success': False, 'error_message': None}
    try:
        resume_text = extract_text_from_file(uploaded_file)
        basic_analysis = analyze_resume(resume_text)
        # ADDED BACK: ATS score calculation is now part of the pipeline
        ats_score = generate_ats_score(basic_analysis)
        ai_recommendations = generate_gemini_recommendations(resume_text)
        
        result.update({
            'success': True,
            'resume_text': resume_text,
            'basic_analysis': basic_analysis,
            'ats_score': ats_score, # Pass the score to the UI
            'ai_recommendations': ai_recommendations,
            'ai_available': bool(ai_recommendations)
        })
    except (TextExtractionError, Exception) as e:
        result['error_message'] = str(e)
    return result