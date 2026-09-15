"""
Semantic Job Search Engine using FAISS Vector Store.
Builds and persists job embeddings, creates candidate search queries,
and retrieves top-N matching jobs with similarity scores.
"""

import os
import re
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional

from ..config import JOBS_CSV_PATH, JOB_FAISS_INDEX_PATH
from .embed import get_embedding_model

class JobSearchEngine:
    def __init__(self, csv_path=JOBS_CSV_PATH, index_path=JOB_FAISS_INDEX_PATH):
        self.csv_path = csv_path
        self.index_path = index_path
        self.vector_store = None
        self.jobs_df = None
        self._load_dataset()

    def _load_dataset(self):
        """Loads and cleans the jobs CSV dataset."""
        if not os.path.exists(self.csv_path):
            raise FileNotFoundError(f"Jobs dataset CSV not found at: {self.csv_path}")
        
        df = pd.read_csv(self.csv_path)
        required_cols = ["job_title", "company", "location", "skills", "description"]
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"Missing required column '{col}' in {self.csv_path}")
                
        # Fill missing values
        df = df.fillna("Not Specified")
        df["job_title"] = df["job_title"].str.strip()
        df["company"] = df["company"].str.strip()
        df["location"] = df["location"].str.strip()
        df["skills"] = df["skills"].str.strip()
        df["description"] = df["description"].str.strip()
        
        # Create searchable text representation for each job
        df["search_text"] = df.apply(
            lambda r: f"Job Title: {r['job_title']}. Company: {r['company']}. Location: {r['location']}. Required Skills: {r['skills']}. Job Description: {r['description']}",
            axis=1
        )
        self.jobs_df = df

    def is_index_built(self) -> bool:
        """Checks whether the FAISS job index is saved locally."""
        if not os.path.exists(self.index_path):
            return False
        # LangChain FAISS index creates index.faiss and index.pkl
        return os.path.exists(os.path.join(self.index_path, "index.faiss")) or os.path.exists(os.path.join(self.index_path, "faiss.index"))

    def build_index(self, force_rebuild: bool = False):
        """
        Creates embeddings for all jobs and persists the FAISS index locally.
        Uses LangChain FAISS wrapper.
        """
        from langchain_community.vectorstores import FAISS
        from langchain_core.documents import Document

        if self.is_index_built() and not force_rebuild:
            self.load_index()
            return

        documents = []
        for idx, row in self.jobs_df.iterrows():
            metadata = {
                "job_id": int(idx),
                "job_title": str(row["job_title"]),
                "company": str(row["company"]),
                "location": str(row["location"]),
                "skills": str(row["skills"]),
                "description": str(row["description"]),
            }
            documents.append(Document(page_content=row["search_text"], metadata=metadata))

        embedder = get_embedding_model()
        self.vector_store = FAISS.from_documents(documents, embedder)
        
        os.makedirs(self.index_path, exist_ok=True)
        self.vector_store.save_local(str(self.index_path))

    def load_index(self):
        """Loads the persisted FAISS index from disk."""
        from langchain_community.vectorstores import FAISS

        if not self.is_index_built():
            self.build_index()
            return

        embedder = get_embedding_model()
        self.vector_store = FAISS.load_local(
            str(self.index_path),
            embedder,
            allow_dangerous_deserialization=True
        )

    def create_candidate_profile_text(self, profile: Dict[str, Any]) -> str:
        """
        Converts a parsed candidate profile dictionary into an optimized semantic query string.
        """
        name = profile.get("name", "Candidate")
        target_role = profile.get("target_role", "Software Engineer")
        skills = ", ".join(profile.get("skills", []))
        experience = " | ".join(profile.get("experience", []))
        education = " | ".join(profile.get("education", []))

        return (
            f"Candidate Profile: {name}. "
            f"Target Role: {target_role}. "
            f"Technical Skills: {skills}. "
            f"Experience and Projects: {experience}. "
            f"Education: {education}."
        )

    def search_matching_jobs(self, profile_or_text: Any, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Executes semantic search against FAISS and computes similarity scores.
        
        Args:
            profile_or_text: Parsed profile dict OR raw query string.
            top_k: Number of top matching jobs to retrieve.
            
        Returns:
            List of matching job dictionaries with normalized semantic similarity scores.
        """
        if self.vector_store is None:
            self.load_index()

        if isinstance(profile_or_text, dict):
            query_text = self.create_candidate_profile_text(profile_or_text)
        else:
            query_text = str(profile_or_text)

        # similarity_search_with_score returns (Document, L2 distance or negative inner product)
        docs_with_scores = self.vector_store.similarity_search_with_score(query_text, k=min(top_k, len(self.jobs_df)))

        results = []
        for doc, raw_score in docs_with_scores:
            meta = doc.metadata
            # Normalize L2 distance or inner product into a percentage match (0% - 100%)
            # In FAISS Euclidean L2, lower distance means closer similarity.
            # Typical L2 distances range from 0.0 to 2.0+ for normalized vectors.
            if raw_score < 0:
                # Cosine similarity metric (already between -1 and 1)
                match_percentage = max(0.0, min(100.0, float((raw_score + 1.0) / 2.0 * 100.0)))
            else:
                # L2 distance metric
                # score = 1 / (1 + distance) or exp(-distance/2)
                sim = 1.0 / (1.0 + float(raw_score))
                match_percentage = round(sim * 100.0, 1)

            results.append({
                "job_id": meta.get("job_id", 0),
                "job_title": meta.get("job_title", "Unknown Role"),
                "company": meta.get("company", "Unknown Company"),
                "location": meta.get("location", "Not Specified"),
                "skills": meta.get("skills", ""),
                "description": meta.get("description", ""),
                "match_score": match_percentage,
                "score_label": f"{match_percentage}% Semantic Similarity"
            })

        return results

_global_search_engine = None

def get_job_search_engine() -> JobSearchEngine:
    global _global_search_engine
    if _global_search_engine is None:
        _global_search_engine = JobSearchEngine()
    return _global_search_engine
