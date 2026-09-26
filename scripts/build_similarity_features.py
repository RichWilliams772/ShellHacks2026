# Aaron Green
# Adds text and infrastructure similarity to every Duke x TECO pair from Task 3.

import csv
import math
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from analysis.infrastructure import (  # noqa: E402
    calculate_infrastructure_similarity, similarity_confidence,
)
from analysis.similarity import (  # noqa: E402
    build_corpus, calculate_project_similarity, fit_tfidf,
)

FEATURES_CSV = ROOT / "data" / "processed" / "duke_teco_pair_features.csv"
DUKE_CSV = ROOT / "data" / "processed" / "duke_projects_normalized.csv"
TECO_CSV = ROOT / "data" / "processed" / "teco_projects_geocoded.csv"
OUT_CSV = ROOT / "data" / "processed" / "duke_teco_pair_similarity.csv"

SIMILARITY_FIELDS = [
    "text_similarity_available", "text_similarity_raw", "text_similarity_score",
    "shared_text_terms", "project_type_similarity", "voltage_similarity",
    "infrastructure_similarity_available", "infrastructure_similarity",
    "similarity_confidence",
]


def clean(value):
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def build_unique_project_corpus(duke, teco):
    """Task 4's corpus is unique PROJECTS, not pairs - 10 Duke + 16 TECO = 26 docs,
    fit once. Fitting per pair would give every pair its own vocabulary and make
    scores incomparable to each other.
    """
    projects = ([(r.project_id, r.project_name, r.project_type) for r in duke.itertuples()]
               + [(r.project_id, r.project_name, r.project_type) for r in teco.itertuples()])
    return build_corpus(projects)


def project_a_view(row):
    return {"id": row["project_a_id"], "project_type": row["project_a_type"],
            "voltage_min_kv": row["project_a_voltage_min_kv"],
            "voltage_max_kv": row["project_a_voltage_max_kv"]}


def project_b_view(row):
    return {"id": row["project_b_id"], "project_type": row["project_b_type"],
            "voltage_min_kv": row["project_b_voltage_min_kv"],
            "voltage_max_kv": row["project_b_voltage_max_kv"]}


def build_features(pairs, matrix, id_to_row, vectorizer):
    rows = []
    for raw_row in pairs.to_dict("records"):
        row = {key: clean(value) for key, value in raw_row.items()}
        project_a, project_b = project_a_view(row), project_b_view(row)

        text = calculate_project_similarity(project_a, project_b, matrix, id_to_row, vectorizer)
        infra = calculate_infrastructure_similarity(project_a, project_b)
        confidence = similarity_confidence(
            text["text_similarity_available"],
            infra["project_type_similarity"], infra["voltage_similarity"])

        rows.append({**row, **text, **infra, "similarity_confidence": confidence})
    return rows


def summarize(rows):
    text_available = [r for r in rows if r["text_similarity_available"]]
    text_scores = sorted(r["text_similarity_score"] for r in text_available)
    infra_available = [r for r in rows if r["infrastructure_similarity_available"]]
    infra_scores = sorted(r["infrastructure_similarity"] for r in infra_available)
    type_compared = [r for r in rows if r["project_type_similarity"] is not None]
    voltage_compared = [r for r in rows if r["voltage_similarity"] is not None]

    def stats(values, label):
        if not values:
            print(f"  {label}: n/a (no pairs)")
            return
        n = len(values)
        median = values[n // 2] if n % 2 else (values[n // 2 - 1] + values[n // 2]) / 2
        print(f"  {label}: min={values[0]:.2f}  median={median:.2f}  max={values[-1]:.2f}")

    print("=" * 70)
    print("TASK 4 VALIDATION REPORT")
    print("=" * 70)
    print(f"total pairs:                          {len(rows)}")
    print(f"pairs with text similarity:            {len(text_available)}")
    print(f"pairs without text similarity:          {len(rows) - len(text_available)}")
    stats(text_scores, "text similarity (0-100)")
    print(f"pairs with project type comparison:    {len(type_compared)}")
    print(f"pairs with voltage comparison:         {len(voltage_compared)}")
    print(f"pairs with infrastructure similarity:  {len(infra_available)}")
    print(f"pairs without infrastructure similarity: {len(rows) - len(infra_available)}")
    stats(infra_scores, "infrastructure similarity (0-100)")
    print("confidence distribution:")
    counts = {}
    for r in rows:
        counts[r["similarity_confidence"]] = counts.get(r["similarity_confidence"], 0) + 1
    for level in ("HIGH", "MEDIUM", "LOW", "UNKNOWN"):
        if level in counts:
            print(f"  {level:<8} {counts[level]}")
    print("=" * 70)


def print_top_similar(rows, n=8):
    print(f"\nVALIDATION - top {n} pairs by text similarity (not a final ranking):")
    top = sorted((r for r in rows if r["text_similarity_available"]),
                key=lambda r: r["text_similarity_score"], reverse=True)[:n]
    for r in top:
        print(f"  {r['pair_id']:<28} text={r['text_similarity_score']:>6.2f}  "
              f"infra={r['infrastructure_similarity']}  "
              f"types=({r['project_a_type']}/{r['project_b_type']})  "
              f"terms=[{r['shared_text_terms']}]")
        print(f"      {r['project_a_name'][:34]:<34} <-> {r['project_b_name']}")


def print_low_similar(rows, n=5):
    print(f"\nVALIDATION - {n} lowest text-similarity pairs:")
    low = sorted((r for r in rows if r["text_similarity_available"]),
                key=lambda r: r["text_similarity_score"])[:n]
    for r in low:
        print(f"  {r['pair_id']:<28} text={r['text_similarity_score']:>6.2f}  "
              f"infra={r['infrastructure_similarity']}  "
              f"types=({r['project_a_type']}/{r['project_b_type']})")


def print_disagreements(rows, n=5):
    print(f"\nVALIDATION - text/infrastructure disagreements (not auto-corrected):")
    scored = [r for r in rows if r["text_similarity_score"] is not None
             and r["infrastructure_similarity"] is not None]

    high_text_low_infra = sorted(
        scored, key=lambda r: r["text_similarity_score"] - r["infrastructure_similarity"],
        reverse=True)[:n]
    print(f"  text HIGH, infrastructure LOW (top {n} by gap):")
    for r in high_text_low_infra:
        print(f"    {r['pair_id']:<28} text={r['text_similarity_score']:>6.2f}  "
              f"infra={r['infrastructure_similarity']:>6.2f}  "
              f"types=({r['project_a_type']}/{r['project_b_type']})")

    low_text_high_infra = sorted(
        scored, key=lambda r: r["infrastructure_similarity"] - r["text_similarity_score"],
        reverse=True)[:n]
    print(f"  text LOW, infrastructure HIGH (top {n} by gap):")
    for r in low_text_high_infra:
        print(f"    {r['pair_id']:<28} text={r['text_similarity_score']:>6.2f}  "
              f"infra={r['infrastructure_similarity']:>6.2f}  "
              f"types=({r['project_a_type']}/{r['project_b_type']})")


def main():
    pairs = pd.read_csv(FEATURES_CSV)
    duke = pd.read_csv(DUKE_CSV)
    teco = pd.read_csv(TECO_CSV, dtype={"circuit_id": "string"})

    corpus = build_unique_project_corpus(duke, teco)
    print(f"unique project corpus: {len(corpus)} documents "
          f"({len(duke)} Duke + {len(teco)} TECO)")
    vectorizer, matrix, id_to_row = fit_tfidf(corpus)
    print(f"TF-IDF vocabulary size: {len(vectorizer.vocabulary_)}")

    rows = build_features(pairs, matrix, id_to_row, vectorizer)
    fields = list(pairs.columns) + SIMILARITY_FIELDS

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nwrote {len(rows)} pairs with similarity features to {OUT_CSV.relative_to(ROOT)}\n")
    summarize(rows)
    print_top_similar(rows)
    print_low_similar(rows)
    print_disagreements(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
