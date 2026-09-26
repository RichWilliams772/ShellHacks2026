# Aaron Green
# Maps project types to potential coordination categories - a category to look into, not a promise anyone can share it.

# GridSync prototype resource-compatibility rules. These are domain-assumption
# heuristics tied to normalized project type, not learned from historical
# coordination outcomes and not derived from any utility's actual equipment,
# crew, or material inventory - GridSync has no such data.
#
# Deliberately smaller than a generic taxonomy would allow. Dropped from an
# earlier draft: "cranes" (folded into heavy_equipment - naming a specific
# machine implies a concreteness public planning data can't support), plus
# transformer_logistics / excavation_crews / trenching_equipment /
# traffic_control / specialized_engineering, none of which are supported by
# any project type actually present in this dataset (no undergrounding or
# substation-upgrade project exists here - only transmission work and
# substation storm hardening).
DISPLAY_NAMES = {
    "specialized_line_crews": "Specialized Line Crews",
    "heavy_equipment": "Heavy Equipment",
    "material_logistics": "Material Logistics",
    "outage_planning": "Outage Planning",
    "construction_mobilization": "Construction Mobilization",
    "electrical_crews": "Electrical Crews",
}

# Only covers project types that actually appear in the normalized Duke/TECO
# data (transmission_upgrade, transmission_line, substation_hardening). A
# project type not listed here - "unknown", missing, or anything new - maps
# to no categories at all rather than a guess.
RESOURCE_RULES = {
    "transmission_upgrade": {
        "specialized_line_crews", "heavy_equipment", "material_logistics",
        "outage_planning", "construction_mobilization",
    },
    "transmission_line": {
        "specialized_line_crews", "heavy_equipment", "material_logistics",
        "outage_planning", "construction_mobilization",
    },
    "substation_hardening": {
        "electrical_crews", "material_logistics", "outage_planning",
        "construction_mobilization",
    },
}

# A category exists in the shared set purely from matching project types -
# that intersection is fixed and geography/schedule can never add or remove a
# category from it (section 24/25's actual rule: don't CREATE a resource from
# geography or schedule alone). But once a category already exists, sections
# 22/23 explicitly allow geography and schedule to "strengthen" (or, just as
# reasonably, weaken) how confidently to state it - an earlier version of this
# comment overstated the prohibition as covering that case too. It doesn't.
#
#   HIGH    identical project type on both sides AND compatible voltage class.
#           Two independent structured signals agreeing.
#   MEDIUM  identical project type alone, OR a cross-type shared category
#           (e.g. outage_planning applies to most grid work) reinforced by
#           compatible voltage. One corroborating signal.
#   LOW     the category exists only because it is a broad category common to
#           both project types, with no type-identity or voltage support.
#
# Coordination Score itself never appears here (section 19's actual target -
# "if coordination_score > 80: all HIGH" is exactly the shortcut banned), and
# neither does schedule (no pair in this dataset has evidence precise enough
# to justify a threshold - temporal precision is never better than "mixed").
# But a real, calculated geographic_score does apply, as a downgrade only:
# two project types matching on paper is not strong coordination evidence if
# the projects are 100+ miles apart, per PROJECT_SPEC's own "weak proximity"
# band (score <= 20 is exactly that band - not a new threshold invented here).
# A MISSING geographic_score never downgrades anything - not knowing the
# distance is not evidence the distance is bad.
VOLTAGE_COMPATIBLE_THRESHOLD = 70
WEAK_GEOGRAPHY_THRESHOLD = 20
POTENTIAL_DOWNGRADE = {"HIGH": "MEDIUM", "MEDIUM": "LOW", "LOW": "LOW"}


def get_project_resource_categories(project_type):
    """The categories associated with one project's normalized type. Empty
    set for a missing or unrecognized type - never a guess.
    """
    if not project_type:
        return set()
    return set(RESOURCE_RULES.get(str(project_type).strip().lower(), set()))


def match_shared_resources(project_a_type, project_b_type):
    """Categories both projects' types map to. Deterministic exact
    intersection - no fuzzy matching, no embeddings.
    """
    return get_project_resource_categories(project_a_type) & get_project_resource_categories(project_b_type)


def calculate_resource_potential(project_type_similarity, voltage_similarity, geographic_score=None):
    """HIGH/MEDIUM/LOW for a category already confirmed to be shared.

    Only called once a resource is already known to be in both projects'
    category sets - this function never decides whether a resource EXISTS,
    only how strongly to state it once it does. geographic_score can only
    move the result down a tier, never up, and never on its own - a resource
    still requires type/voltage evidence to reach any tier at all.
    """
    same_type = project_type_similarity == 100
    voltage_compatible = voltage_similarity is not None and voltage_similarity >= VOLTAGE_COMPATIBLE_THRESHOLD

    if same_type and voltage_compatible:
        potential = "HIGH"
    elif same_type or voltage_compatible:
        potential = "MEDIUM"
    else:
        potential = "LOW"

    if geographic_score is not None and geographic_score <= WEAK_GEOGRAPHY_THRESHOLD:
        potential = POTENTIAL_DOWNGRADE[potential]
    return potential


def build_resource_evidence(resource_id, project_a_type, project_b_type,
                            project_type_similarity, voltage_similarity,
                            voltage_label_a, voltage_label_b, geography_downgraded):
    """Deterministic sentences for one shared resource category. Always
    phrased as a category to investigate, never as a confirmed shared item -
    GridSync does not know either utility's actual equipment, crew, or
    material availability.
    """
    display_name = DISPLAY_NAMES[resource_id]
    evidence = []

    if project_type_similarity == 100:
        evidence.append(f"Both projects are categorized as {project_a_type}, a category the "
                        f"GridSync prototype rules associate with {display_name.lower()}.")
    else:
        evidence.append(f"{project_a_type} and {project_b_type} projects are both associated "
                        f"with {display_name.lower()} under the GridSync prototype rules.")

    if voltage_similarity is not None and voltage_similarity >= VOLTAGE_COMPATIBLE_THRESHOLD \
       and voltage_label_a and voltage_label_b:
        evidence.append(f"Both projects also involve compatible voltage infrastructure "
                        f"({voltage_label_a} / {voltage_label_b}).")

    if geography_downgraded:
        evidence.append("The two known project locations are far enough apart that practical "
                        "coordination on this category is less certain.")

    return evidence


def build_shared_resources(project_a_type, project_b_type, project_type_similarity,
                           voltage_similarity, voltage_label_a, voltage_label_b,
                           geographic_score=None):
    """The full potential_shared_resources list for one pair, sorted for a
    stable, deterministic order (HIGH first, then alphabetical).
    """
    shared = match_shared_resources(project_a_type, project_b_type)
    if not shared:
        return []

    potential = calculate_resource_potential(project_type_similarity, voltage_similarity, geographic_score)
    geography_downgraded = geographic_score is not None and geographic_score <= WEAK_GEOGRAPHY_THRESHOLD
    resources = [{
        "resource_id": resource_id,
        "display_name": DISPLAY_NAMES[resource_id],
        "potential": potential,
        "evidence": build_resource_evidence(resource_id, project_a_type, project_b_type,
                                            project_type_similarity, voltage_similarity,
                                            voltage_label_a, voltage_label_b, geography_downgraded),
    } for resource_id in shared]

    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    resources.sort(key=lambda r: (order[r["potential"]], r["resource_id"]))
    return resources
