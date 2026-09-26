"""HTTP routes for the GridSync analysis API."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request

from app.assistant import answer_query
from app.config import SCORE_INTERPRETATION
from app.errors import (
    OpportunityNotFoundError,
    ProjectNotFoundError,
    SameUtilityError,
    UnknownUtilityError,
)
from app.filters import OpportunityFilters
from app.models import (
    AnalyzeRequest,
    AnalyzeResponse,
    AssistantQuery,
    AssistantResponse,
    HealthResponse,
    OpportunityResponse,
    ProjectListResponse,
    ProjectResponse,
    UtilityListResponse,
)
from app.service import AnalysisService

router = APIRouter()


def _service(request: Request) -> AnalysisService:
    service = request.app.state.service
    if not isinstance(service, AnalysisService):
        raise RuntimeError("GridSync analysis service is not configured")
    return service


def _filters(
    year: int | None,
    project_type: str | None,
    max_distance_miles: float | None,
    min_coordination_score: float | None,
) -> OpportunityFilters:
    return OpportunityFilters(
        year=year,
        project_type=project_type,
        max_distance_miles=max_distance_miles,
        min_coordination_score=min_coordination_score,
    )


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    service = _service(request)
    projects = service.envelope()
    analysis = service.analysis_envelope()
    return HealthResponse(
        dataset_status=projects.dataset_status,
        data_notice=projects.data_notice,
        contains_demo_data=projects.contains_demo_data,
        contains_verified_public_data=projects.contains_verified_public_data,
        analysis_dataset_status=analysis.dataset_status,
        analysis_data_notice=analysis.data_notice,
    )


@router.get("/utilities", response_model=UtilityListResponse)
def utilities(request: Request) -> UtilityListResponse:
    service = _service(request)
    envelope = service.envelope()
    return UtilityListResponse(
        dataset_status=envelope.dataset_status,
        data_notice=envelope.data_notice,
        contains_demo_data=envelope.contains_demo_data,
        contains_verified_public_data=envelope.contains_verified_public_data,
        utilities=service.list_utilities(),
    )


@router.get("/projects", response_model=ProjectListResponse)
def projects(
    request: Request,
    utility: Annotated[str | None, Query()] = None,
    project_type: Annotated[str | None, Query()] = None,
    year: Annotated[int | None, Query(ge=1900, le=2200)] = None,
) -> ProjectListResponse:
    service = _service(request)
    envelope = service.envelope()
    found = service.list_projects(utility=utility, project_type=project_type, year=year)
    return ProjectListResponse(
        dataset_status=envelope.dataset_status,
        data_notice=envelope.data_notice,
        contains_demo_data=envelope.contains_demo_data,
        contains_verified_public_data=envelope.contains_verified_public_data,
        count=len(found),
        projects=found,
    )


@router.get("/projects/{project_id}", response_model=ProjectResponse)
def project_detail(project_id: str, request: Request) -> ProjectResponse:
    service = _service(request)
    try:
        project = service.get_project(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    envelope = service.envelope()
    return ProjectResponse(
        dataset_status=envelope.dataset_status,
        data_notice=envelope.data_notice,
        contains_demo_data=envelope.contains_demo_data,
        contains_verified_public_data=envelope.contains_verified_public_data,
        project=project,
    )


@router.get("/opportunities", response_model=AnalyzeResponse)
def opportunities(
    request: Request,
    utility_a: Annotated[str | None, Query()] = None,
    utility_b: Annotated[str | None, Query()] = None,
    year: Annotated[int | None, Query(ge=1900, le=2200)] = None,
    project_type: Annotated[str | None, Query()] = None,
    max_distance_miles: Annotated[float | None, Query(ge=0)] = None,
    min_coordination_score: Annotated[float | None, Query(ge=0, le=100)] = None,
) -> AnalyzeResponse:
    service = _service(request)
    left, right = _utility_pair(service, utility_a, utility_b)
    return _analyze(
        service,
        left,
        right,
        _filters(year, project_type, max_distance_miles, min_coordination_score),
    )


@router.get("/opportunities/{opportunity_id}", response_model=OpportunityResponse)
def opportunity_detail(opportunity_id: str, request: Request) -> OpportunityResponse:
    service = _service(request)
    try:
        opportunity = service.get_opportunity(opportunity_id)
    except OpportunityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    envelope = service.envelope()
    return OpportunityResponse(
        dataset_status=envelope.dataset_status,
        data_notice=envelope.data_notice,
        contains_demo_data=envelope.contains_demo_data,
        contains_verified_public_data=envelope.contains_verified_public_data,
        score_interpretation=SCORE_INTERPRETATION,
        opportunity=opportunity,
    )


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze(body: AnalyzeRequest, request: Request) -> AnalyzeResponse:
    service = _service(request)
    return _analyze(
        service,
        body.utility_a,
        body.utility_b,
        _filters(
            body.year,
            body.project_type,
            body.max_distance_miles,
            body.min_coordination_score,
        ),
    )


@router.post("/assistant/query", response_model=AssistantResponse)
def assistant_query(body: AssistantQuery, request: Request) -> AssistantResponse:
    service = _service(request)
    focus_id = body.opportunity_id
    if focus_id:
        try:
            catalog = [service.get_opportunity(focus_id)]
        except OpportunityNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    else:
        left, right = _utility_pair(service, body.utility_a, body.utility_b)
        catalog = _analyze(service, left, right, OpportunityFilters()).opportunities
    result = answer_query(
        body.query,
        catalog,
        client=getattr(request.app.state, "llm_client", None),
        history=body.messages,
        focus_id=focus_id,
    )
    envelope = service.envelope()
    return AssistantResponse(
        dataset_status=envelope.dataset_status,
        data_notice=envelope.data_notice,
        contains_demo_data=envelope.contains_demo_data,
        contains_verified_public_data=envelope.contains_verified_public_data,
        assistant_mode="structured_retrieval",
        llm_used=result.llm_used,
        llm_configured=result.llm_configured,
        answer=result.answer,
        note=result.note,
        filters_applied=result.filters_applied,
        opportunities=result.opportunities,
    )


def _utility_pair(
    service: AnalysisService,
    utility_a: str | None,
    utility_b: str | None,
) -> tuple[str, str]:
    if (utility_a is None) != (utility_b is None):
        raise HTTPException(
            status_code=400,
            detail="utility_a and utility_b must be supplied together",
        )
    if utility_a is None or utility_b is None:
        try:
            return service.default_utilities()
        except UnknownUtilityError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return utility_a, utility_b


def _analyze(
    service: AnalysisService,
    utility_a: str,
    utility_b: str,
    filters: OpportunityFilters,
) -> AnalyzeResponse:
    try:
        return service.analyze(utility_a, utility_b, filters)
    except SameUtilityError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except UnknownUtilityError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
