"""
Step 2: Clean extracted page text.
- Remove page numbers, fix hyphen breaks
- Remove remaining corrupted Unicode characters
- Collapse excessive whitespace
- Keep [Формула] and [Фигура] markers from extraction
"""
import json
import re
from pathlib import Path

IN_PATH = Path("../data/processed/pages.jsonl")
OUT_PATH = Path("../data/processed/pages_clean.jsonl")

only_number_line = re.compile(r"^\s*\d+\s*$")
hyphen_break = re.compile(r"(\w+)-\n(\w+)")

# Allowed Unicode ranges: ASCII, Cyrillic, Greek, common math symbols, markers
ALLOWED_RANGES = (
    (0x0000, 0x024F),   # Basic Latin + Latin Extended
    (0x0370, 0x03FF),   # Greek
    (0x0400, 0x04FF),   # Cyrillic
    (0x2000, 0x206F),   # General Punctuation
    (0x2190, 0x21FF),   # Arrows
    (0x2200, 0x22FF),   # Mathematical Operators
    (0x2300, 0x23FF),   # Miscellaneous Technical
    (0x25A0, 0x25FF),   # Geometric Shapes
    (0x2600, 0x26FF),   # Miscellaneous Symbols
)


def is_allowed_char(c: str) -> bool:
    """Check if character is in allowed Unicode ranges"""
    cp = ord(c)
    for start, end in ALLOWED_RANGES:
        if start <= cp <= end:
            return True
    return False


def clean_corrupted(text: str) -> str:
    """Remove corrupted Unicode while preserving markers and clean text"""
    result = []
    i = 0
    while i < len(text):
        c = text[i]
        if c == '[':
            # Preserve [...] markers (formulas, figures)
            end = text.find(']', i)
            if end != -1:
                result.append(text[i:end+1])
                i = end + 1
                continue
        
        if is_allowed_char(c):
            result.append(c)
        else:
            result.append(' ')  # Replace corrupted char with space
        i += 1
    
    return ''.join(result)


def clean_text(t: str) -> str:
    """Full text cleaning pipeline"""
    t = t.replace("\r", "")
    t = hyphen_break.sub(r"\1\2", t)
    
    # Remove corrupted Unicode characters
    t = clean_corrupted(t)
    
    lines = []
    for line in t.split("\n"):
        # Skip standalone page numbers
        if only_number_line.match(line):
            continue
        # Collapse multiple spaces within line
        line = re.sub(r'  +', ' ', line).rstrip()
        if line:
            lines.append(line)
    
    t2 = "\n".join(lines)
    # Collapse 3+ newlines to 2
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
