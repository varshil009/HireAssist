from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


STAGE_LABELS = {
    -1: "Rejected",
    0: "Applied",
    1: "Screening",
    2: "Offered",
    3: "Hired",
}


class PositionOut(BaseModel):
    id: int
    position_code: str
    title: str


class CandidateCreate(BaseModel):
    name: str = Field(min_length=1)
    email: EmailStr
    phone: str | None = None
    position_id: int


class CandidateOut(BaseModel):
    id: int
    name: str
    email: str
    phone: str | None
    position_id: int
    position_code: str | None = None
    position_title: str | None = None
    current_stage: int
    stage_label: str
    rejected_at: str | None
    offered_flag: int
    hired_flag: int
    entered_applied_at: str
    entered_screening_at: str | None
    entered_offered_at: str | None
    entered_hired_at: str | None
    days_in_current_stage: float | None = None


class StageEventOut(BaseModel):
    id: int
    candidate_id: int
    from_stage: int
    to_stage: int
    from_label: str
    to_label: str
    occurred_at: str


class PipelineColumn(BaseModel):
    stage: int
    label: str
    candidates: list[CandidateOut]


class PipelineOut(BaseModel):
    columns: list[PipelineColumn]


class SuggestItem(BaseModel):
    id: int
    name: str
    current_stage: int
    stage_label: str
    position_title: str
    position_code: str
    score: float


class SuggestOut(BaseModel):
    query: str
    suggestions: list[SuggestItem]
    empty_message: str | None = None


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)


class SearchResponse(BaseModel):
    ok: bool
    message: str
    query: str
    columns: list[str]
    rows: list[list[str | int | float | None]]
    fuzzy_suggestions: list[SuggestItem] = []
