"""
Resume Parser Module using Gemini LLM.
Extracts structured JSON profiles from raw resume text with strict validation.
"""

import json
import re
from typing import Dict, Any, List
import google.generativeai as genai

from ..config import GEMINI_API_KEY, LLM_MODEL_NAME, check_api_key
from ..generate.prompts import RESUME_PARSER_SYSTEM_PROMPT

def clean_json_response(raw_response: str) -> str:
    """Removes markdown code fences and cleans response for JSON parsing."""
    text = raw_response.strip()
    # Strip markdown fences if present
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()

def validate_resume_json(data: Any) -> Dict[str, Any]:
    """
    Validates and normalizes parsed resume JSON structure against the required schema:
    {
      "name": str,
      "skills": list,
      "experience": list,
      "education": list,
      "target_role": str
    }
    """
    if not isinstance(data, dict):
        raise ValueError("Parsed resume data must be a JSON dictionary.")

    validated = {
        "name": str(data.get("name", "")).strip() or "Candidate",
        "skills": [],
        "experience": [],
        "education": [],
        "target_role": str(data.get("target_role", "")).strip() or "Software Engineer",
    }

    # Normalize skills
    raw_skills = data.get("skills", [])
    if isinstance(raw_skills, list):
        validated["skills"] = [str(s).strip() for s in raw_skills if str(s).strip()]
    elif isinstance(raw_skills, str):
        validated["skills"] = [s.strip() for s in raw_skills.split(",") if s.strip()]

    # Normalize experience
    raw_exp = data.get("experience", [])
    if isinstance(raw_exp, list):
        for item in raw_exp:
            if isinstance(item, dict):
                role = item.get("role") or item.get("title") or "Role"
                company = item.get("company") or item.get("organization") or ""
                desc = item.get("description") or item.get("details") or ""
                validated["experience"].append(f"{role} at {company}: {desc}".strip(" :"))
            else:
                validated["experience"].append(str(item).strip())
    elif isinstance(raw_exp, str) and raw_exp.strip():
        validated["experience"] = [raw_exp.strip()]

    # Normalize education
    raw_edu = data.get("education", [])
    if isinstance(raw_edu, list):
        for item in raw_edu:
            if isinstance(item, dict):
                degree = item.get("degree") or "Degree"
                inst = item.get("institution") or item.get("college") or ""
                year = item.get("year") or ""
                validated["education"].append(f"{degree}, {inst} ({year})".strip(" ,()"))
            else:
                validated["education"].append(str(item).strip())
    elif isinstance(raw_edu, str) and raw_edu.strip():
        validated["education"] = [raw_edu.strip()]

    return validated

def parse_resume_text(resume_text: str) -> Dict[str, Any]:
    """
    Sends extracted resume text to Gemini and extracts candidate profile as validated JSON.
    
    Args:
        resume_text: Plain text extracted from candidate resume.
        
    Returns:
        Dictionary conforming to the validated resume schema.
    """
    if not resume_text or not resume_text.strip():
        raise ValueError("Resume text is empty. Please upload a valid document.")

    if not check_api_key():
        # Heuristic fallback for offline / mock testing if API key is not yet configured
        return fallback_heuristic_parser(resume_text)

    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(
            model_name=LLM_MODEL_NAME,
            system_instruction=RESUME_PARSER_SYSTEM_PROMPT,
            generation_config={"temperature": 0.1, "response_mime_type": "application/json"}
        )

        user_content = f"RESUME CONTENT TO PARSE:\n\n{resume_text}"
        response = model.generate_content(user_content)
        cleaned_json = clean_json_response(response.text)
        parsed_data = json.loads(cleaned_json)
        return validate_resume_json(parsed_data)

    except Exception as e:
        # If API or parsing fails, attempt regex/heuristic fallback with an informative message
        fallback = fallback_heuristic_parser(resume_text)
        fallback["_warning"] = f"LLM Parsing encountered an issue ({str(e)}). Extracted using rule-based fallback."
        return fallback

def fallback_heuristic_parser(resume_text: str) -> Dict[str, Any]:
    """
    Rule-based extraction fallback for testing or offline environments.
    Extracts name, skills, and experience sections using keyword patterns.
    """
    lines = [line.strip() for line in resume_text.splitlines() if line.strip()]
    candidate_name = lines[0] if lines else "Candidate"
    
    # Common tech skills keywords
    known_tech = [
        "Python", "Java", "C++", "JavaScript", "TypeScript", "React", "Node.js",
        "FastAPI", "Django", "Flask", "SQL", "PostgreSQL", "MySQL", "MongoDB",
        "Docker", "Kubernetes", "AWS", "Git", "Pandas", "NumPy", "Scikit-learn",
        "PyTorch", "TensorFlow", "Tableau", "Power BI", "HTML5", "CSS3", "Linux"
    ]
    detected_skills = [skill for skill in known_tech if re.search(rf"\b{re.escape(skill)}\b", resume_text, re.IGNORECASE)]

    # Infer target role
    target_role = "Software Developer"
    lower_text = resume_text.lower()
    if "data scientist" in lower_text:
        target_role = "Data Scientist"
    elif "data analyst" in lower_text or "tableau" in lower_text or "power bi" in lower_text:
        target_role = "Data Analyst"
    elif "machine learning" in lower_text or "pytorch" in lower_text:
        target_role = "Machine Learning Engineer"
    elif "frontend" in lower_text or "react" in lower_text:
        target_role = "Frontend Developer"
    elif "backend" in lower_text or "fastapi" in lower_text:
        target_role = "Backend Developer"
    elif "devops" in lower_text or "cloud" in lower_text:
        target_role = "Cloud Engineer"

    # Extract sample experience lines
    exp_lines = [l for l in lines if any(k in l.lower() for k in ["intern", "engineer", "developer", "built", "developed", "led"])]
    edu_lines = [l for l in lines if any(k in l.lower() for k in ["bachelor", "master", "degree", "b.tech", "university", "institute"])]

    return validate_resume_json({
        "name": candidate_name[:50],
        "skills": detected_skills or ["Python", "Git", "Problem Solving"],
        "experience": exp_lines[:4] or ["Practical engineering projects detailed in resume"],
        "education": edu_lines[:2] or ["Bachelor of Technology in Information Technology"],
        "target_role": target_role
    })
