import json
import math
import pickle
import re
from collections import Counter
from pathlib import Path

CHUNKS_PATH = Path("../data/processed/chunks.jsonl")
OUT_PATH = Path("../data/index/bm25_index.pkl")
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

TOKEN_RE = re.compile(r"[A-Za-zА-Яа-я0-9]+", re.UNICODE)

def tokenize(text: str):
    return [t.lower() for t in TOKEN_RE.findall(text)]

doc_tf = []
doc_lens = []
df = Counter()
N = 0

with open(CHUNKS_PATH, "r", encoding="utf-8") as f:
    for line in f:
        rec = json.loads(line)
        tokens = tokenize(rec["text"])
        tf = Counter(tokens)
        doc_tf.append(dict(tf))
        doc_lens.append(len(tokens))
        for term in tf.keys():
            df[term] += 1
        N += 1

avgdl = sum(doc_lens) / max(1, N)

idf = {}
for term, freq in df.items():
    idf[term] = math.log(1 + (N - freq + 0.5) / (freq + 0.5))

bm25 = {
    "k1": 1.5,
    "b": 0.75,
    "avgdl": avgdl,
    "idf": idf,
    "doc_lens": doc_lens,
    "doc_tf": doc_tf
}

with open(OUT_PATH, "wb") as f:
    pickle.dump(bm25, f)

print(f"OK -> {OUT_PATH} (docs: {N})")
