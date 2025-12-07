from typing import List, Dict, Any, Optional, Tuple
import os
import json
import re

# Simple storage location for prototype
JDS_JSON_PATH = os.path.join("data", "jds.json")

# Reuse a basic predefined skills list similar to resume analyzer
PREDEFINED_SKILLS: List[str] = [
    "Python",
    "Java",
    "JavaScript",
    "SQL",
    "C++",
    "Project Management",
    "Data Analysis",
    "Machine Learning",
    "Deep Learning",
    "NLP",
    "Communication",
    "Leadership",
    "AWS",
    "Azure",
    "GCP",
    "Docker",
    "Kubernetes",
]

_STOPWORDS = {
    "and", "or", "the", "a", "an", "with", "to", "for", "of", "in", "on", "by",
    "as", "is", "are", "be", "this", "that", "will", "we", "you", "your", "our",
    "at", "from", "per", "ages", "years", "yr", "yrs", "plus", "experience"
}

def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()

def _find_skills(text: str) -> List[str]:
    found: List[str] = []
    for skill in PREDEFINED_SKILLS:
        pattern = r"(?i)(?<![\w#])" + re.escape(skill) + r"(?![\w+])"
        if re.search(pattern, text):
            found.append(skill)
    return sorted(set(found), key=lambda s: PREDEFINED_SKILLS.index(s) if s in PREDEFINED_SKILLS else s)

def _parse_years_of_experience(text: str) -> Optional[float]:
    # Range e.g., 3-5 years -> take upper bound
    m_range = re.search(r"(?i)(\d{1,2})\s*\-\s*(\d{1,2})\s*(years|yrs|year)", text)
    if m_range:
        try:
            return float(max(int(m_range.group(1)), int(m_range.group(2))))
        except Exception:
            pass

    patterns: List[re.Pattern[str]] = [
        re.compile(r"(?i)(over|approximately|around|about)?\s*(\d{1,2})\s*\+?\s*(years|yrs|y/o|yo|year)"),
        re.compile(r"(?i)(\d{1,2})\s*\+\s*years"),
        re.compile(r"(?i)(\d{1,2})\s*\-?\s*year\b"),
    ]
    for pat in patterns:
        m = pat.search(text)
        if m:
            nums = [float(g) for g in m.groups() if isinstance(g, str) and g.isdigit()]
            if nums:
                return float(nums[-1])
    m_simple = re.search(r"(?i)(\d{1,2})\s*\+?\s*(years|yrs)\b", text)
    if m_simple:
        try:
            return float(m_simple.group(1))
        except Exception:
            return None
    return None

def _extract_keywords(text: str, max_keywords: int = 25) -> List[str]:
    words = re.findall(r"[A-Za-z][A-Za-z\-\+#]{2,}", text)
    kws: List[str] = []
    seen = set()
    for w in words:
        lw = w.lower()
        if lw in _STOPWORDS:
            continue
        if lw in seen:
            continue
        seen.add(lw)
        kws.append(lw)
        if len(kws) >= max_keywords:
            break
    return kws

def parse_job_description(jd_text: str) -> Dict[str, Any]:
    """
    Extract key requirements from a job description: required skills, keywords, and experience.
    """
    normalized = _normalize_text(jd_text)
    lowercase_text = normalized.lower()

    required_skills = _find_skills(lowercase_text)
    experience_years = _parse_years_of_experience(lowercase_text)
    keywords = _extract_keywords(lowercase_text)

    return {
        "required_skills": required_skills,
        "experience_years": experience_years,
        "keywords": keywords,
        "raw_text": normalized,
    }

def calculate_jd_match(resume_analysis_dict: Dict[str, Any], jd_requirements_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute a compatibility score (0-100) between a resume analysis and JD requirements.
    Considers skills overlap, experience alignment, and keyword coverage.
    Returns score, matched/missing skills and keywords.
    """
    resume_skills: List[str] = (resume_analysis_dict or {}).get("skills_found", []) or []
    resume_skills_lc = [s.lower() for s in resume_skills]
    resume_years = (resume_analysis_dict or {}).get("experience_level")
    try:
        resume_years_val = float(resume_years) if resume_years is not None else 0.0
    except Exception:
        resume_years_val = 0.0

    jd_skills: List[str] = (jd_requirements_dict or {}).get("required_skills", []) or []
    jd_skills_lc = [s.lower() for s in jd_skills]
    jd_years = (jd_requirements_dict or {}).get("experience_years")
    try:
        jd_years_val = float(jd_years) if jd_years is not None else 0.0
    except Exception:
        jd_years_val = 0.0

    jd_keywords: List[str] = (jd_requirements_dict or {}).get("keywords", []) or []

    # Skills overlap
    matched_skills = sorted(set(s for s in resume_skills if s.lower() in jd_skills_lc))
    missing_skills = sorted(set(jd_skills) - set(matched_skills))
    skills_ratio = (len(matched_skills) / len(jd_skills)) if jd_skills else 1.0

    # Experience alignment: if resume >= JD -> full credit; else proportional
    if jd_years_val <= 0:
        experience_factor = 1.0
    else:
        experience_factor = max(0.0, min(1.0, resume_years_val / jd_years_val))

    # Keyword coverage: prototype approximation compares JD keywords against resume skills tokens
    combined_resume_tokens = set(resume_skills_lc)
    matched_keywords = sorted([kw for kw in jd_keywords if kw.lower() in combined_resume_tokens])
    missing_keywords = sorted([kw for kw in jd_keywords if kw.lower() not in combined_resume_tokens])
    keyword_ratio = (len(matched_keywords) / len(jd_keywords)) if jd_keywords else 1.0

    # Weighted score: skills 70%, experience 25%, keywords 5%
    score = 100.0 * (0.70 * skills_ratio + 0.25 * experience_factor + 0.05 * keyword_ratio)
    score_int = int(round(max(0.0, min(100.0, score))))

    return {
        "score": score_int,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "matched_keywords": matched_keywords,
        "missing_keywords": missing_keywords,
    }

def save_jd_to_json(jd_dict: Dict[str, Any], json_path: str = JDS_JSON_PATH) -> None:
    """
    Append a JD dict to the JSON store (creates file if missing).
    """
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    existing: List[Dict[str, Any]] = []
    if os.path.isfile(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
                if not isinstance(existing, list):
                    existing = []
        except Exception:
            existing = []
    existing.append(jd_dict)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)

def load_jds_from_json(json_path: str = JDS_JSON_PATH) -> List[Dict[str, Any]]:
    """
    Load all JDs from the JSON store; returns an empty list if none.
    """
    if not os.path.isfile(json_path):
        return []
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            return []
    except Exception:
        return []

def load_job_descriptions(data_dir: str = 'data') -> List[str]:
    """
    Existing helper to list JD files in the data directory (txt, md, docx, pdf).
    """
    if not os.path.isdir(data_dir):
        return []
    items: List[str] = []
    for name in os.listdir(data_dir):
        if name.lower().endswith((".txt", ".md", ".docx", ".pdf")):
            items.append(os.path.join(data_dir, name))
    return items
