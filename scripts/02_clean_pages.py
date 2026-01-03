import json
import re
from pathlib import Path

IN_PATH = Path("../data/processed/pages.jsonl")
OUT_PATH = Path("../data/processed/pages_clean.jsonl")

only_number_line = re.compile(r"^\s*\d+\s*$")
hyphen_break = re.compile(r"(\w+)-\n(\w+)")

def clean_text(t: str) -> str:
    t = t.replace("\r", "")
    t = hyphen_break.sub(r"\1\2", t)

    lines = []
    for line in t.split("\n"):
        if only_number_line.match(line):
            continue
        lines.append(line.rstrip())

    t2 = "\n".join(lines)
    t2 = re.sub(r"\n{3,}", "\n\n", t2)
    return t2.strip()

with open(IN_PATH, "r", encoding="utf-8") as fin, open(OUT_PATH, "w", encoding="utf-8") as fout:
    for line in fin:
        rec = json.loads(line)
        fout.write(json.dumps({
            "page": rec["page"],
            "text": clean_text(rec.get("text_raw", ""))
        }, ensure_ascii=False) + "\n")

print(f"OK -> {OUT_PATH}")
