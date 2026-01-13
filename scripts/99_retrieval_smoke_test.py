import json, pickle, re
from collections import Counter
import numpy as np
from pathlib import Path

CHUNKS = Path("../data/processed/chunks.jsonl")
BM25 = Path("../data/index/bm25_index.pkl")

TOKEN_RE = re.compile(r"[A-Za-zА-Яа-я0-9]+", re.UNICODE)
def tokenize(text): return [t.lower() for t in TOKEN_RE.findall(text)]

with open(BM25, "rb") as f:
    d = pickle.load(f)

chunks = []
with open(CHUNKS, "r", encoding="utf-8") as f:
    for line in f:
        chunks.append(json.loads(line))

def retrieve(query, k=5):
    q = Counter(tokenize(query))
    scores = np.zeros(len(chunks), dtype=float)
    for term in q:
        if term not in d["idf"]:
            continue
        idf = d["idf"][term]
        for i in range(len(chunks)):
            tf = d["doc_tf"][i].get(term, 0)
            if tf == 0:
                continue
            denom = tf + d["k1"] * (1 - d["b"] + d["b"] * d["doc_lens"][i] / d["avgdl"])
            scores[i] += idf * (tf * (d["k1"] + 1) / denom)
    top = np.argsort(-scores)[:k]
    for idx in top:
        if scores[idx] <= 0:
            continue
        c = chunks[idx]
        print(f"- score={scores[idx]:.2f} | стр.{c['page']} | {c['section_title']}")
        print("  ", c["text"][:200].replace("\n"," "), "...\n")

for q in ["обърнат индекс", "precision recall", "BM25"]:
    print("\nQUERY:", q)
    retrieve(q, 5)
