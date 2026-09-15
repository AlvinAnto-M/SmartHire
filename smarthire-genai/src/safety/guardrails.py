"""
Guardrails and Safety Layer for SmartHire GenAI.
Enforces domain boundaries, input length checks, prompt injection defense,
and API key protection before routing queries to LLM pipelines.
"""

import re
from dataclasses import dataclass
from typing import Optional
from ..config import MAX_CHAT_INPUT_LIMIT

@dataclass
class GuardrailResult:
    is_allowed: bool
    category: str
    reason: str
    user_message: str

# Patterns indicating prompt-injection or system prompt extraction attempts
INJECTION_PATTERNS = [
    r"ignore (all )?(previous|prior|above) (instructions|directions|prompts)",
    r"disregard (all )?(previous|prior|above)",
    r"you are now in (developer|dan|god|jailbreak) mode",
    r"system prompt",
    r"reveal (your|the) (system|initial) prompt",
    r"what are your (hidden|exact) instructions",
    r"repeat (everything|the text) above",
    r"show me your api[ _]?key",
    r"print (your )?api[ _]?key",
    r"output (your )?secret",
    r"override security",
]

# Patterns indicating malicious or clearly unsafe instructions
UNSAFE_PATTERNS = [
    r"\b(ddos|sql injection|xss attack|exploit vulnerability|ransomware|malware)\b",
    r"\b(how to hack|bypass security|crack password)\b",
]

# Core domain keyword heuristics for Career Mentor
CAREER_KEYWORDS = [
    "career", "job", "resume", "cv", "interview", "skills", "salary",
    "developer", "engineer", "analyst", "roadmap", "learn", "study",
    "internship", "project", "python", "sql", "machine learning", "ai",
    "degree", "college", "course", "certif", "tech", "coding", "software",
    "fullstack", "frontend", "backend", "data", "cloud", "devops",
    "experience", "placement", "portfolio", "hire", "hiring", "role",
    "switch", "freshers", "btech", "mtech", "bca", "mca", "leetcode",
    "aptitude", "work", "company", "industry", "recruit", "ats"
]

def check_guardrails(user_input: str, context_type: str = "chat") -> GuardrailResult:
    """
    Evaluates input text against safety, length, injection, and off-topic rules.
    
    Args:
        user_input: The raw string provided by the user.
        context_type: 'chat' for Career Mentor or 'resume' for document parsing.
        
    Returns:
        GuardrailResult with pass/fail decision and friendly user-facing message.
    """
    text = user_input.strip()

    # Rule 1: Empty input check
    if not text:
        return GuardrailResult(
            is_allowed=False,
            category="empty_input",
            reason="Input string is empty.",
            user_message="Please enter a question or topic to discuss with the Career Mentor."
        )

    # Rule 2: Length constraint
    if len(text) > MAX_CHAT_INPUT_LIMIT:
        return GuardrailResult(
            is_allowed=False,
            category="length_exceeded",
            reason=f"Input length ({len(text)} chars) exceeds maximum limit of {MAX_CHAT_INPUT_LIMIT}.",
            user_message=f"Your message is quite long ({len(text)} characters). Please shorten your question to under {MAX_CHAT_INPUT_LIMIT} characters for better focus."
        )

    lower_text = text.lower()

    # Rule 3: Prompt Injection / System Prompt Extraction
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, lower_text):
            return GuardrailResult(
                is_allowed=False,
                category="prompt_injection",
                reason=f"Matched prompt injection/extraction signature: '{pattern}'.",
                user_message="Security Notice: For privacy and integrity reasons, this assistant cannot reveal internal system prompts, developer configurations, or credentials. How can I help with your tech career journey?"
            )

    # Rule 4: Unsafe Content
    for pattern in UNSAFE_PATTERNS:
        if re.search(pattern, lower_text):
            return GuardrailResult(
                is_allowed=False,
                category="unsafe_content",
                reason="Matched cyber/security hazard keyword.",
                user_message="I cannot assist with offensive security exploits or malicious activities. I am happy to guide you on defensive cybersecurity careers, ethical hacking certifications, or coding practices!"
            )

    # Rule 5: Domain Boundary Filter (for Chat Mentor only)
    if context_type == "chat":
        # Allow natural greetings
        greetings = ["hi", "hello", "hey", "good morning", "good evening", "namaste", "help", "who are you"]
        if any(lower_text == g or lower_text.startswith(g + " ") or lower_text.startswith(g + "!") for g in greetings):
            return GuardrailResult(
                is_allowed=True,
                category="greeting",
                reason="User greeting permitted.",
                user_message=""
            )

        has_career_keyword = any(kw in lower_text for kw in CAREER_KEYWORDS)
        
        # Off-topic checks (e.g. asking for recipes, movies, politics, sports scores)
        off_topic_indicators = [
            "recipe for", "bake a cake", "cook", "who won the match",
            "movie review", "write a love poem", "president of", "weather today",
            "bitcoin price", "astrology", "horoscope"
        ]
        if any(ot in lower_text for ot in off_topic_indicators) and not has_career_keyword:
            return GuardrailResult(
                is_allowed=False,
                category="off_topic",
                reason="Query is outside the career, resume, and technology learning domain.",
                user_message="This assistant is designed specifically for career, resume, job-search, interview preparation, and technical development questions. Please ask a career or technology-related question!"
            )

    return GuardrailResult(
        is_allowed=True,
        category="allowed",
        reason="Passed all guardrail checks.",
        user_message=""
    )
