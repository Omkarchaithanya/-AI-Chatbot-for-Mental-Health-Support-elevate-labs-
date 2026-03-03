"""MindEase PRO — RAG Engine using Sentence-Transformers + FAISS"""
from __future__ import annotations

import json
import logging
import os
import pickle
import time
from typing import Optional

import numpy as np

logger = logging.getLogger("mindease.rag")

_EMOTION_CATEGORY_MAP: dict[str, list[str]] = {
    "sadness": ["depression_support", "self_compassion", "behavioral_activation"],
    "fear": ["anxiety_management", "grounding_techniques", "mindfulness"],
    "anger": ["cognitive_restructuring", "grounding_techniques"],
    "joy": ["mindfulness", "self_compassion"],
    "neutral": [],
    "disgust": ["cognitive_restructuring"],
    "surprise": ["grounding_techniques"],
    "love": ["self_compassion"],
}


class RAGEngine:
    """Retrieval-Augmented Generation over CBT knowledge base."""

    def __init__(self, config) -> None:
        self.config = config
        self._encoder = None
        self._index = None
        self._entries: list[dict] = []
        self._entry_texts: list[str] = []
        self.top_k = config.RAG_TOP_K
        self.threshold = config.RAG_SIMILARITY_THRESHOLD
        self._load()

    # ── Loading ──────────────────────────────────────────────────────────────

    def _load(self) -> None:
        logger.info("Initializing RAGEngine...")
        try:
            from sentence_transformers import SentenceTransformer
            self._encoder = SentenceTransformer(self.config.EMBEDDING_MODEL)
        except Exception as exc:
            logger.warning(f"Could not load SentenceTransformer: {exc}. RAG disabled.")
            return

        self._entries = self._load_knowledge_base()
        if not self._entries:
            logger.warning("Knowledge base empty — RAG disabled.")
            return

        self._entry_texts = [self._entry_to_text(e) for e in self._entries]
        self._index = self._build_or_load_index()
        logger.info(f"RAGEngine ready with {len(self._entries)} entries ✓")

    def _load_knowledge_base(self) -> list[dict]:
        kb_path = self.config.KNOWLEDGE_BASE_PATH
        if not os.path.isabs(kb_path):
            base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            kb_path = os.path.join(base, kb_path)
        try:
            with open(kb_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except Exception as exc:
            logger.error(f"Failed to load knowledge base from {kb_path}: {exc}")
            return []

    def _entry_to_text(self, entry: dict) -> str:
        parts = [
            entry.get("title", ""),
            entry.get("content", ""),
            " ".join(entry.get("keywords", [])),
            entry.get("when_to_use", ""),
        ]
        return " ".join(p for p in parts if p)

    def _build_or_load_index(self):
        cache_path = self.config.EMBEDDINGS_CACHE_PATH
        if not os.path.isabs(cache_path):
            base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            cache_path = os.path.join(base, cache_path)

        # Try loading from cache (if < 7 days old)
        try:
            if os.path.exists(cache_path):
                age = time.time() - os.path.getmtime(cache_path)
                if age < 7 * 86400:
                    with open(cache_path, "rb") as f:
                        cache = pickle.load(f)
                    index = self._build_faiss(cache["embeddings"])
                    logger.info("Loaded embeddings from cache ✓")
                    return index
        except Exception as exc:
            logger.warning(f"Cache load failed: {exc}")

        # Encode and cache
        logger.info(f"Encoding {len(self._entry_texts)} knowledge base entries...")
        embeddings = self._encoder.encode(
            self._entry_texts, convert_to_numpy=True, show_progress_bar=False
        )
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        with open(cache_path, "wb") as f:
            pickle.dump({"embeddings": embeddings, "timestamp": time.time()}, f)
        return self._build_faiss(embeddings)

    def _build_faiss(self, embeddings: np.ndarray):
        try:
            import faiss
            dim = embeddings.shape[1]
            index = faiss.IndexFlatIP(dim)
            faiss.normalize_L2(embeddings)
            index.add(embeddings.astype(np.float32))
            return index
        except Exception as exc:
            logger.warning(f"FAISS unavailable ({exc}); using numpy fallback.")
            return {"type": "numpy", "embeddings": embeddings}

    # ── Retrieval ────────────────────────────────────────────────────────────

    def retrieve(self, query: str, emotion: Optional[str] = None) -> list[dict]:
        """Retrieve top-k relevant entries for query."""
        if not self._encoder or not self._entries:
            return []
        try:
            q_emb = self._encoder.encode([query], convert_to_numpy=True)
            q_emb_norm = q_emb.copy()

            # FAISS path
            if isinstance(self._index, dict) and self._index.get("type") == "numpy":
                scores = self._numpy_search(q_emb)
            else:
                import faiss
                faiss.normalize_L2(q_emb_norm)
                distances, indices = self._index.search(
                    q_emb_norm.astype(np.float32), min(self.top_k * 2, len(self._entries))
                )
                scores = list(zip(indices[0].tolist(), distances[0].tolist()))

            # Filter by threshold and get top_k
            boost_cats = _EMOTION_CATEGORY_MAP.get(emotion or "neutral", [])
            results = []
            for idx, score in scores:
                if idx < 0 or idx >= len(self._entries):
                    continue
                entry = self._entries[idx]
                adj_score = float(score)
                if entry.get("category") in boost_cats:
                    adj_score += 0.1
                if adj_score >= self.threshold:
                    results.append({
                        "entry": entry,
                        "score": round(adj_score, 4),
                        "relevance": self._score_to_label(adj_score),
                    })

            results.sort(key=lambda x: x["score"], reverse=True)
            return results[: self.top_k]
        except Exception as exc:
            logger.error(f"RAG retrieve error: {exc}")
            return []

    def _numpy_search(self, q_emb: np.ndarray) -> list[tuple[int, float]]:
        emb = self._index["embeddings"]
        q_norm = q_emb / (np.linalg.norm(q_emb) + 1e-9)
        norms = np.linalg.norm(emb, axis=1, keepdims=True)
        emb_norm = emb / (norms + 1e-9)
        cosines = emb_norm @ q_norm.T
        cosines = cosines.flatten()
        top_indices = np.argsort(cosines)[::-1][: self.top_k * 2]
        return [(int(i), float(cosines[i])) for i in top_indices]

    def _score_to_label(self, score: float) -> str:
        if score >= 0.8:
            return "very_high"
        if score >= 0.65:
            return "high"
        if score >= 0.5:
            return "medium"
        return "low"

    def format_context(self, retrieved: list[dict]) -> str:
        """Format retrieved entries as context string for LLM, max ~400 tokens."""
        if not retrieved:
            return ""
        parts: list[str] = []
        total_len = 0
        for item in retrieved:
            entry = item["entry"]
            section = (
                f"[{entry.get('title', 'Technique')}]\n"
                f"{entry.get('content', '')[:300]}\n"
            )
            exercises = entry.get("exercises", [])
            if exercises:
                section += f"Suggested exercise: {exercises[0]}\n"
            if total_len + len(section) > 1600:  # ~400 tokens rough estimate
                break
            parts.append(section)
            total_len += len(section)
        return "\n".join(parts)

    def is_relevant(self, query: str) -> bool:
        """Check if any entry exceeds the similarity threshold."""
        results = self.retrieve(query)
        return bool(results and results[0]["score"] >= self.threshold)
