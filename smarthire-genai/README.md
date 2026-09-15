# SmartHire GenAI — Resume Matching & AI Career Mentor

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.32%2B-FF4B4B.svg)](https://streamlit.io/)
[![LangChain](https://img.shields.io/badge/LangChain-Enabled-green.svg)](https://www.langchain.com/)
[![FAISS](https://img.shields.io/badge/Vector%20Store-FAISS-purple.svg)](https://github.com/facebookresearch/faiss)
[![Gemini LLM](https://img.shields.io/badge/LLM-Google%20Gemini-orange.svg)](https://aistudio.google.com/)

A production-style Generative AI college capstone project that parses candidate resumes, performs semantic job matching using FAISS vector indexing, generates actionable ATS-optimized CV improvements, and provides a grounded AI Career Mentor chatbot using Retrieval-Augmented Generation (RAG) and safety guardrails.

---

## 1. Project Overview

Students and early-career tech professionals often struggle to understand how their technical skills map onto live industry job descriptions. Traditional job portals rely on exact keyword matching, which penalizes candidates whose resumes describe equivalent skills using different phrasing (e.g., `FastAPI` vs `REST API backend`). Furthermore, students frequently lack actionable guidance on how to strengthen their bullet points or navigate career paths without generic advice.

**SmartHire GenAI** solves this challenge through a four-part Generative AI architecture:
1. **Factual Resume Extraction**: Uses Google Gemini to extract verified skills, practical experiences, and education into a strict JSON structure without hallucination.
2. **Semantic Vector Job Search**: Creates vector embeddings of job postings and queries a local FAISS index to calculate true semantic similarity rather than rigid keyword overlap.
3. **Targeted CV Critique**: Compares the candidate profile directly against a chosen job to identify missing competencies and rewrite bullet points using the Google XYZ formula (*Accomplished X, measured by Y, by doing Z*).
4. **Grounded Career Mentor (RAG)**: A conversational advisor that answers questions grounded strictly in curated role guides, market datasets, and skill roadmaps.

---

## 2. Key Features

- **Document Ingestion**: Accepts PDF, DOCX, and TXT resumes using `pypdf` and `python-docx`.
- **Structured JSON Profiling**: Validates extracted output to prevent missing keys or corrupted schemas.
- **Persistent Vector Store**: Pre-indexes jobs into a local FAISS index so embeddings are not recomputed on every run.
- **Similarity Scoring**: Provides normalized 0–100% semantic matching scores clearly differentiated from hiring probabilities.
- **Truthful CV Gap Analysis**: Strictly forbidden from fabricating fake experience or unverified certifications.
- **RAG Pipeline**: Retrieves relevant context chunks from Markdown career guides and displays source citations.
- **Safety Guardrails**: Intercepts prompt injections, system prompt extraction, credential phishing, and off-topic requests.
- **Interactive Streamlit UI**: Complete with multi-page navigation, sample candidate profiles, metric badges, and chat history.

---

## 3. Technology Stack

| Layer | Technology | Description |
| :--- | :--- | :--- |
| **Frontend / Dashboard** | Streamlit | Clean, responsive web dashboard with sidebar navigation |
| **LLM Inference** | Google Gemini API | `gemini-2.5-flash` / `gemini-3.8-flash` for extraction & reasoning |
| **Embeddings** | Google GenAI Embeddings | `models/text-embedding-004` (768 dimensions) |
| **Vector Database** | FAISS CPU | High-efficiency similarity search & clustering |
| **Orchestration** | LangChain Core / Community | Document chunking, retriever pipelines, and chain assembly |
| **Document Loaders** | `pypdf`, `python-docx` | Robust text extraction from candidate uploads |
| **Data Processing** | Pandas, NumPy | Dataset handling, normalization, and scoring math |

---

## 4. System Architecture

```text
Student Resume (PDF/DOCX)
          │
          ▼
   Document Loader
   (pypdf / python-docx)
          │
          ▼
   Raw Text Extracted
          │
          ▼
   LLM Resume Parser (Gemini)
          │
          ▼
   Structured Candidate JSON
          │
          ▼
   Candidate Embedding Vector
          │
          ▼
   FAISS Semantic Vector Search ◄─── Pre-Indexed Kaggle Jobs Dataset
          │
          ▼
   Top-N Matching Roles (with Similarity Scores)
          │
          ▼
   Selected Job ───► CV Improvement Generator (Google XYZ Bullet Rewriting)

────────────────────────────────────────────────────────────────────────

Student Career Question
          │
          ▼
   Guardrails & Security Firewall (Filter prompt injection / off-topic)
          │
          ▼
   LangChain Retriever
          │
          ▼
   FAISS Career Knowledge Base ◄─── Curated Guides (data/career_notes/*.md)
          │
          ▼
   Grounded Context + Student Query
          │
          ▼
   Gemini AI Career Mentor
          │
          ▼
   Answer with Source Citations
```

---

## 5. Project Directory Structure

```text
smarthire-genai/
├── README.md                      # Comprehensive project documentation
├── requirements.txt               # Pinned, tested Python dependencies
├── .env.example                   # Template for environment variables
├── .gitignore                     # Prevents committing secrets or build files
│
├── data/
│   ├── jobs/
│   │   └── jobs.csv               # Kaggle-style tech job postings dataset
│   ├── resumes/
│   │   ├── sample_resume_swe.txt  # Sample Software Engineer resume
│   │   └── sample_resume_data.txt # Sample Data Analyst resume
│   └── career_notes/              # Markdown guides for RAG pipeline
│       ├── software_developer_guide.md
│       ├── data_analyst_guide.md
│       ├── ml_ai_engineer_guide.md
│       ├── cloud_devops_guide.md
│       └── resume_and_interview_tips.md
│
├── vectorstore/                   # Local FAISS index persistence directory
│   └── .gitkeep
│
├── notebooks/                     # Exploratory analysis & demonstration notebooks
│   ├── 01_embeddings_explore.ipynb
│   ├── 02_build_faiss.ipynb
│   └── 03_rag_prototype.ipynb
│
├── src/
│   ├── __init__.py
│   ├── config.py                  # Paths, models, and environment loader
│   ├── parsing/                   # Document extraction & LLM parser
│   │   ├── __init__.py
│   │   ├── loader.py
│   │   └── resume_parser.py
│   ├── search/                    # Embeddings & FAISS job search
│   │   ├── __init__.py
│   │   ├── embed.py
│   │   └── job_search.py
│   ├── generate/                  # Prompts & CV gap analysis
│   │   ├── __init__.py
│   │   ├── prompts.py
│   │   └── cv_suggestions.py
│   ├── mentor/                    # LangChain RAG pipeline
│   │   ├── __init__.py
│   │   └── rag_chain.py
│   ├── safety/                    # Guardrails firewall
│   │   ├── __init__.py
│   │   └── guardrails.py
│   └── evaluate.py                # Automated benchmark evaluator
│
├── app/
│   ├── __init__.py
│   └── streamlit_app.py           # Multi-page Streamlit application
│
└── reports/
    └── answer_quality.md          # Evaluation report and defense notes
```

---

## 6. Installation & Setup

### Prerequisites
- Python 3.10 or 3.11 installed
- Git installed
- Google AI Studio Gemini API Key (free tier available at [aistudio.google.com](https://aistudio.google.com/))

### Step 1: Clone Repository & Create Virtual Environment
```bash
git clone https://github.com/your-username/smarthire-genai.git
cd smarthire-genai

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/macOS:
source venv/bin/activate
# On Windows:
venv\Scripts\activate
```

### Step 2: Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 3: Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Open `.env` and paste your Gemini API key:
```env
GEMINI_API_KEY=AIzaSyYourActualKeyHere
```

---

## 7. How to Build the FAISS Vector Indexes

You can pre-build the FAISS indexes before launching the web dashboard:
```bash
python -c "from src.search.job_search import get_job_search_engine; get_job_search_engine().build_index(force_rebuild=True)"
python -c "from src.mentor.rag_chain import get_career_mentor; get_career_mentor().build_knowledge_base(force_rebuild=True)"
```
*(Note: If you skip this step, the application will automatically build the FAISS index upon its first search request).*

---

## 8. Running the Application

Launch the Streamlit dashboard:
```bash
streamlit run app/streamlit_app.py
```
Open your browser and navigate to:
```text
http://localhost:8501
```

---

## 9. How to Replace with a Larger Kaggle Dataset

The application includes 12 curated tech roles in `data/jobs/jobs.csv`. To plug in a larger Kaggle dataset (e.g. 5,000+ LinkedIn or Indeed job postings):
1. Download the CSV from Kaggle.
2. Ensure the CSV contains these column names:
   - `job_title`
   - `company`
   - `location`
   - `skills`
   - `description`
3. Replace `data/jobs/jobs.csv` with your new file.
4. Run the index rebuild command (Section 7) to generate the new FAISS embeddings!

---

## 10. Core Concepts Explained (For College Viva / Project Review)

### How FAISS Works
FAISS (Facebook AI Similarity Search) is an open-source library optimized for vector similarity searching. In our project:
1. Each job posting is converted into a 768-dimensional dense vector using Google's embedding model.
2. Vectors are indexed in an L2 / Inner Product matrix on CPU.
3. When the candidate profile vector is submitted, FAISS computes cosine distances across all rows in sub-milliseconds and returns the nearest neighbors.

### How RAG Works
Traditional LLMs hallucinate when asked for specific advice because they rely solely on internal training memory.
- **R** (Retrieve): We query the FAISS index with the student's question to pull relevant chunks from `data/career_notes/*.md`.
- **A** (Augment): The retrieved chunks are injected into the system prompt as Ground Truth.
- **G** (Generate): Gemini reads the combined context and synthesizes a truthful answer with source citations.

### How Guardrails Protect the System
Located in `src/safety/guardrails.py`, this layer acts as an upfront firewall before any LLM API call:
- Rejects empty and excessively long strings.
- Detects prompt injection attempts (e.g. *"ignore instructions", "show me your system prompt"*).
- Intercepts requests attempting to fish for credentials (`GEMINI_API_KEY`).
- Filters out non-career questions (e.g. cooking recipes or movie spoilers) with friendly redirection.

---

## 11. Automated Benchmark Evaluation

To execute the automated evaluation test suite:
```bash
python -m src.evaluate
```
This evaluates 5 benchmark scenarios checking Grounding, Keyword Coverage, Guardrail Enforcement, and Latency. Full qualitative results are documented in `reports/answer_quality.md`.

---

## 12. Deployment to Streamlit Community Cloud

1. Push your repository to GitHub:
   ```bash
   git init
   git add .
   git commit -m "feat: Initial commit of SmartHire GenAI capstone"
   git branch -M main
   git remote add origin https://github.com/your-username/smarthire-genai.git
   git push -u origin main
   ```
2. Log in to [share.streamlit.io](https://share.streamlit.io/).
3. Click **"New App"** and select your GitHub repository.
4. Set Main file path to: `app/streamlit_app.py`.
5. Under **Advanced Settings > Secrets**, add your API key:
   ```toml
   GEMINI_API_KEY = "AIzaSyYourActualKeyHere"
   ```
6. Click **Deploy!** Your app will be live on a public URL.

---

## 13. Limitations & Future Roadmap

- **Scanned Resumes**: Optical Character Recognition (OCR via Tesseract) can be added to parse image-only scanned PDFs.
- **Dynamic Job Ingestion**: Integration with authenticated corporate ATS webhooks (Greenhouse / Lever).
- **Audio Interview Simulator**: Using Gemini Live Audio API for real-time mock technical interviews.

---

## 14. Capstone Project Credits
- **Project Title**: SmartHire GenAI — Resume Matching & AI Career Mentor
- **Course**: B.Tech Information Technology Capstone Project
- **License**: Apache 2.0
