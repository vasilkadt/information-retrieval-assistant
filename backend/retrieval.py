"""
Hybrid Retrieval Module
Combines BM25 (keyword-based) and Vector Search (semantic) for better results
"""
import json
import pickle
import re
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path
from typing import List, Dict, Tuple

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

# Paths
BASE_DIR = Path(__file__).parent.parent
CHUNKS_PATH = BASE_DIR / "data/processed/chunks.jsonl"
BM25_PATH = BASE_DIR / "data/index/bm25_index.pkl"
FAISS_PATH = BASE_DIR / "data/index/faiss_index.bin"
EMBEDDINGS_PATH = BASE_DIR / "data/index/embeddings.npy"

# Tokenization
TOKEN_RE = re.compile(r"[A-Za-zА-Яа-я0-9]+", re.UNICODE)

def tokenize(text: str) -> List[str]:
    return [t.lower() for t in TOKEN_RE.findall(text)]


class HybridRetriever:
    """Hybrid retrieval combining BM25 and vector search"""
    
    def __init__(self):
        print("Loading retrieval system...")
        
        # Load chunks
        self.chunks = []
        with open(CHUNKS_PATH, "r", encoding="utf-8") as f:
            for line in f:
                self.chunks.append(json.loads(line))
        
        # Load BM25 index
        with open(BM25_PATH, "rb") as f:
            self.bm25 = pickle.load(f)
        
        # Build inverted index for faster BM25 lookup
        self._build_inverted_index()
        
        # Load FAISS index
        self.faiss_index = faiss.read_index(str(FAISS_PATH))
        
        # Load embedding model
        self.model = SentenceTransformer('paraphrase-multilingual-mpnet-base-v2')
        
        # Cache for query embeddings
        self._embedding_cache: Dict[str, np.ndarray] = {}
        self._cache_max_size = 100
        
        print(f"✓ Loaded {len(self.chunks)} chunks")
    
    def _build_inverted_index(self):
        """Build inverted index mapping terms to document indices for fast BM25"""
        self.inverted_index = defaultdict(list)
        for doc_idx, doc_tf in enumerate(self.bm25["doc_tf"]):
            for term in doc_tf.keys():
                self.inverted_index[term].append(doc_idx)
        print(f"✓ Built inverted index with {len(self.inverted_index)} terms")
    
    def retrieve_bm25(self, query: str, k: int = 10) -> List[Tuple[int, float]]:
        """BM25 retrieval - keyword-based (optimized with inverted index)"""
        q = Counter(tokenize(query))
        
        # Use dict instead of full array - only store docs that have matches
        scores = {}
        
        for term in q:
            if term not in self.bm25["idf"]:
                continue
            idf = self.bm25["idf"][term]
            
            # Only iterate through documents that contain this term (via inverted index)
            for doc_idx in self.inverted_index.get(term, []):
                tf = self.bm25["doc_tf"][doc_idx].get(term, 0)
                denom = tf + self.bm25["k1"] * (
                    1 - self.bm25["b"] + 
                    self.bm25["b"] * self.bm25["doc_lens"][doc_idx] / self.bm25["avgdl"]
                )
                score_contrib = idf * (tf * (self.bm25["k1"] + 1) / denom)
                scores[doc_idx] = scores.get(doc_idx, 0) + score_contrib
        
        # Sort by score and get top-k
        sorted_results = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:k]
        return [(idx, score) for idx, score in sorted_results if score > 0]
    
    def _get_query_embedding(self, query: str) -> np.ndarray:
        """Get query embedding with caching"""
        if query in self._embedding_cache:
            return self._embedding_cache[query]
        
        # Encode query
        query_embedding = self.model.encode([query], convert_to_numpy=True)
        faiss.normalize_L2(query_embedding)
        
        # Cache management - remove oldest if full
        if len(self._embedding_cache) >= self._cache_max_size:
            oldest_key = next(iter(self._embedding_cache))
            del self._embedding_cache[oldest_key]
        
        self._embedding_cache[query] = query_embedding
        return query_embedding
    
    def retrieve_vector(self, query: str, k: int = 10) -> List[Tuple[int, float]]:
        """Vector search - semantic similarity (with embedding caching)"""
        # Get cached or compute query embedding
        query_embedding = self._get_query_embedding(query)
        
        # Search
        scores, indices = self.faiss_index.search(query_embedding, k)
        
        results = [(int(indices[0][i]), float(scores[0][i])) 
                   for i in range(len(indices[0]))]
        return results
    
    def retrieve_hybrid(
        self, 
        query: str, 
        k: int = 5,
        bm25_weight: float = 0.4,
        vector_weight: float = 0.6
    ) -> List[Dict]:
        """
        Hybrid retrieval combining BM25 and vector search
        
        Args:
            query: Search query
            k: Number of results to return
            bm25_weight: Weight for BM25 scores (default 0.4)
            vector_weight: Weight for vector scores (default 0.6)
        
        Returns:
            List of chunks with metadata
        """
        # Get results from both methods
        bm25_results = self.retrieve_bm25(query, k=k*2)
        vector_results = self.retrieve_vector(query, k=k*2)
        
        # Normalize scores to [0, 1]
        def normalize_scores(results):
            if not results:
                return {}
            max_score = max(score for _, score in results)
            if max_score == 0:
                return {idx: 0 for idx, _ in results}
            return {idx: score / max_score for idx, score in results}
        
        bm25_normalized = normalize_scores(bm25_results)
        vector_normalized = normalize_scores(vector_results)
        
        # Combine scores
        all_indices = set(bm25_normalized.keys()) | set(vector_normalized.keys())
        combined_scores = {}
        
        for idx in all_indices:
            bm25_score = bm25_normalized.get(idx, 0)
            vector_score = vector_normalized.get(idx, 0)
            combined_scores[idx] = (
                bm25_weight * bm25_score + 
                vector_weight * vector_score
            )
        
        # Sort by combined score
        sorted_indices = sorted(
            combined_scores.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:k]
        
        # Build results
        results = []
        for idx, score in sorted_indices:
            chunk = self.chunks[idx].copy()
            chunk["score"] = float(score)
            chunk["bm25_score"] = float(bm25_normalized.get(idx, 0))
            chunk["vector_score"] = float(vector_normalized.get(idx, 0))
            results.append(chunk)
        
        return results
    
    def retrieve(self, query: str, k: int = 5, method: str = "hybrid") -> List[Dict]:
        """
        Main retrieval interface
        
        Args:
            query: Search query
            k: Number of results
            method: "hybrid", "bm25", or "vector"
        """
        if method == "bm25":
            bm25_results = self.retrieve_bm25(query, k)
            return [
                {**self.chunks[idx], "score": float(score)} 
                for idx, score in bm25_results
            ]
        elif method == "vector":
            vector_results = self.retrieve_vector(query, k)
            return [
                {**self.chunks[idx], "score": float(score)} 
                for idx, score in vector_results
            ]
        else:  # hybrid
            return self.retrieve_hybrid(query, k)


# Global retriever instance
_retriever = None

def get_retriever() -> HybridRetriever:
    """Get or create the global retriever instance"""
    global _retriever
    if _retriever is None:
        _retriever = HybridRetriever()
    return _retriever


