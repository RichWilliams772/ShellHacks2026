# Aaron Green
# Checks score_confidence describes evidence, never how high the score is.

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from analysis.confidence import calculate_score_confidence  # noqa: E402

failures = []


def check(name, condition, detail=""):
    if condition:
        print(f"PASS  {name}")
    else:
        print(f"FAIL  {name}" + (f" -- {detail}" if detail else ""))
        failures.append(name)


def test_complete_strong_evidence_is_high():
    confidence = calculate_score_confidence(
        eligible=True, components_available=4, geography_confidence="HIGH",
        temporal_data_available=True, similarity_confidence="HIGH")
    check("4/4 components with strong confidence fields gives HIGH",
          confidence == "HIGH", confidence)


def test_partial_evidence_is_medium():
    confidence = calculate_score_confidence(
        eligible=True, components_available=3, geography_confidence="HIGH",
        temporal_data_available=False, similarity_confidence="HIGH")
    check("3/4 components gives MEDIUM, not HIGH", confidence == "MEDIUM", confidence)


def test_ineligible_is_insufficient():
    confidence = calculate_score_confidence(
        eligible=False, components_available=1, geography_confidence=None,
        temporal_data_available=False, similarity_confidence="HIGH")
    check("an ineligible pair is always INSUFFICIENT", confidence == "INSUFFICIENT", confidence)


def test_weak_geography_confidence_prevents_high():
    confidence = calculate_score_confidence(
        eligible=True, components_available=4, geography_confidence="LOW",
        temporal_data_available=True, similarity_confidence="HIGH")
    check("LOW geography confidence blocks HIGH even with 4/4 components",
          confidence != "HIGH", confidence)


def test_high_score_does_not_imply_high_confidence():
    """The exact case PROJECT_SPEC calls out: score=92, confidence=MEDIUM is valid."""
    confidence = calculate_score_confidence(
        eligible=True, components_available=3, geography_confidence="MEDIUM",
        temporal_data_available=False, similarity_confidence="HIGH")
    # A high coordination_score could still pair with this confidence level -
    # this function never looks at the score itself, only at evidence inputs.
    check("confidence calculation takes no score argument at all",
          "score" not in calculate_score_confidence.__code__.co_varnames[
              :calculate_score_confidence.__code__.co_argcount])
    check("3/4 components with MEDIUM geography confidence is MEDIUM, regardless of score",
          confidence == "MEDIUM", confidence)


def test_low_score_does_not_imply_low_confidence():
    """A confidently-dissimilar pair: full evidence, low score, still HIGH confidence."""
    confidence = calculate_score_confidence(
        eligible=True, components_available=4, geography_confidence="HIGH",
        temporal_data_available=True, similarity_confidence="HIGH")
    check("full evidence gives HIGH confidence no matter what the score turns out to be",
          confidence == "HIGH", confidence)


def test_mixed_precision_temporal_does_not_block_high():
    """Task 3 already caps mixed/year-precision temporal scores below 100 -
    confidence must not penalize the same imprecision a second time.
    """
    confidence = calculate_score_confidence(
        eligible=True, components_available=4, geography_confidence="HIGH",
        temporal_data_available=True, similarity_confidence="HIGH")
    check("temporal_data_available=True is enough for HIGH; precision is not re-checked here",
          confidence == "HIGH", confidence)


def main():
    test_complete_strong_evidence_is_high()
    test_partial_evidence_is_medium()
    test_ineligible_is_insufficient()
    test_weak_geography_confidence_prevents_high()
    test_high_score_does_not_imply_high_confidence()
    test_low_score_does_not_imply_low_confidence()
    test_mixed_precision_temporal_does_not_block_high()

    print()
    if failures:
        print(f"{len(failures)} check(s) failed: {', '.join(failures)}")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
