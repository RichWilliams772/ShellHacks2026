# Aaron Green
# Measures how similar a Duke project and a TECO project sound, using their own words only.

import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# TF-IDF is fit ONCE across every unique project (Duke + TECO combined), never
# refit per pair - otherwise every pair would live in its own vocabulary and
# scores would not be comparable to each other.
#
# ngram_range=(1,1): tested (1,1) against (1,2) on the real 26-project corpus.
# Bigrams made same-type vs different-type separation worse, not better
# (median 0.097 vs 0.165), because a corpus this small rarely repeats an exact
# two-word phrase across documents. Unigrams win on both simplicity and result
# quality here - not a default left untested.
TFIDF_CONFIG = {"ngram_range": (1, 1), "stop_words": "english"}

# TECO's project names never contain utility branding today (checked directly:
# none of the 16 names include "Tampa Electric" or "TECO"), but this guards
# against it if that ever changes, per TASK_4 section 10.
UTILITY_BRANDING_TERMS = [
    "duke energy florida", "duke energy", "tampa electric company",
    "tampa electric", "teco",
]


def normalize_text(text):
    """Lowercase, strip utility branding, collapse whitespace. Nothing fancier."""
    text = str(text).lower()
    for term in UTILITY_BRANDING_TERMS:
        text = re.sub(rf"\b{re.escape(term)}\b", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def build_project_text(project_name, project_type):
    """One project's text, or None if there isn't enough to build a real document.

    Uses project_name + project_type only. Deliberately excludes voltage
    (already a separate structured component - including it here would double
    -count it), and excludes coordinates/dates/cost/utility identity, which
    describe WHERE/WHEN/WHO, not WHAT the project is.
    """
    name = normalize_text(project_name) if project_name else ""
    type_words = normalize_text(str(project_type).replace("_", " ")) if project_type else ""
    text = f"{name} {type_words}".strip()
    return text if text else None


def build_corpus(projects):
    """projects: list of (project_id, project_name, project_type).

    Returns {project_id: text}. A project with no usable text is left out of
    the dict entirely - it is looked up later and found missing, never given
    invented placeholder text.
    """
    corpus = {}
    for project_id, name, project_type in projects:
        text = build_project_text(name, project_type)
        if text:
            corpus[project_id] = text
    return corpus


def fit_tfidf(corpus):
    """corpus: {project_id: text}. Returns (vectorizer, matrix, id_to_row).

    Fit once, across every unique project. Pair-level similarity is computed
    afterward by looking up two rows in this one shared vector space.
    """
    ids = list(corpus.keys())
    vectorizer = TfidfVectorizer(**TFIDF_CONFIG)
    matrix = vectorizer.fit_transform(corpus[i] for i in ids)
    id_to_row = {project_id: row for row, project_id in enumerate(ids)}
    return vectorizer, matrix, id_to_row


def calculate_text_similarity(project_a_id, project_b_id, matrix, id_to_row):
    """Cosine similarity between two already-fitted TF-IDF rows, or None.

    None means at least one project had no usable text - a calculated 0.0
    (the vectors share no weighted terms) is a real, different answer and is
    returned as 0.0, not None.
    """
    if project_a_id not in id_to_row or project_b_id not in id_to_row:
        return None
    row_a, row_b = id_to_row[project_a_id], id_to_row[project_b_id]
    similarity = cosine_similarity(matrix[row_a], matrix[row_b])[0, 0]
    # Cosine similarity can drift a hair outside [0, 1] on floating-point noise.
    return max(0.0, min(1.0, float(similarity)))


def shared_terms(project_a_id, project_b_id, vectorizer, matrix, id_to_row, top_n=5):
    """The terms that actually drove a similarity score - real evidence, not an LLM guess.

    Ranked by how much each term's weight in A times its weight in B
    contributed to the cosine similarity. Empty list if nothing overlaps.
    """
    if project_a_id not in id_to_row or project_b_id not in id_to_row:
        return []
    row_a = matrix[id_to_row[project_a_id]].toarray()[0]
    row_b = matrix[id_to_row[project_b_id]].toarray()[0]
    contribution = row_a * row_b
    if not contribution.any():
        return []
    feature_names = vectorizer.get_feature_names_out()
    top_indices = contribution.argsort()[::-1]
    return [feature_names[i] for i in top_indices[:top_n] if contribution[i] > 0]


def calculate_project_similarity(project_a, project_b, matrix, id_to_row, vectorizer):
    """Full text-similarity feature set for one Duke x TECO row.

    project_a / project_b: dicts with 'id'.
    """
    raw = calculate_text_similarity(project_a["id"], project_b["id"], matrix, id_to_row)
    terms = (shared_terms(project_a["id"], project_b["id"], vectorizer, matrix, id_to_row)
            if raw is not None else [])
    return {
        "text_similarity_available": raw is not None,
        "text_similarity_raw": round(raw, 4) if raw is not None else None,
        "text_similarity_score": round(raw * 100, 2) if raw is not None else None,
        "shared_text_terms": "; ".join(terms) if terms else None,
    }
