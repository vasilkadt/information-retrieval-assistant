import json
import re
from pathlib import Path

IN_PATH = Path("../data/processed/pages_clean.jsonl")
OUT_PATH = Path("../data/processed/pages_with_sections.jsonl")

sec_re = re.compile(r"^\s*(\d+(?:\.\d+)*)\s+([A-Za-zА-Яа-я].{3,120})\s*$")

current_section = "Unknown"

with open(IN_PATH, "r", encoding="utf-8") as fin, open(OUT_PATH, "w", encoding="utf-8") as fout:
    for line in fin:
        rec = json.loads(line)
        text = rec["text"]

        head = "\n".join(text.split("\n")[:40])
        for l in head.split("\n"):
            m = sec_re.match(l)
            if m:
                current_section = f"{m.group(1)} {m.group(2).strip()}"
                break

        rec["section_title"] = current_section
        fout.write(json.dumps(rec, ensure_ascii=False) + "\n")

print(f"OK -> {OUT_PATH}")
