# Aaron Green
# Checks the TF-IDF text-similarity logic in analysis/similarity.py.

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from analysis.similarity import (  # noqa: E402
    build_corpus, build_project_text, calculate_project_similarity,
    calculate_text_similarity, fit_tfidf, normalize_text, shared_terms,
)

failures = []


def check(name, condition, detail=""):
    if condition:
        print(f"PASS  {name}")
    else:
        print(f"FAIL  {name}" + (f" -- {detail}" if detail else ""))
        failures.append(name)


def test_identical_text_gives_near_one():
    corpus = {
        "A": "transmission upgrade project",
        "B": "transmission upgrade project",
        "C": "completely unrelated substation hardening work",
    }
    vectorizer, matrix, id_to_row = fit_tfidf(corpus)
    similarity = calculate_text_similarity("A", "B", matrix, id_to_row)
    check("identical text gives similarity near 1.0",
          similarity is not None and similarity > 0.99, f"got {similarity}")


def test_unrelated_text_gives_lower_similarity():
    corpus = {
        "A": "transmission upgrade project reliability",
        "B": "transmission upgrade project reliability",
        "C": "completely unrelated substation hardening storm work",
    }
    vectorizer, matrix, id_to_row = fit_tfidf(corpus)
    same = calculate_text_similarity("A", "B", matrix, id_to_row)
    different = calculate_text_similarity("A", "C", matrix, id_to_row)
    check("unrelated text scores lower than identical text",
          different < same, f"same={same}, different={different}")


def test_symmetry():
    corpus = {
        "A": "transmission upgrade reliability project",
        "B": "substation hardening extreme weather",
    }
    vectorizer, matrix, id_to_row = fit_tfidf(corpus)
    a_b = calculate_text_similarity("A", "B", matrix, id_to_row)
    b_a = calculate_text_similarity("B", "A", matrix, id_to_row)
    check("text similarity is symmetric", math.isclose(a_b, b_a, rel_tol=1e-9),
          f"{a_b} vs {b_a}")


def test_missing_text_returns_null():
    corpus = build_corpus([("A", "Some Project", "transmission_upgrade"),
                          ("B", None, "transmission_upgrade"),
                          ("C", "", None)])
    # C has neither a name nor a type - genuinely nothing to build text from.
    check("a project with no name AND no type is left out of the corpus",
          "C" not in corpus, str(corpus.keys()))
    # B has no name but does have a real project_type - that's real, available
    # data, not a placeholder, so it correctly still produces a document.
    check("a project with only a type (no name) still gets real partial text",
          corpus.get("B") == "transmission upgrade", corpus.get("B"))

    vectorizer, matrix, id_to_row = fit_tfidf(corpus)
    similarity = calculate_text_similarity("A", "C", matrix, id_to_row)
    check("similarity against a project with no text at all is null, not a fake number",
          similarity is None)


def test_missing_text_is_not_a_placeholder():
    text = build_project_text(None, None)
    check("no name and no type produces None, never 'unknown project'", text is None)
    text = build_project_text("", "")
    check("blank name and blank type also produce None", text is None)


def test_tfidf_fit_once_on_unique_corpus():
    # The same project text appearing in two different "pairs" must use the
    # exact same vector - proof the corpus was fit once, not refit per pair.
    corpus = {
        "DUKE-1": "north central florida upgrade project transmission upgrade",
        "TECO-1": "transmission upgrades 69 kv 66833 transmission upgrade",
        "TECO-2": "transmission upgrades 69 kv 66004 transmission upgrade",
    }
    vectorizer, matrix, id_to_row = fit_tfidf(corpus)
    sim_1 = calculate_text_similarity("DUKE-1", "TECO-1", matrix, id_to_row)
    sim_2 = calculate_text_similarity("DUKE-1", "TECO-2", matrix, id_to_row)
    # TECO-1 and TECO-2 differ only by a circuit number that appears in neither
    # other document, so DUKE-1's similarity to both should be identical -
    # that number carries no weight anywhere else in this shared vocabulary.
    check("a shared vocabulary gives consistent similarity across similar docs",
          math.isclose(sim_1, sim_2, rel_tol=1e-9), f"{sim_1} vs {sim_2}")


def test_similarity_range():
    corpus = {"A": "transmission upgrade", "B": "substation hardening",
             "C": "transmission upgrade reliability"}
    vectorizer, matrix, id_to_row = fit_tfidf(corpus)
    for a in corpus:
        for b in corpus:
            similarity = calculate_text_similarity(a, b, matrix, id_to_row)
            check(f"similarity({a},{b}) is within [0, 1]", 0.0 <= similarity <= 1.0 + 1e-9,
                  f"got {similarity}")


def test_score_conversion():
    project_a = {"id": "A"}
    project_b = {"id": "B"}
    corpus = {"A": "transmission upgrade reliability florida",
             "B": "transmission upgrade project central"}
    vectorizer, matrix, id_to_row = fit_tfidf(corpus)
    features = calculate_project_similarity(project_a, project_b, matrix, id_to_row, vectorizer)
    check("text_similarity_score is raw * 100",
          math.isclose(features["text_similarity_score"],
                      features["text_similarity_raw"] * 100, rel_tol=1e-6),
          str(features))


def test_zero_similarity_is_valid_and_distinct_from_null():
    corpus = {"A": "aaaaaa bbbbbb", "B": "cccccc dddddd"}
    vectorizer, matrix, id_to_row = fit_tfidf(corpus)
    similarity = calculate_text_similarity("A", "B", matrix, id_to_row)
    check("completely disjoint vocabularies give exactly 0.0, not null",
          similarity == 0.0, f"got {similarity}")
    check("0.0 is not None", similarity is not None)


def test_utility_branding_removed():
    text = normalize_text("Tampa Electric Transmission Upgrade")
    check("utility branding is stripped from text",
          "tampa electric" not in text, text)
    check("the meaningful words survive branding removal",
          "transmission" in text and "upgrade" in text, text)


def test_shared_terms_come_from_real_overlap():
    corpus = {"A": "transmission upgrade reliability", "B": "transmission upgrade project",
             "C": "substation hardening storm"}
    vectorizer, matrix, id_to_row = fit_tfidf(corpus)
    terms = shared_terms("A", "B", vectorizer, matrix, id_to_row)
    check("shared terms exist for overlapping text", "transmission" in terms or "upgrade" in terms,
          str(terms))
    terms_none = shared_terms("A", "C", vectorizer, matrix, id_to_row)
    check("no shared terms for disjoint text", terms_none == [], str(terms_none))


def main():
    test_identical_text_gives_near_one()
    test_unrelated_text_gives_lower_similarity()
    test_symmetry()
    test_missing_text_returns_null()
    test_missing_text_is_not_a_placeholder()
    test_tfidf_fit_once_on_unique_corpus()
    test_similarity_range()
    test_score_conversion()
    test_zero_similarity_is_valid_and_distinct_from_null()
    test_utility_branding_removed()
    test_shared_terms_come_from_real_overlap()

    print()
    if failures:
        print(f"{len(failures)} check(s) failed: {', '.join(failures)}")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
