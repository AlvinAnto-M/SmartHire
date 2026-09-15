"""
Central Configuration Module for SmartHire GenAI.
Handles environment variables, project paths, and model settings.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Base Project Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
JOBS_CSV_PATH = DATA_DIR / "jobs" / "jobs.csv"
CAREER_NOTES_DIR = DATA_DIR / "career_notes"
SAMPLE_RESUMES_DIR = DATA_DIR / "resumes"
VECTORSTORE_DIR = BASE_DIR / "vectorstore"

JOB_FAISS_INDEX_PATH = VECTORSTORE_DIR / "faiss_job_index"
RAG_FAISS_INDEX_PATH = VECTORSTORE_DIR / "faiss_rag_index"

# Load .env file from base directory
ENV_FILE = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_FILE)

# API Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# LLM and Embedding Model Names
# Using standard Google Generative AI model endpoints
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "gemini-2.5-flash")
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "models/text-embedding-004")

# Search and Generation Parameters
DEFAULT_TOP_K_JOBS = 5
MAX_RESUME_CHAR_LIMIT = 20000
MAX_CHAT_INPUT_LIMIT = 1500

def check_api_key() -> bool:
    """Returns True if the GEMINI_API_KEY is configured and non-empty."""
    return bool(GEMINI_API_KEY and GEMINI_API_KEY.strip() and GEMINI_API_KEY != "your_key_here")
