import os
import re
import numpy as np
from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextBox, LTChar, LTFigure

def get_timestamp():
    from datetime import datetime
    return datetime.now().isoformat()

def extract_pdf_text(filepath):
    """
    Extract text per page. Returns: {page_num (int, 1-based): "full text"}
    """
    from PyPDF2 import PdfReader
    reader = PdfReader(filepath)
    text_by_page = {}
    for i, page in enumerate(reader.pages):
        try:
            txt = page.extract_text()
        except Exception:
            txt = ""
        text_by_page[i+1] = txt or ""
    return text_by_page

def extract_layout_with_features(pdf_path):
    BULLET_CHARS = {'•', '‣', '∙', '*'}
    def clean_heading_text(text):
        return text.lstrip(''.join(BULLET_CHARS)).strip()
    def overlaps(line_bbox, box_bbox, margin=2):
        lx0, ly0, lx1, ly1 = line_bbox
        bx0, by0, bx1, by1 = box_bbox
        return not (lx1 < bx0 - margin or lx0 > bx1 + margin or ly1 < by0 - margin or ly0 > by1 + margin)
    def extract_title_lines(layout_items):
        page1_items = [item for item in layout_items if item["page"] == 1]
        if not page1_items: return []
        max_size = max(item["font_size"] for item in page1_items)
        top_y_threshold = max(item["y0"] for item in page1_items) * 0.65
        center_min_x = 0.25
        center_max_x = 0.75
        title_lines = []; prev_y0 = None
        for item in sorted(page1_items, key=lambda x: -x["y0"]):
            if abs(item["font_size"] - max_size) > 1.0: continue
            if item["y0"] < top_y_threshold: continue
            x_center_ratio = (item.get("x0", 0) + item.get("x1", 0)) / 2 / 612
            if x_center_ratio < center_min_x or x_center_ratio > center_max_x: continue
            if prev_y0 is not None and abs(prev_y0 - item["y0"]) > 50: break
            title_lines.append(item["text"].strip())
            prev_y0 = item["y0"]
        return title_lines

    layout_items = []
    features = []
    box_regions = {}

    for page_num, layout in enumerate(extract_pages(pdf_path)):
        box_regions[page_num] = []
        page_height = layout.bbox[3]
        for el in layout:
            if isinstance(el, (LTTextBox, LTFigure)):
                box_regions[page_num].append((el.x0, el.y0, el.x1, el.y1))
        prev_y = None
        for element in layout:
            if isinstance(element, LTTextBox):
                for line in element:
                    chars = [char for char in line if isinstance(char, LTChar)]
                    if not chars: continue
                    text = line.get_text().strip()
                    if not text or len(text) < 3: continue
                    if re.fullmatch(r"[\d\s\.\(\)\%\+\-\/]+", text): continue
                    font_size = np.mean([c.size for c in chars])
                    is_bold = any("Bold" in c.fontname or "Black" in c.fontname for c in chars)
                    starts_with_number = text[:3].strip()[0].isdigit() if text else False
                    x0, y0, x1, y1 = line.x0, line.y0, line.x1, line.y1
                    line_bbox = (x0, y0, x1, y1)
                    box_overlap = any(overlaps(line_bbox, box) for box in box_regions[page_num])
                    word_count = len(text.split())
                    proximity_to_top = y0 / page_height
                    if font_size < 8.5 and word_count <= 3 and box_overlap: continue
                    if prev_y is not None and abs(prev_y - y0) < 5: continue
                    prev_y = y0
                    match = re.match(r'^(\d+(\.\d+)*)(\s+|[\)\.])', text)
                    depth = match.group(1).count('.') + 1 if match else 0
                    layout_items.append({
                        "text": text,
                        "font_size": font_size,
                        "is_bold": is_bold,
                        "starts_with_number": starts_with_number,
                        "y0": y0,
                        "x0": x0,
                        "x1": x1,
                        "page": page_num + 1,
                        "word_count": word_count,
                        "depth": depth,
                        "proximity_to_top": proximity_to_top,
                        "box_overlap": int(box_overlap)
                    })
    title_lines = extract_title_lines(layout_items)
    filtered_layout = []
    for item in layout_items:
        if item["text"].strip() in title_lines and item["page"] == 1:
            continue
        filtered_layout.append(item)
        features.append([
            item["font_size"],
            int(item["is_bold"]),
            int(item["starts_with_number"]),
            item["y0"],
            item["depth"],
            item["word_count"],
            item["proximity_to_top"],
            item["box_overlap"]
        ])
    return title_lines, filtered_layout, np.array(features)

def detect_headings(pdf_path):
    """
    Returns (title_lines, headings) where headings is a list of dicts: { "text", "page" }
    Only includes model-predicted headings (ignoring level/tags).
    """
    import joblib
    MODEL_PATH = os.path.join("model-1.pkl")
    clf, le = joblib.load(MODEL_PATH)
    NON_HEADING_LABELS = {"body", "no_heading", "other"}  # Update to match your model
    title_lines, filtered_layout, features = extract_layout_with_features(pdf_path)
    if features.shape[0] == 0:
        return title_lines, []
    preds = clf.predict(features)
    labels = le.inverse_transform(preds)
    headings = []
    for item, label in zip(filtered_layout, labels):
        label_str = str(label).strip().lower()
        if label_str in NON_HEADING_LABELS:
            continue
        text = item.get("text", "").strip()
        if not text or len(text) < 4 or text.endswith('.') or text.startswith('•') or len(text.split()) < 2:
            continue
        headings.append({
            "text": text,
            "page": item["page"]
        })
    return title_lines, headings
