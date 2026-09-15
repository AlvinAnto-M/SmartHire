"""
Retrieval-Augmented Generation (RAG) Career Mentor Pipeline.
Combines LangChain, FAISS vector store, career knowledge documents,
job market records, and Gemini LLM for grounded career mentoring.
"""

import os
import glob
from pathlib import Path
from typing import List, Dict, Any, Tuple

from ..config import (
    CAREER_NOTES_DIR,
    JOBS_CSV_PATH,
    RAG_FAISS_INDEX_PATH,
    GEMINI_API_KEY,
    LLM_MODEL_NAME,
    check_api_key
)
from ..search.embed import get_embedding_model
from ..generate.prompts import CAREER_MENTOR_SYSTEM_PROMPT
from ..safety.guardrails import check_guardrails

class CareerMentorRAG:
    def __init__(self, notes_dir=CAREER_NOTES_DIR, index_path=RAG_FAISS_INDEX_PATH):
        self.notes_dir = Path(notes_dir)
        self.index_path = Path(index_path)
        self.vector_store = None
        self.retriever = None

    def is_index_built(self) -> bool:
        """Checks if the RAG FAISS index already exists on disk."""
        faiss_file = self.index_path / "index.faiss"
        pkl_file = self.index_path / "index.pkl"
        return faiss_file.exists() and pkl_file.exists()

    def build_knowledge_base(self, force_rebuild: bool = False):
        """
        Loads career notes and job market data, chunks the text,
        generates embeddings, and stores them in FAISS vector store.
        """
        from langchain_community.vectorstores import FAISS
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        from langchain_core.documents import Document
        import pandas as pd

        if self.is_index_built() and not force_rebuild:
            self.load_knowledge_base()
            return

        documents = []

        # 1. Load Markdown career notes
        md_files = glob.glob(str(self.notes_dir / "*.md"))
        for file_path in md_files:
            fname = Path(file_path).name
            title = fname.replace("_", " ").replace(".md", "").title()
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            documents.append(Document(
                page_content=content,
                metadata={"source": fname, "title": title, "category": "Career Guide"}
            ))

        # 2. Also inject Job Market summaries from jobs.csv
        if os.path.exists(JOBS_CSV_PATH):
            df = pd.read_csv(JOBS_CSV_PATH).fillna("")
            for _, row in df.iterrows():
                summary = (
                    f"Market Job Role: {row['job_title']} at {row['company']} ({row['location']}).\n"
                    f"Key Required Skills: {row['skills']}.\n"
                    f"Role Description: {row['description']}"
                )
                documents.append(Document(
                    page_content=summary,
                    metadata={
                        "source": "jobs.csv",
                        "title": f"Job: {row['job_title']}",
                        "category": "Market Opening"
                    }
                ))

        if not documents:
            documents.append(Document(
                page_content="SmartHire GenAI provides career mentoring for software engineering, data science, and tech roles.",
                metadata={"source": "system_default", "title": "Default Guide", "category": "General"}
            ))

        # Chunk documents
        splitter = RecursiveCharacterTextSplitter(chunk_size=750, chunk_overlap=120)
        chunked_docs = splitter.split_documents(documents)

        # Build and persist FAISS index
        embedder = get_embedding_model()
        self.vector_store = FAISS.from_documents(chunked_docs, embedder)
        
        self.index_path.mkdir(parents=True, exist_ok=True)
        self.vector_store.save_local(str(self.index_path))
        self.retriever = self.vector_store.as_retriever(search_kwargs={"k": 4})

    def load_knowledge_base(self):
        """Loads persisted FAISS knowledge base from disk."""
        from langchain_community.vectorstores import FAISS

        if not self.is_index_built():
            self.build_knowledge_base()
            return

        embedder = get_embedding_model()
        self.vector_store = FAISS.load_local(
            str(self.index_path),
            embedder,
            allow_dangerous_deserialization=True
        )
        self.retriever = self.vector_store.as_retriever(search_kwargs={"k": 4})

    def ask(self, question: str, chat_history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Processes student question through Guardrails, RAG Retriever, and Gemini LLM.
        
        Args:
            question: Student's career query.
            chat_history: Optional list of past messages [{'role': 'user'|'assistant', 'content': '...'}].
            
        Returns:
            Dict with 'answer', 'sources', and 'guardrail' status.
        """
        # Step 1: Guardrails check
        guardrail = check_guardrails(question, context_type="chat")
        if not guardrail.is_allowed:
            return {
                "answer": guardrail.user_message,
                "sources": [],
                "guardrail_triggered": True,
                "category": guardrail.category
            }

        # Step 2: Ensure knowledge base is loaded
        if self.retriever is None:
            self.load_knowledge_base()

        # Step 3: Retrieve relevant knowledge documents
        retrieved_docs = self.retriever.invoke(question)

        # Build formatted context and source citations
        context_snippets = []
        sources = []
        for i, doc in enumerate(retrieved_docs, start=1):
            src_name = doc.metadata.get("title", doc.metadata.get("source", f"Document {i}"))
            snippet = doc.page_content.strip()
            context_snippets.append(f"--- SOURCE {i} [{src_name}] ---\n{snippet}")
            sources.append({
                "title": src_name,
                "source": doc.metadata.get("source", "Knowledge Base"),
                "snippet": snippet[:200] + "..." if len(snippet) > 200 else snippet
            })

        combined_context = "\n\n".join(context_snippets)

        # Format chat history
        formatted_history = ""
        if chat_history:
            recent_turns = chat_history[-6:]
            formatted_history = "\n".join([f"{m.get('role', 'user').title()}: {m.get('content', '')}" for m in recent_turns])

        # Step 4: Generate grounded answer using Gemini or offline fallback
        if not check_api_key():
            answer = self._generate_offline_answer(question, retrieved_docs)
            return {
                "answer": answer,
                "sources": sources,
                "guardrail_triggered": False,
                "category": "allowed"
            }

        try:
            import google.generativeai as genai
            genai.configure(api_key=GEMINI_API_KEY)

            prompt = CAREER_MENTOR_SYSTEM_PROMPT.format(
                context=combined_context,
                chat_history=formatted_history or "None so far.",
                question=question
            )

            model = genai.GenerativeModel(
                model_name=LLM_MODEL_NAME,
                generation_config={"temperature": 0.3}
            )
            response = model.generate_content(prompt)
            return {
                "answer": response.text.strip(),
                "sources": sources,
                "guardrail_triggered": False,
                "category": "allowed"
            }

        except Exception as e:
            return {
                "answer": f"I retrieved relevant career guide records, but experienced a model generation issue ({str(e)}). Here is the relevant knowledge extract:\n\n{combined_context[:600]}...",
                "sources": sources,
                "guardrail_triggered": False,
                "category": "model_error"
            }

    def _generate_offline_answer(self, question: str, retrieved_docs: List[Any]) -> str:
        """Grounded fallback for offline demonstrations and test runs."""
        top_doc = retrieved_docs[0] if retrieved_docs else None
        top_title = top_doc.metadata.get("title", "Career Knowledge Base") if top_doc else "Career Guide"
        
        return (
            f"### AI Career Mentor Guidance (Grounded in {top_title})\n\n"
            f"Based on our career notes and job market intelligence:\n\n"
            f"- **Primary Focus**: Develop foundational competencies, solve practical technical challenges, and build production-grade projects.\n"
            f"- **Curated Knowledge Extract**: {top_doc.page_content[:350] if top_doc else 'Review the role guides in the sidebar.'}...\n\n"
            f"*(Note: For dynamic conversational synthesis, ensure your `GEMINI_API_KEY` is active in `.env`)*"
        )

_global_mentor = None

def get_career_mentor() -> CareerMentorRAG:
    global _global_mentor
    if _global_mentor is None:
        _global_mentor = CareerMentorRAG()
    return _global_mentor
