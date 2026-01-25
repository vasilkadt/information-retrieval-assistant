import json
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer
import faiss

CHUNKS_PATH = Path("../data/processed/chunks.jsonl")
EMBEDDINGS_PATH = Path("../data/index/embeddings.npy")
FAISS_INDEX_PATH = Path("../data/index/faiss_index.bin")
EMBEDDINGS_PATH.parent.mkdir(parents=True, exist_ok=True)

MODEL_NAME = 'paraphrase-multilingual-mpnet-base-v2'
BATCH_SIZE = 32

# Load chunks
chunks = []
with open(CHUNKS_PATH, "r", encoding="utf-8") as f:
    for line in f:
        chunks.append(json.loads(line))

texts = [chunk["text"] for chunk in chunks]

# Load model and generate embeddings
model = SentenceTransformer(MODEL_NAME)
embeddings = model.encode(
    texts,
    show_progress_bar=True,
    batch_size=BATCH_SIZE,
    convert_to_numpy=True,
    normalize_embeddings=False
)

# Save embeddings
np.save(EMBEDDINGS_PATH, embeddings)

# Build FAISS index
dimension = embeddings.shape[1]
index = faiss.IndexFlatIP(dimension)

# Normalize and add to index
embeddings_normalized = embeddings.copy()
faiss.normalize_L2(embeddings_normalized)
index.add(embeddings_normalized)

# Save FAISS index
faiss.write_index(index, str(FAISS_INDEX_PATH))

print(f"OK -> {EMBEDDINGS_PATH} + {FAISS_INDEX_PATH} (chunks: {len(chunks)}, dim: {dimension})")
