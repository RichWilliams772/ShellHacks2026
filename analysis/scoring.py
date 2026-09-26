# Aaron Green
# Combines geography, schedule, and similarity into one transparent Coordination Score.

from analysis.infrastructure import weighted_available_average

# Prototype decision-support weights, not learned coefficients and not an
# industry standard. PROJECT_SPEC defines this exact weighting (section 16);
# nothing here overrides it.
COORDINATION_WEIGHTS = {
    "geographic": 0.40,
    "temporal": 0.30,
    "text_similarity": 0.20,
    "infrastructure": 0.10,
}

# A pair needs at least 3 of these 4 signals, and geography specifically must
# be one of them - PROJECT_SPEC treats WHERE as the precondition for
# operational relevance (section 8), so text/infrastructure similarity alone
# must never manufacture a top "opportunity" for two projects nobody can even
# place near each other.
#
# On the real Task 4 data this reduces to "geography must be available":
# text_similarity and infrastructure_similarity are populated for 100% of
# pairs, so every geo-available row already clears 3 components without help.
# The >=3 check is kept anyway - not because it does independent work today,
# but so a future data change (e.g. missing project text) can't silently slip
# a 2-component pair through on geography alone.
MIN_COMPONENTS_REQUIRED = 3

# Round only here, for display. Every internal calculation stays full-precision.
DISPLAY_DECIMALS = 1


def components_available(geographic, temporal, text_similarity, infrastructure):
    """How many of the 4 signals are non-null for this pair. 0-4."""
    return sum(v is not None for v in (geographic, temporal, text_similarity, infrastructure))


def is_score_eligible(geographic, temporal, text_similarity, infrastructure):
    """Geography must be present, and at least 3 of the 4 signals overall.

    Missing geography disqualifies a pair regardless of how strong the other
    three signals are - text/infrastructure similarity alone must never
    produce a top-ranked "opportunity" for two projects with no known location
    relationship (PROJECT_SPEC section 15).
    """
    if geographic is None:
        return False
    return components_available(geographic, temporal, text_similarity, infrastructure) >= MIN_COMPONENTS_REQUIRED


def score_weight_coverage(geographic, temporal, text_similarity, infrastructure):
    """Fraction of the full weighting scheme that had real evidence behind it.

    1.00 = all 4 present. 0.90 = infrastructure (10%) missing. This describes
    completeness, not accuracy - a 0.60-coverage score is not "40% wrong."
    """
    scores = {"geographic": geographic, "temporal": temporal,
             "text_similarity": text_similarity, "infrastructure": infrastructure}
    available_weight = sum(COORDINATION_WEIGHTS[name] for name, value in scores.items()
                           if value is not None)
    return round(available_weight, 4)


def calculate_coordination_score(geographic, temporal, text_similarity, infrastructure):
    """0-100, or None if the pair is not score-eligible.

    Available-weight rebalancing (via the same weighted_available_average used
    for Task 4's infrastructure_similarity) - a missing component is excluded
    from both the numerator and the denominator, never treated as a 0. This
    alone is not sufficient protection against sparse pairs, which is why
    eligibility is checked first and separately.
    """
    if not is_score_eligible(geographic, temporal, text_similarity, infrastructure):
        return None
    scores = {"geographic": geographic, "temporal": temporal,
             "text_similarity": text_similarity, "infrastructure": infrastructure}
    raw = weighted_available_average(scores, COORDINATION_WEIGHTS)
    return round(raw, DISPLAY_DECIMALS) if raw is not None else None


def voltage_label_or_fallback(label, min_kv, max_kv):
    """Duke has no filed voltage_label (TECO's schema does) - build one from
    min/max so evidence never prints the literal word 'None'.
    """
    if label:
        return label
    if min_kv is None or max_kv is None:
        return None
    return f"{min_kv:g} kV" if min_kv == max_kv else f"{min_kv:g}-{max_kv:g} kV"


def build_evidence(row):
    """Deterministic evidence sentences, generated only from already-calculated
    fields. No new claim is made here that an earlier task didn't already
    establish and store as a column.
    """
    evidence = []

    if row.get("geography_available"):
        reason = row.get("geographic_reason")
        if reason:
            evidence.append(reason)
    else:
        evidence.append("Insufficient location data to estimate distance between these projects.")

    if row.get("temporal_data_available"):
        reason = row.get("temporal_reason")
        if reason:
            evidence.append(reason)
    else:
        evidence.append("Insufficient schedule information to compare timing.")

    text_score = row.get("text_similarity_score")
    if text_score is not None:
        terms = row.get("shared_text_terms")
        if terms:
            evidence.append(f"Project descriptions share terms related to {terms.replace(';', ',')}.")
        else:
            evidence.append(f"Project text similarity is {text_score:.0f}/100.")

    type_a, type_b = row.get("project_a_type"), row.get("project_b_type")
    type_similarity = row.get("project_type_similarity")
    if type_similarity == 100:
        evidence.append(f"Both projects are categorized as {type_a}.")
    elif type_similarity == 0:
        evidence.append(f"Project types differ ({type_a} vs {type_b}).")

    voltage_similarity = row.get("voltage_similarity")
    label_a = voltage_label_or_fallback(row.get("project_a_voltage_label"),
                             row.get("project_a_voltage_min_kv"), row.get("project_a_voltage_max_kv"))
    label_b = voltage_label_or_fallback(row.get("project_b_voltage_label"),
                             row.get("project_b_voltage_min_kv"), row.get("project_b_voltage_max_kv"))
    if voltage_similarity == 100 and label_a and label_b:
        evidence.append(f"Both projects involve compatible voltage infrastructure ({label_a} / {label_b}).")
    elif voltage_similarity is not None and voltage_similarity <= 20 and label_a and label_b:
        evidence.append(f"Project voltage classes differ substantially ({label_a} vs {label_b}).")

    return evidence


TIE_BREAK_COLUMNS = ["coordination_score", "geographic_score", "temporal_score"]
TIE_BREAK_ASCENDING = [False, False, False]


def rank_opportunities(rows):
    """Assigns opportunity_rank to eligible rows only; ineligible rows get None.

    Deterministic tie-break: coordination_score desc, geographic_score desc,
    temporal_score desc, pair_id asc (PROJECT_SPEC section 21). A missing
    tie-break value sorts last within its own comparison, never first.
    """
    eligible = [r for r in rows if r["coordination_score_eligible"]]
    eligible.sort(key=lambda r: (
        -(r["coordination_score"] if r["coordination_score"] is not None else -1),
        -(r["geographic_score"] if r["geographic_score"] is not None else -1),
        -(r["temporal_score"] if r["temporal_score"] is not None else -1),
        r["pair_id"],
    ))
    for rank, row in enumerate(eligible, start=1):
        row["opportunity_rank"] = rank
    for row in rows:
        row.setdefault("opportunity_rank", None)
    return rows
