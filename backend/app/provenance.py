"""Dataset-level labels so clients can tell demo fixtures from public records."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Literal, NamedTuple

DatasetStatus = Literal["demo", "verified_public", "mixed", "empty"]

DEMO_NOTICE = (
    "This response contains explicitly labeled demo fixtures (data_type='demo'). "
    "These are not verified Duke Energy Florida or Tampa Electric public records. "
    "Source fields identify the demo fixture set rather than a utility filing."
)
PUBLIC_NOTICE = (
    "Every loaded project is marked data_type='public'. Provenance is limited to the "
    "source_name and source_url supplied in the data file. GridSync does not scrape "
    "filings and does not certify that those rows are complete Duke or TECO records."
)
MIXED_NOTICE = (
    "This response mixes demo fixtures and rows marked data_type='public'. "
    "Read data_type on each project before describing it as a public utility project."
)
EMPTY_NOTICE = (
    "No project records are loaded. GridSync is not showing verified Duke Energy "
    "Florida or Tampa Electric public records."
)
SOURCE_URL_GAP_NOTICE = (
    "The processed TECO file has no source_url column. Those projects keep "
    "source_url null and list source_url in provenance_gaps. No per-project URL was added."
)
DEMO_ANALYSIS_ISOLATED_NOTICE = (
    "Opportunity endpoints still use the labeled demo catalog. Those coordination "
    "scores were not calculated from the public processed records and must stay labeled demo."
)
SOURCE_URL_MISSING_NOTE = (
    "source_url is missing from this processed record. source_name is the filing "
    "citation from project_source, not a URL. No URL was invented."
)


def dataset_status(data_types: Iterable[str]) -> DatasetStatus:
    kinds = set(data_types)
    if not kinds:
        return "empty"
    if kinds == {"demo"}:
        return "demo"
    if kinds == {"public"}:
        return "verified_public"
    return "mixed"


def data_notice(status: DatasetStatus) -> str:
    if status == "demo":
        return DEMO_NOTICE
    if status == "verified_public":
        return PUBLIC_NOTICE
    if status == "mixed":
        return MIXED_NOTICE
    return EMPTY_NOTICE


class DataLabels(NamedTuple):
    dataset_status: DatasetStatus
    data_notice: str
    contains_demo_data: bool
    contains_verified_public_data: bool


def labels_for(data_types: Iterable[str]) -> DataLabels:
    kinds = list(data_types)
    status = dataset_status(kinds)
    return DataLabels(
        dataset_status=status,
        data_notice=data_notice(status),
        contains_demo_data=any(kind == "demo" for kind in kinds),
        contains_verified_public_data=any(kind == "public" for kind in kinds),
    )


def pair_data_type(left: str, right: str) -> Literal["demo", "public", "mixed"]:
    if left == "demo" and right == "demo":
        return "demo"
    if left == "public" and right == "public":
        return "public"
    return "mixed"
