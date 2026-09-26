"""GridSync FastAPI application."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings
from app.loader import ProjectSource, default_source
from app.processed_loader import ProcessedProjectLoader
from app.routes import router
from app.service import AnalysisService


def create_app(
    source: ProjectSource | None = None,
    settings: Settings | None = None,
) -> FastAPI:
    active_settings = settings or Settings.from_env()
    if active_settings.project_catalog == "processed":
        projects = ProcessedProjectLoader().load_projects()
        analysis_projects = None
    else:
        loader = source or default_source(active_settings.data_file)
        projects = loader.load_projects()
        analysis_projects = None
    service = AnalysisService(projects, active_settings, analysis_projects)
    app = FastAPI(
        title="GridSync",
        version="0.1.0",
        summary="Cross-utility coordination opportunities",
        description=(
            "Processed mode serves precomputed public Duke and TECO opportunities. "
            "Explicit demo mode keeps the labeled demo scoring engine. "
            "A coordination score measures opportunity strength from available evidence. "
            "It is not a probability, expected savings, or a recommendation. "
            "PDF scraping is not implemented."
        ),
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.service = service
    app.include_router(router)
    return app


app = create_app()
