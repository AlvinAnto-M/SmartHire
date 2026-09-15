"""Generation and Prompt Library Module."""
from .prompts import (
    RESUME_PARSER_SYSTEM_PROMPT,
    CV_IMPROVEMENT_SYSTEM_PROMPT,
    CAREER_MENTOR_SYSTEM_PROMPT,
    GUARDRAIL_CLASSIFICATION_PROMPT,
)
from .cv_suggestions import generate_cv_improvements

__all__ = [
    "RESUME_PARSER_SYSTEM_PROMPT",
    "CV_IMPROVEMENT_SYSTEM_PROMPT",
    "CAREER_MENTOR_SYSTEM_PROMPT",
    "GUARDRAIL_CLASSIFICATION_PROMPT",
    "generate_cv_improvements",
]
