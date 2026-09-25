from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import Response

from ..models.schemas import CandidateOut, StageEventOut
from ..services import pipeline as pipeline_svc

router = APIRouter(prefix="/candidates", tags=["candidates"])


@router.get("/{candidate_id}", response_model=CandidateOut)
def get_candidate(candidate_id: int):
    cand = pipeline_svc.get_candidate(candidate_id)
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return cand


@router.get("/{candidate_id}/timeline", response_model=list[StageEventOut])
def get_timeline(candidate_id: int):
    if not pipeline_svc.get_candidate(candidate_id):
        raise HTTPException(status_code=404, detail="Candidate not found")
    return pipeline_svc.get_timeline(candidate_id)


@router.post("/{candidate_id}/advance", response_model=CandidateOut)
def advance(candidate_id: int):
    try:
        return pipeline_svc.advance_candidate(candidate_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/{candidate_id}/reject", response_model=CandidateOut)
def reject(candidate_id: int):
    try:
        return pipeline_svc.reject_candidate(candidate_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.put("/{candidate_id}/resume")
async def upload_resume(candidate_id: int, file: UploadFile = File(...)):
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    try:
        pipeline_svc.upsert_resume(candidate_id, data, file.filename)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return {"ok": True, "filename": file.filename}


@router.get("/{candidate_id}/resume")
def download_resume(candidate_id: int):
    res = pipeline_svc.get_resume(candidate_id)
    if not res:
        raise HTTPException(status_code=404, detail="Resume not found")
    blob, filename = res
    media = "application/octet-stream"
    if filename and filename.lower().endswith(".pdf"):
        media = "application/pdf"
    return Response(
        content=blob,
        media_type=media,
        headers={"Content-Disposition": f'inline; filename="{filename or "resume"}"'},
    )
