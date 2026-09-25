from fastapi import APIRouter, HTTPException

from ..models.schemas import CandidateCreate, CandidateOut, PipelineColumn, PipelineOut, STAGE_LABELS
from ..services import pipeline as pipeline_svc

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


@router.get("", response_model=PipelineOut)
def get_pipeline():
    grouped = pipeline_svc.list_pipeline()
    order = [0, 1, 2, 3, -1]
    columns = []
    for stage in order:
        columns.append(
            PipelineColumn(
                stage=stage,
                label=STAGE_LABELS[stage],
                candidates=grouped.get(stage, []),
            )
        )
    return PipelineOut(columns=columns)


@router.post("/candidates", response_model=CandidateOut)
def create_candidate(body: CandidateCreate):
    try:
        return pipeline_svc.create_candidate(body.name, str(body.email), body.phone, body.position_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
