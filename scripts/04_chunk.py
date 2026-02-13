"""
Step 4: Split sections into overlapping chunks with quality filtering.
- Chunks that are mostly TOC (dots/dashes) are skipped
- Chunks with very low alphabetic content are skipped
- Minimum chunk length: 80 characters
"""
import json
import hashlib
from pathlib import Path

IN_PATH = Path("../data/processed/pages_with_sections.jsonl")
OUT_PATH = Path("../data/processed/chunks.jsonl")

CHUNK_SIZE = 1200
OVERLAP = 200
MIN_CHUNK_LEN = 80
MIN_ALPHA_RATIO = 0.3  # At least 30% alphabetic characters


def chunk_text(t: str, size: int, overlap: int):
    t = t.strip()
    if len(t) <= size:
        return [t]
    chunks = []
    start = 0
    while start < len(t):
        end = min(len(t), start + size)
        chunks.append(t[start:end].strip())
        if end == len(t):
            break
        start = max(0, end - overlap)
    return [c for c in chunks if len(c) > MIN_CHUNK_LEN]


def is_quality_chunk(text: str) -> bool:
    """Check if chunk has enough useful content"""
    if len(text) < MIN_CHUNK_LEN:
        return False
    
    # Skip TOC-like content (too many dots or dashes)
    dot_count = text.count('.') + text.count('…')
    if dot_count > len(text) * 0.15:
        return False
    
    # Must have minimum alphabetic content
    alpha_count = sum(1 for c in text if c.isalpha())
    if alpha_count / max(len(text), 1) < MIN_ALPHA_RATIO:
        return False
    
    return True


idx = 0
skipped = 0

with open(IN_PATH, "r", encoding="utf-8") as fin, open(OUT_PATH, "w", encoding="utf-8") as fout:
    for line in fin:
        rec = json.loads(line)
        page = rec["page"]
        sec = rec["section_title"]

        for c in chunk_text(rec["text"], CHUNK_SIZE, OVERLAP):
            if not is_quality_chunk(c):
                skipped += 1
                continue
            
            idx += 1
            chunk_id = f"ch_{idx:06d}_" + hashlib.md5(c.encode("utf-8")).hexdigest()[:8]
            fout.write(json.dumps({
                "chunk_id": chunk_id,
                "page": page,
                "section_title": sec,
                "text": c
            }, ensure_ascii=False) + "\n")

print(f"OK -> {OUT_PATH} (chunks: {idx}, skipped: {skipped})")
