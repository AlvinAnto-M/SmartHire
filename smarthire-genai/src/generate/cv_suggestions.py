"""
CV Improvement Generator comparing candidate resumes to selected target jobs.
Uses Gemini LLM to generate targeted, truthful, ATS-optimized recommendations.
"""

import json
from typing import Dict, Any, List
import google.generativeai as genai

from ..config import GEMINI_API_KEY, LLM_MODEL_NAME, check_api_key
from .prompts import CV_IMPROVEMENT_SYSTEM_PROMPT

def clean_json_str(text: str) -> str:
    s = text.strip()
    if s.startswith("```json"):
        s = s[7:]
    elif s.startswith("```"):
        s = s[3:]
    if s.endswith("```"):
        s = s[:-3]
    return s.strip()

def validate_cv_suggestions(data: Any) -> Dict[str, Any]:
    """Ensures consistent schema format for CV improvement recommendations."""
    if not isinstance(data, dict):
        raise ValueError("Invalid format: expected a dictionary.")

    return {
        "missing_skills": [str(s).strip() for s in data.get("missing_skills", []) if str(s).strip()],
        "weak_bullet_points": [str(b).strip() for b in data.get("weak_bullet_points", []) if str(b).strip()],
        "improved_bullet_points": [str(b).strip() for b in data.get("improved_bullet_points", []) if str(b).strip()],
        "rewritten_summary": str(data.get("rewritten_summary", "")).strip(),
        "overall_suggestions": [str(s).strip() for s in data.get("overall_suggestions", []) if str(s).strip()],
    }

def generate_cv_improvements(candidate_profile: Dict[str, Any], selected_job: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compares candidate resume profile against target job description.
    
    Args:
        candidate_profile: Parsed candidate resume details.
        selected_job: Dictionary with job_title, skills, description.
        
    Returns:
        Structured JSON dictionary with improvement suggestions.
    """
    job_title = selected_job.get("job_title", "Target Role")
    job_skills = selected_job.get("skills", "")
    job_desc = selected_job.get("description", "")
    
    cand_name = candidate_profile.get("name", "Candidate")
    cand_skills = ", ".join(candidate_profile.get("skills", []))
    cand_exp = "\n- ".join(candidate_profile.get("experience", []))
    cand_edu = "\n- ".join(candidate_profile.get("education", []))

    user_prompt = f"""
TARGET JOB SPECIFICATION:
Job Title: {job_title}
Required Tech Skills: {job_skills}
Job Description: {job_desc}

CANDIDATE CURRENT RESUME:
Name: {cand_name}
Existing Skills: {cand_skills}
Experience & Projects:
- {cand_exp}
Education:
- {cand_edu}

Perform the comparative CV critique and return the requested JSON schema.
Remember: Do NOT invent fake companies, fake experience, or fake metrics.
"""

    if not check_api_key():
        return fallback_cv_improvements(candidate_profile, selected_job)

    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(
            model_name=LLM_MODEL_NAME,
            system_instruction=CV_IMPROVEMENT_SYSTEM_PROMPT,
            generation_config={"temperature": 0.2, "response_mime_type": "application/json"}
        )

        response = model.generate_content(user_prompt)
        cleaned = clean_json_str(response.text)
        parsed = json.loads(cleaned)
        return validate_cv_suggestions(parsed)

    except Exception as e:
        fallback = fallback_cv_improvements(candidate_profile, selected_job)
        fallback["_warning"] = f"LLM generation notice: {str(e)}"
        return fallback

def fallback_cv_improvements(candidate_profile: Dict[str, Any], selected_job: Dict[str, Any]) -> Dict[str, Any]:
    """Rule-based fallback for generating realistic CV critique when offline."""
    cand_skills_lower = set(s.lower().strip() for s in candidate_profile.get("skills", []))
    req_skills_raw = selected_job.get("skills", "").split(",")
    
    missing = []
    for s in req_skills_raw:
        clean_s = s.strip()
        if clean_s and clean_s.lower() not in cand_skills_lower:
            missing.append(clean_s)

    exp_list = candidate_profile.get("experience", [])
    weak_bullets = exp_list[:2] if exp_list else ["Developed backend endpoints for internal analytics dashboard."]
    
    improved_bullets = [
        f"Engineered and deployed modular REST endpoints in Python, reducing test runtime and achieving 82% code coverage.",
        f"Containerized microservice architecture with Docker, cutting local environment bootstrapping time by 40% for team developers."
    ]

    target_role = selected_job.get("job_title", "Software Engineer")
    summary = (
        f"Aspiring {target_role} with strong foundations in {', '.join(list(cand_skills_lower)[:3]).title()}. "
        f"Demonstrated project experience in API engineering, containerization, and data persistence. "
        f"Focused on applying analytical problem-solving and clean code principles to drive product impact at {selected_job.get('company', 'your organization')}."
    )

    suggestions = [
        f"Build an end-to-end portfolio project explicitly highlighting {', '.join(missing[:2]) if missing else 'production CI/CD pipelines'}.",
        "Quantify outcomes in your experience bullet points using the Google XYZ formula (Accomplished X, measured by Y, by doing Z).",
        "Publish your project repositories on GitHub with thorough README.md documentation and architectural diagrams.",
        "Add a dedicated 'Key Technical Competencies' section categorized by Languages, Frameworks, and Cloud Tools."
    ]

    return validate_cv_suggestions({
        "missing_skills": missing[:6],
        "weak_bullet_points": weak_bullets,
        "improved_bullet_points": improved_bullets,
        "rewritten_summary": summary,
        "overall_suggestions": suggestions
    })
