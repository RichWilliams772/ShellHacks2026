# Aaron Green
# Decides how much evidence backs a Coordination Score - separate from how high the score is.

# Describes evidence, never magnitude. A score of 92 with MEDIUM confidence and
# a score of 35 with HIGH confidence are both valid, ordinary outputs.
#
#   HIGH          4/4 components, geography confidence HIGH/MEDIUM, temporal
#                 data available, similarity confidence HIGH/MEDIUM.
#   MEDIUM        3/4 components (one missing, geography always present since
#                 that's required for eligibility at all), geography
#                 confidence HIGH/MEDIUM.
#   LOW           eligible, but weaker than the above - e.g. geography
#                 confidence below HIGH/MEDIUM. Never occurs in the current
#                 dataset (geography confidence is always HIGH or MEDIUM
#                 whenever geography_available is true), but real if a future
#                 project only has approximate/LOW-confidence geography.
#   INSUFFICIENT  not score-eligible at all - there is no score to have
#                 confidence about.
#
# Deliberately does NOT gate on temporal_precision being "month" rather than
# "mixed"/"year". That imprecision is already priced into temporal_score
# itself (Task 3 caps mixed/year-precision scores at 80, never 100) -
# checking it again here would penalize the same fact twice.
ADEQUATE_CONFIDENCE_LEVELS = {"HIGH", "MEDIUM"}


def calculate_score_confidence(eligible, components_available, geography_confidence,
                               temporal_data_available, similarity_confidence):
    if not eligible:
        return "INSUFFICIENT"

    geography_ok = geography_confidence in ADEQUATE_CONFIDENCE_LEVELS
    similarity_ok = similarity_confidence in ADEQUATE_CONFIDENCE_LEVELS

    if components_available == 4 and geography_ok and temporal_data_available and similarity_ok:
        return "HIGH"
    if components_available >= 3 and geography_ok:
        return "MEDIUM"
    return "LOW"
