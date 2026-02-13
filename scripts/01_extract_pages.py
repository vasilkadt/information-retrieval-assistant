"""
Step 1: Extract text from PDF with font-aware processing.
- Detects CambriaMath spans → replaces with [Формула] markers
- Detects image blocks → inserts [Фигура] markers
- Preserves clean text from regular fonts
"""
import fitz
import json
import re
from pathlib import Path

PDF_PATH = Path("../data/raw/IR_lecture_notes.pdf")
OUT_PATH = Path("../data/processed/pages.jsonl")
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

# Fonts that produce corrupted output (math symbols rendered as garbled Unicode)
FORMULA_FONTS = {"CambriaMath", "Cambria Math", "Symbol", "MT Extra"}

# Figure caption patterns in Bulgarian and English
FIGURE_PATTERN = re.compile(
    r'(Фиг(?:ура)?\.?\s*\d+[\.\d]*|Figure\s*\d+[\.\d]*)',
    re.IGNORECASE
)


def extract_page_smart(page, page_num: int) -> str:
    """
    Extract text from a page using font-aware block processing.
    - Regular text fonts → keep as-is
    - CambriaMath / formula fonts → replace with [Формула]
    - Image blocks → insert [Фигура] marker
    """
    blocks = page.get_text("dict")["blocks"]
    result_lines = []
    
    for block in blocks:
        # Image block
        if block["type"] == 1:
            # Try to find a caption near this image
            caption = _find_nearby_caption(blocks, block)
            if caption:
                result_lines.append(f"[Фигура: {caption} - вижте стр. {page_num} в PDF]")
            else:
                result_lines.append(f"[Фигура - вижте стр. {page_num} в PDF]")
            continue
        
        # Text block
        if block["type"] != 0:
            continue
        
        for line in block.get("lines", []):
            line_text = ""
            has_formula = False
            has_regular = False
            
            for span in line.get("spans", []):
                font = span.get("font", "")
                text = span.get("text", "")
                
                # Check if this span uses a formula font
                if any(ff in font for ff in FORMULA_FONTS):
                    has_formula = True
                else:
                    has_regular = True
                    line_text += text
            
            # If line had formula parts mixed with text
            if has_formula and has_regular:
                # Keep the text part, mark formula
                line_text = line_text.strip()
                if line_text:
                    result_lines.append(f"{line_text} [формула]")
            elif has_formula and not has_regular:
                # Pure formula line — check for equation number
                eq_match = re.search(r'\((\d+[\.\d]*)\)', line_text)
                if eq_match:
                    result_lines.append(f"[Формула ({eq_match.group(1)}) - вижте стр. {page_num} в PDF]")
                else:
                    result_lines.append(f"[Формула - вижте стр. {page_num} в PDF]")
            elif line_text.strip():
                result_lines.append(line_text)
    
    return "\n".join(result_lines)


def _find_nearby_caption(blocks, image_block) -> str:
    """Find figure caption text near an image block"""
    img_y = image_block["bbox"][3]  # bottom y of image
    
    best_caption = ""
    best_distance = float("inf")
    
    for block in blocks:
        if block["type"] != 0:
            continue
        
        block_y = block["bbox"][1]  # top y of text block
        distance = abs(block_y - img_y)
        
        if distance < 50 and distance < best_distance:
            text = " ".join(
                s["text"] for l in block.get("lines", []) 
                for s in l.get("spans", [])
            ).strip()
            
            match = FIGURE_PATTERN.search(text)
            if match:
                # Return the figure reference + short description
                caption = text[:150]
                best_caption = caption
                best_distance = distance
    
    return best_caption


# Main extraction
doc = fitz.open(PDF_PATH)

with open(OUT_PATH, "w", encoding="utf-8") as f:
    for i in range(doc.page_count):
        page = doc.load_page(i)
        text = extract_page_smart(page, i + 1)
        rec = {"page": i + 1, "text_raw": text}
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

total_pages = doc.page_count
doc.close()
print(f"OK -> {OUT_PATH} ({total_pages} pages)")
