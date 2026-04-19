import os
import json
import re
from src.model_loader import load_heading_extractor
from src.utils import extract_layout_with_features, extract_pdf_text, get_timestamp
from src.relevance import load_sentence_transformer, rank_by_relevance
from src.summarizer import summarize_section

# ==============================
# 🔥 LOAD MODELS ONLY ONCE
# ==============================
clf, le = load_heading_extractor("model-1.pkl")
st_model = load_sentence_transformer()

NON_HEADING_LABELS = {"body", "no_heading", "other"}


# ==============================
# 🧠 HEADING FILTER
# ==============================
def is_heading_like(text):
    if not text or len(text) < 6:
        return False
    if text.endswith('.') or text.endswith(',') or text.endswith(':'):
        return False
    if text.startswith(('•', '-', '·')):
        return False
    if len(text.split()) < 2:
        return False
    if text == text.lower():
        return False
    if not (text.istitle() or text.isupper()):
        if not re.match(r'\d+[\).]?\s*[A-Z][a-zA-Z]', text):
            return False
    if re.match(r'[a-z]', text[0]):
        return False
    if re.search(r'\s(and|or|but|because|so|to|with|for|from|of|by|in|on|at)$', text, re.IGNORECASE):
        return False
    return True


# ==============================
# 🚀 MAIN PIPELINE FUNCTION
# ==============================
def run_pipeline(input_data):
    docs = input_data["documents"]
    persona = input_data["persona"]["role"]
    job_to_do = input_data["job_to_be_done"]["task"]

    doc_filenames = [d["filename"] for d in docs]

    all_sections = []
    filtered_layout_by_doc = {}
    section_indices_by_doc = {}

    for fname in doc_filenames:
        pdf_path = os.path.join("data/input_documents", fname)

        title_lines, filtered_layout, feature_array = extract_layout_with_features(pdf_path)
        filtered_layout_by_doc[fname] = filtered_layout

        if feature_array.shape[0] == 0:
            continue

        preds = clf.predict(feature_array)
        labels = le.inverse_transform(preds)

        heading_idxs = [
            i for i, label in enumerate(labels)
            if str(label).strip().lower() not in NON_HEADING_LABELS
        ]

        section_indices_by_doc[fname] = heading_idxs

        for idx in heading_idxs:
            text = filtered_layout[idx]['text'].strip()

            if is_heading_like(text):
                all_sections.append({
                    'document': fname,
                    'section_title': text,
                    'page_number': filtered_layout[idx]['page'],
                    'feature_idx': idx
                })

    # ==============================
    # 🧠 SEMANTIC RANKING
    # ==============================
    ranked_sections = rank_by_relevance(all_sections, job_to_do, st_model)

    for i, sec in enumerate(ranked_sections):
        sec['importance_rank'] = i + 1

    extracted_sections = [{
        'document': s['document'],
        'section_title': s['section_title'],
        'importance_rank': s['importance_rank'],
        'page_number': s['page_number']
    } for s in ranked_sections[:5]]

    # ==============================
    # ✍️ SUBSECTION SUMMARIES
    # ==============================
    subsection_analysis = []

    for s in ranked_sections[:5]:
        doc = s['document']
        idx = s['feature_idx']

        heading_idxs = section_indices_by_doc[doc]
        filtered_layout = filtered_layout_by_doc[doc]

        next_idxs = [i for i in heading_idxs if i > idx]
        next_idx = next_idxs[0] if next_idxs else len(filtered_layout)

        section_text = '\n'.join(
            filtered_layout[i]['text'] for i in range(idx + 1, next_idx)
        )

        if not section_text.strip():
            allpages = extract_pdf_text(os.path.join("data/input_documents", doc))
            section_text = allpages.get(filtered_layout[idx]['page'], "")

        refined = summarize_section(
            section_text,
            job_to_do,
            st_model,
            max_sentences=2
        )

        subsection_analysis.append({
            'document': doc,
            'refined_text': refined,
            'page_number': s['page_number']
        })

    # ==============================
    # 📦 FINAL OUTPUT
    # ==============================
    metadata = {
        'input_documents': doc_filenames,
        'persona': persona,
        'job_to_be_done': job_to_do,
        'processing_timestamp': get_timestamp()
    }

    output = {
        'metadata': metadata,
        'extracted_sections': extracted_sections,
        'subsection_analysis': subsection_analysis
    }

    # Save (optional but good)
    os.makedirs("outputs", exist_ok=True)
    with open("outputs/challenge1b_output.json", "w", encoding='utf-8') as f:
        json.dump(output, f, indent=4, ensure_ascii=False)

    return output


# ==============================
# 🧪 RUN STANDALONE (OPTIONAL)
# ==============================
if __name__ == "__main__":
    with open("data/sample_input.json", "r", encoding="utf-8") as f:
        input_data = json.load(f)

    result = run_pipeline(input_data)
    print(json.dumps(result, indent=2))