from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

def load_sentence_transformer(model_name="paraphrase-MiniLM-L6-v2"):
    return SentenceTransformer(model_name)

def rank_by_relevance(title_items, job_to_do, st_model):
    section_titles = [item['section_title'] for item in title_items]
    if not section_titles:
        return []
    title_embeddings = st_model.encode(section_titles)
    task_embedding = st_model.encode([job_to_do])

    similarities = cosine_similarity(title_embeddings, task_embedding).reshape(-1)

    for item, sim in zip(title_items, similarities):
        item['relevance_score'] = float(sim)

    return sorted(title_items, key=lambda x: -x['relevance_score'])
