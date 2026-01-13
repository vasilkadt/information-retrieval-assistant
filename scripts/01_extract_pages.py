import fitz
import json
from pathlib import Path

PDF_PATH = Path("../data/raw/IR_lecture_notes.pdf")
OUT_PATH = Path("../data/processed/pages.jsonl")

OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

doc = fitz.open(PDF_PATH)

with open(OUT_PATH, "w", encoding="utf-8") as f:
    for i in range(doc.page_count):
        page = doc.load_page(i)
        text = page.get_text("text")
        rec = {"page": i + 1, "text_raw": text}
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

print(f"OK -> {OUT_PATH} ({doc.page_count} pages)")