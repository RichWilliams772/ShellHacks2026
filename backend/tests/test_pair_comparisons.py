"""Internal adapter for Aaron's Duke–TECO pair features."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from app.comparison import PAIR_FEATURE_COLUMNS, PairComparisonAdapter
from app.errors import LoaderError
from app.processed_loader import ProcessedProjectLoader

PROJECTS = ProcessedProjectLoader().load_projects()
COMPARISONS = PairComparisonAdapter(PROJECTS).load()
BY_PAIR = {comparison.pair_id: comparison for comparison in COMPARISONS}


def test_adapter_joins_all_pair_feature_rows() -> None:
    assert len(COMPARISONS) == 160
    assert len(BY_PAIR) == 160
    utilities = {"Duke Energy Florida", "Tampa Electric"}
    catalog = {project.id: project for project in PROJECTS}
    for comparison in COMPARISONS:
        assert {comparison.project_a.utility, comparison.project_b.utility} == utilities
        assert comparison.project_a.model_dump() == catalog[comparison.project_a.id].model_dump()
        assert comparison.project_b.model_dump() == catalog[comparison.project_b.id].model_dump()
        assert comparison.comparison_status == "partial_public_features"
        assert comparison.features_complete is False
        assert comparison.coordination_score is None
        assert comparison.shared_resources is None
        assert comparison.geography.distance_kind == "known_endpoints"
        assert comparison.geography.route_distance_miles is None
        assert "transmission routes" in comparison.geography.distance_note


def test_missing_geography_stays_null_and_a_measured_zero_stays_zero() -> None:
    missing = BY_PAIR["DUKE-P0132__TECO-66833"]
    assert missing.geography.geography_available is False
    assert missing.geography.geography_available_both is False
    assert missing.geography.geography_point_count_a == 2
    assert missing.geography.geography_point_count_b == 0
    assert missing.geography.minimum_endpoint_distance_miles is None
    assert missing.geography.geographic_score is None
    assert missing.geography.project_a_nearest_endpoint is None
    assert missing.geography.pair_geography_confidence == "UNKNOWN"
    assert missing.geography.project_b_location_confidence == "UNKNOWN"
    assert missing.project_b.location_confidence == "UNKNOWN"
    assert "Insufficient location data" in (missing.geography.geographic_reason or "")

    measured_zero = BY_PAIR["DUKE-P0017__TECO-230037"]
    assert measured_zero.geography.geography_available is True
    assert measured_zero.geography.minimum_endpoint_distance_miles == 106.08
    assert measured_zero.geography.geographic_score == 0
    assert measured_zero.geography.geographic_score is not None
    assert measured_zero.geography.project_a_nearest_endpoint == "origin"
    assert measured_zero.geography.project_b_nearest_endpoint == "destination"

    unmeasured = [row for row in COMPARISONS if row.geography.geographic_score is None]
    assert len(unmeasured) == 110
    assert all(row.geography.minimum_endpoint_distance_miles is None for row in unmeasured)
    assert all(row.geography.geography_available is False for row in unmeasured)


def test_mixed_temporal_precision_does_not_become_overlap_months() -> None:
    stale = BY_PAIR["DUKE-P0313__TECO-66653"]
    assert stale.temporal.temporal_precision == "mixed"
    assert stale.temporal.temporal_data_available is True
    assert stale.temporal.schedule_overlap is None
    assert stale.temporal.schedule_overlap_months is None
    assert stale.temporal.schedule_overlap_months_are_exact is False
    assert stale.temporal.same_active_year is False
    assert stale.temporal.year_difference == 3
    assert stale.temporal.temporal_score == 20
    assert stale.geography.geographic_score == 100
    assert stale.geography.minimum_endpoint_distance_miles == 6.03
    assert stale.geography.pair_geography_confidence == "MEDIUM"
    assert stale.project_a.location_confidence == "HIGH"
    assert stale.project_b.location_confidence == "MEDIUM"
    assert "3 years" in (stale.temporal.temporal_reason or "")
    assert stale.coordination_score is None

    current = BY_PAIR["DUKE-P0132__TECO-230037"]
    assert current.temporal.temporal_precision == "mixed"
    assert current.temporal.schedule_overlap_months is None
    assert current.temporal.year_difference == 1
    assert current.temporal.temporal_score == 50
    assert current.geography.geographic_score == 80
    assert current.geography.minimum_endpoint_distance_miles == 17.76

    unknown = [row for row in COMPARISONS if row.temporal.temporal_precision == "unknown"]
    assert len(unknown) == 16
    assert all(row.temporal.temporal_score is None for row in unknown)
    assert all(row.temporal.year_difference is None for row in unknown)
    assert all(row.temporal.schedule_overlap_months is None for row in unknown)
    assert all(row.temporal.schedule_overlap_months_are_exact is False for row in COMPARISONS)


def test_joined_projects_keep_provenance() -> None:
    pair = BY_PAIR["DUKE-P0132__TECO-230037"]
    assert pair.project_a.data_type == "public"
    assert pair.project_b.data_type == "public"
    assert pair.project_a.date_precision == "year"
    assert pair.project_a.estimated_in_service_year == 2027
    assert pair.project_a.source_url is not None
    assert pair.project_a.source_url.startswith("https://www.duke-energy.com/")
    assert pair.project_a.provenance_gaps == []
    assert pair.project_a.geography_source is not None
    assert "Our Grid Future" in pair.project_a.source_name
    assert pair.project_b.date_precision == "month"
    assert pair.project_b.source_url is None
    assert pair.project_b.provenance_gaps == ["source_url"]
    assert pair.project_b.source_url_note is not None
    assert pair.project_b.geography_source is not None
    assert "Storm Protection Plan" in pair.project_b.source_name
    assert pair.geography.project_a_location_confidence == "HIGH"
    assert pair.geography.project_b_location_confidence == "HIGH"


def test_unknown_project_reference_is_rejected() -> None:
    catalog = [project for project in PROJECTS if project.id != "TECO-66833"]
    with pytest.raises(LoaderError, match="unknown project_b_id TECO-66833"):
        PairComparisonAdapter(catalog).load()


def test_blank_tokens_stay_null_and_same_utility_pairs_fail(tmp_path: Path) -> None:
    projects = PROJECTS
    nan_path = tmp_path / "nan-pairs.csv"
    _write_pairs(
        nan_path,
        [
            {
                "pair_id": "DUKE-P0132__TECO-230037",
                "project_a_id": "DUKE-P0132",
                "project_b_id": "TECO-230037",
                "project_a_utility": "Duke Energy Florida",
                "project_b_utility": "Tampa Electric",
                "geography_available": "False",
                "geography_available_both": "False",
                "geography_point_count_b": "0",
                "minimum_endpoint_distance_miles": "nan",
                "geographic_score": "NaN",
                "temporal_data_available": "False",
                "temporal_precision": "unknown",
                "schedule_overlap_months": "none",
                "year_difference": "null",
                "temporal_score": "<NA>",
                "text_similarity_available": "False",
                "text_similarity_raw": "nan",
                "text_similarity_score": "NaN",
                "shared_text_terms": "none",
                "voltage_similarity": "null",
                "infrastructure_similarity_available": "False",
                "infrastructure_similarity": "<NA>",
                "similarity_confidence": "",
            }
        ],
    )
    loaded = PairComparisonAdapter(projects, nan_path).load()
    assert loaded[0].geography.minimum_endpoint_distance_miles is None
    assert loaded[0].geography.geographic_score is None
    assert loaded[0].temporal.schedule_overlap_months is None
    assert loaded[0].temporal.year_difference is None
    assert loaded[0].temporal.temporal_score is None
    assert loaded[0].similarity.text_similarity_raw is None
    assert loaded[0].similarity.text_similarity_score is None
    assert loaded[0].similarity.shared_text_terms == []
    assert loaded[0].similarity.voltage_similarity is None
    assert loaded[0].similarity.infrastructure_similarity is None
    assert '"nan"' not in loaded[0].model_dump_json().lower()

    same_utility = tmp_path / "same-utility.csv"
    _write_pairs(
        same_utility,
        [
            {
                "pair_id": "DUKE-P0132__DUKE-P0313",
                "project_a_id": "DUKE-P0132",
                "project_b_id": "DUKE-P0313",
            }
        ],
    )
    with pytest.raises(LoaderError, match="two Duke Energy Florida projects"):
        PairComparisonAdapter(projects, same_utility).load()


def test_similarity_values_keep_source_scales_and_null_voltage() -> None:
    assert len(COMPARISONS) == 160
    same_type = BY_PAIR["DUKE-P0132__TECO-230037"]
    similarity = same_type.similarity
    assert similarity.text_similarity_available is True
    assert similarity.text_similarity_raw == 0.316
    assert similarity.text_similarity_raw_scale == "0_to_1"
    assert similarity.text_similarity_score == 31.6
    assert similarity.text_similarity_score_scale == "0_to_100"
    assert similarity.text_similarity_raw != similarity.text_similarity_score
    assert similarity.shared_text_terms_raw == "transmission; upgrade"
    assert similarity.shared_text_terms == ["transmission", "upgrade"]
    assert similarity.project_type_similarity == 100
    assert similarity.project_type_similarity_scale == "0_to_100"
    assert similarity.voltage_similarity == 100
    assert similarity.voltage_similarity_scale == "0_to_100"
    assert similarity.infrastructure_similarity_available is True
    assert similarity.infrastructure_similarity == 100
    assert similarity.infrastructure_similarity_scale == "0_to_100"
    assert similarity.similarity_confidence == "HIGH"
    assert same_type.geography.geographic_score == 80
    assert same_type.temporal.temporal_score == 50
    assert same_type.coordination_score is None
    assert same_type.shared_resources is None

    separate = BY_PAIR["DUKE-P0062__TECO-230037"]
    assert separate.similarity.text_similarity_raw == 0.1123
    assert separate.similarity.text_similarity_score == 11.23
    assert separate.similarity.infrastructure_similarity == 100
    assert separate.similarity.project_type_similarity == 100
    assert separate.similarity.voltage_similarity == 100
    assert "0 to 1" in separate.similarity.scale_note
    assert "0 to 100" in separate.similarity.scale_note

    substation = BY_PAIR["DUKE-P0132__TECO-SUB-lake-agnes"]
    assert substation.project_b.project_type == "substation_hardening"
    assert substation.project_b.voltage_kv is None
    assert substation.similarity.voltage_similarity is None
    assert substation.similarity.project_type_similarity == 0
    assert substation.similarity.infrastructure_similarity == 0
    assert substation.similarity.infrastructure_similarity_available is True
    assert substation.similarity.text_similarity_raw == 0
    assert substation.similarity.text_similarity_score == 0
    assert substation.similarity.shared_text_terms == []
    assert substation.similarity.similarity_confidence == "MEDIUM"
    assert "evidence" in substation.similarity.similarity_confidence_note

    missing_voltage = [
        row for row in COMPARISONS if row.similarity.voltage_similarity is None
    ]
    assert len(missing_voltage) == 50
    assert all(row.project_b.voltage_kv is None for row in missing_voltage)
    assert all(row.project_b.project_type == "substation_hardening" for row in missing_voltage)
    assert all(row.similarity.similarity_confidence == "MEDIUM" for row in missing_voltage)
    assert all(row.similarity.project_type_similarity is not None for row in COMPARISONS)


def test_adapter_does_not_recalculate_pair_features() -> None:
    source = Path(__file__).resolve().parents[1].joinpath("app", "comparison.py").read_text()
    assert "from analysis" not in source
    assert "haversine" not in source
    assert "app.scoring" not in source
    assert "app.geographic" not in source
    assert "app.temporal" not in source
    assert "app.resources" not in source
    assert "app.similarity" not in source
    assert "TfidfVectorizer" not in source
    assert "cosine_similarity" not in source


def _write_pairs(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=PAIR_FEATURE_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in PAIR_FEATURE_COLUMNS})
