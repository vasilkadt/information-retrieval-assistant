import json
import hashlib
from pathlib import Path

IN_PATH = Path("../data/processed/pages_with_sections.jsonl")
OUT_PATH = Path("../data/processed/chunks.jsonl")

CHUNK_SIZE = 1200
OVERLAP = 200

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
    return [c for c in chunks if len(c) > 80]

idx = 0
with open(IN_PATH, "r", encoding="utf-8") as fin, open(OUT_PATH, "w", encoding="utf-8") as fout:
    for line in fin:
        rec = json.loads(line)
        page = rec["page"]
        sec = rec["section_title"]

        for c in chunk_text(rec["text"], CHUNK_SIZE, OVERLAP):
            idx += 1
            chunk_id = f"ch_{idx:06d}_" + hashlib.md5(c.encode("utf-8")).hexdigest()[:8]
            fout.write(json.dumps({
                "chunk_id": chunk_id,
                "page": page,
                "section_title": sec,
                "text": c
            }, ensure_ascii=False) + "\n")

print(f"OK -> {OUT_PATH} (chunks: {idx})")

