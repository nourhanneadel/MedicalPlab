import os
import re
import json
import logging
import numpy as np
from typing import List, Dict, Any, Optional

logger = logging.getLogger("MedicalRAGEngine")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(levelname)s] %(asctime)s - %(name)s: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

class MedicalRAGEngine:
    """
    Production-grade Hybrid Retrieval Engine for MedPlab.
    Combines:
      1. BM25 Lexical Retrieval (via rank_bm25) over canonical structure-aware chunks
      2. Dense Vector Retrieval (via sentence-transformers with BAAI/bge-small-en-v1.5)
      3. Reciprocal Rank Fusion (RRF with k=60) for robust rank aggregation

    Guarantees 100% backwards-compatibility with existing interface expected by:
      - Scripts/agents.py (SocraticTutorAgent)
      - main.py (FastAPI /rag/search endpoint)
    """

    def __init__(
        self,
        chunks_path: Optional[str] = None,
        model_name: str = "BAAI/bge-small-en-v1.5",
        rrf_k: int = 60
    ):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.base_dir = base_dir
        if chunks_path is None:
            chunks_path = os.path.join(base_dir, "Data", "canonical_chunks.json")
        self.chunks_path = chunks_path
        self.embeddings_path = os.path.join(base_dir, "Data", "chunk_embeddings.npy")
        self.model_name = model_name
        self.rrf_k = rrf_k

        self.chunks: List[Dict[str, Any]] = []
        self.bm25 = None
        self.bm25_corpus: List[List[str]] = []
        self.dense_model = None
        self.chunk_embeddings: Optional[np.ndarray] = None

        self._load_chunks()
        self._init_bm25()
        self._init_dense()

    def _tokenize(self, text: str) -> List[str]:
        """Simple, deterministic word tokenization for BM25."""
        return re.findall(r"\w+", text.lower())

    def _load_chunks(self):
        """Loads canonical chunks from Data/canonical_chunks.json, rebuilding if missing."""
        if not os.path.exists(self.chunks_path):
            logger.warning(f"Canonical chunks file not found at {self.chunks_path}. Triggering build...")
            from Scripts.build_canonical_chunks import build_canonical_chunks
            self.chunks = build_canonical_chunks(output_path=self.chunks_path)
        else:
            with open(self.chunks_path, "r", encoding="utf-8") as f:
                self.chunks = json.load(f)
        logger.info(f"Loaded {len(self.chunks)} canonical chunks.")

    def _init_bm25(self):
        """Initializes BM25 index over chunk text."""
        try:
            from rank_bm25 import BM25Okapi
            self.bm25_corpus = [
                self._tokenize(f"{c.get('title', '')} {c.get('heading', '')} {c.get('text', '')}")
                for c in self.chunks
            ]
            self.bm25 = BM25Okapi(self.bm25_corpus)
            logger.info("BM25 index initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize BM25: {e}. Fallback to lexical search will be used if needed.")
            self.bm25 = None

    def _init_dense(self):
        """Initializes dense embedding model and loads or computes chunk embeddings."""
        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading dense embedding model '{self.model_name}'...")
            self.dense_model = SentenceTransformer(self.model_name)

            # Check if cached embeddings exist and match chunk count
            if os.path.exists(self.embeddings_path):
                cached = np.load(self.embeddings_path)
                if len(cached) == len(self.chunks):
                    self.chunk_embeddings = cached
                    logger.info(f"Loaded {len(self.chunk_embeddings)} precomputed embeddings from cache.")
                    return

            # Compute and cache embeddings
            logger.info("Computing dense embeddings for canonical chunks...")
            texts = [
                f"{c.get('title', '')} - {c.get('heading', '')}: {c.get('text', '')}"
                for c in self.chunks
            ]
            self.chunk_embeddings = self.dense_model.encode(
                texts,
                show_progress_bar=False,
                convert_to_numpy=True,
                normalize_embeddings=True
            )
            np.save(self.embeddings_path, self.chunk_embeddings)
            logger.info(f"Successfully computed and cached {len(self.chunk_embeddings)} dense embeddings.")
        except Exception as e:
            logger.error(f"Failed to initialize dense embeddings: {e}. Engine will operate in BM25-only degraded mode.")
            self.dense_model = None
            self.chunk_embeddings = None

    def search_bm25(self, query: str, top_n: int = 10) -> List[tuple]:
        """Returns list of (chunk_index, bm25_score) sorted by relevance."""
        if not self.bm25 or not self.chunks:
            return []
        tokenized_query = self._tokenize(query)
        if not tokenized_query:
            return []
        scores = self.bm25.get_scores(tokenized_query)
        ranked_indices = np.argsort(scores)[::-1]
        return [(idx, float(scores[idx])) for idx in ranked_indices[:top_n] if scores[idx] > 0]

    def search_dense(self, query: str, top_n: int = 10) -> List[tuple]:
        """Returns list of (chunk_index, cosine_similarity) sorted by relevance."""
        if self.dense_model is None or self.chunk_embeddings is None or not self.chunks:
            return []
        try:
            query_emb = self.dense_model.encode([query], normalize_embeddings=True, convert_to_numpy=True)[0]
            # Cosine similarity (since embeddings are L2 normalized, dot product = cosine similarity)
            similarities = np.dot(self.chunk_embeddings, query_emb)
            ranked_indices = np.argsort(similarities)[::-1]
            return [(idx, float(similarities[idx])) for idx in ranked_indices[:top_n]]
        except Exception as e:
            logger.error(f"Dense search encountered error: {e}")
            return []

    def _lexical_fallback_search(self, query: str, top_k: int = 2) -> List[Dict[str, Any]]:
        """Fallback word-overlap search in case both BM25 and dense are unavailable."""
        query_words = set(re.findall(r"\w+", query.lower()))
        stop_words = {"a", "an", "the", "and", "or", "in", "on", "at", "of", "to", "for", "with", "is", "was", "are"}
        keywords = [w for w in query_words if len(w) > 2 and w not in stop_words]

        scored = []
        for c in self.chunks:
            text = (c.get("title", "") + " " + c.get("heading", "") + " " + c.get("text", "")).lower()
            score = sum(1.0 for kw in keywords if kw in text)
            if score > 0:
                scored.append((score, c))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [
            {
                "title": c.get("title", ""),
                "section": c.get("heading", c.get("section", "")),
                "content": c.get("text", ""),
                "citation": f"{c.get('title', '')} — {c.get('heading', c.get('section', ''))}",
                "score": round(s, 2),
                "chunk_id": c.get("chunk_id", ""),
                "document_id": c.get("document_id", "")
            }
            for s, c in scored[:top_k]
        ]

    def search(self, query: str, top_k: int = 2) -> List[Dict[str, Any]]:
        """
        Primary search method matching the exact interface required by:
          - Scripts/agents.py
          - main.py

        Returns list of dicts with keys:
          'title', 'section', 'content', 'citation', 'score' (and bonus chunk_id, document_id)
        """
        if not self.chunks:
            return []

        # 1. Retrieve ranked lists from BM25 and Dense
        bm25_results = self.search_bm25(query, top_n=max(10, top_k * 2))
        dense_results = self.search_dense(query, top_n=max(10, top_k * 2))

        # Handle complete failure of both retrieval tiers
        if not bm25_results and not dense_results:
            logger.warning(f"Both BM25 and Dense returned 0 matches for query '{query}'. Using lexical fallback.")
            return self._lexical_fallback_search(query, top_k=top_k)

        # 2. Reciprocal Rank Fusion (RRF)
        rrf_scores: Dict[int, float] = {}

        # Accumulate BM25 reciprocal ranks
        for rank, (idx, _) in enumerate(bm25_results):
            rrf_scores[idx] = rrf_scores.get(idx, 0.0) + (1.0 / (self.rrf_k + (rank + 1)))

        # Accumulate Dense reciprocal ranks
        for rank, (idx, _) in enumerate(dense_results):
            rrf_scores[idx] = rrf_scores.get(idx, 0.0) + (1.0 / (self.rrf_k + (rank + 1)))

        # Sort chunk indices by fused RRF score descending
        sorted_indices = sorted(rrf_scores.keys(), key=lambda i: rrf_scores[i], reverse=True)

        # 3. Format outputs matching the exact legacy contract
        results = []
        for idx in sorted_indices[:top_k]:
            chunk = self.chunks[idx]
            title = chunk.get("title", "")
            heading = chunk.get("heading", chunk.get("section", "General Guidance"))
            content = chunk.get("text", "")
            citation = f"{title} — {heading}"
            score = round(rrf_scores[idx], 4)

            results.append({
                "title": title,
                "section": heading,
                "content": content,
                "citation": citation,
                "score": score,
                # Additional fields for audit and evaluation
                "chunk_id": chunk.get("chunk_id", ""),
                "document_id": chunk.get("document_id", ""),
                "source_locator": chunk.get("source_locator", "")
            })

        return results

# Singleton instance preserved at module level
rag_engine = MedicalRAGEngine()

if __name__ == "__main__":
    print("Testing MedicalRAGEngine Hybrid Retrieval...")
    test_query = "STEMI chest pain emergency reperfusion primary PCI"
    hits = rag_engine.search(test_query, top_k=2)
    print(f"Query: '{test_query}'")
    print(f"Retrieved {len(hits)} hits:")
    for h in hits:
        print(f" -> [{h['score']}] {h['citation']} (chunk_id: {h.get('chunk_id')})")
