from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from services.analysis_service import AnalysisService

router = APIRouter(prefix="/api/v1", tags=["codebase-intelligence"])


class CloneRequest(BaseModel):
    repository_url: str
    destination: Path
    branch: Optional[str] = None


class ChangeRequest(BaseModel):
    repository_path: Path
    changed_symbols: list[str] = Field(default_factory=list)
    base_revision: Optional[str] = None


def get_service() -> AnalysisService:
    return AnalysisService(Path(".codebase-intelligence/index.db"))


@router.post("/repositories/clone-index")
def clone_and_index(payload: CloneRequest):
    service = get_service()

    try:
        return service.clone_and_index(
            payload.repository_url,
            payload.destination,
            payload.branch,
        )
    finally:
        service.close()


@router.post("/repositories/index")
def index_local_repository(repository_path: Path):
    service = get_service()

    try:
        if not repository_path.exists():
            raise HTTPException(status_code=404, detail="Repository path not found")

        return service.index_local_repository(repository_path)
    finally:
        service.close()


@router.get("/symbols")
def find_symbols(
    repository_path: Path,
    query: str = Query(..., min_length=1),
):
    service = get_service()

    try:
        return {"results": service.find_symbol(repository_path, query)}
    finally:
        service.close()


@router.get("/symbols/{symbol_id:path}/details")
def symbol_details(repository_path: Path, symbol_id: str):
    service = get_service()

    try:
        return service.symbol_details(repository_path, symbol_id)
    finally:
        service.close()


@router.post("/analysis/change")
def analyze_change(payload: ChangeRequest):
    service = get_service()

    try:
        return service.analyze_change(
            payload.repository_path,
            payload.changed_symbols,
            payload.base_revision,
        )
    finally:
        service.close()


@router.post("/analysis/dead-code")
def detect_dead_code(repository_path: Path):
    service = get_service()

    try:
        return service.detect_dead_code(repository_path)
    finally:
        service.close()


@router.get("/graph/paths")
def graph_paths(
    repository_path: Path,
    source: str = Query(..., min_length=1),
    target: str = Query(..., min_length=1),
    cutoff: int = Query(5, ge=1),
):
    service = get_service()

    try:
        return service.graph_paths(repository_path, source, target, cutoff=cutoff)
    finally:
        service.close()


@router.get("/graph/call-chain")
def graph_call_chain(
    repository_path: Path,
    source: str = Query(..., min_length=1),
    target: str = Query(..., min_length=1),
    cutoff: int = Query(5, ge=1),
):
    service = get_service()

    try:
        return service.graph_call_chain(repository_path, source, target, cutoff=cutoff)
    finally:
        service.close()


@router.get("/graph/neighbors")
def graph_neighbors(repository_path: Path, node_id: str = Query(..., min_length=1)):
    service = get_service()

    try:
        return service.graph_neighbors(repository_path, node_id)
    finally:
        service.close()
