from fastapi import APIRouter, Query

from ..models.schemas import SearchRequest, SearchResponse, SuggestOut
from ..services.search.ai_chain import run_ai_search
from ..services.search.fuzzy import empty_suggest_message, fuzzy_suggest

router = APIRouter(prefix="/search", tags=["search"])


@router.get("/suggest", response_model=SuggestOut)
def suggest(q: str = Query("", max_length=200)):
    query = q.strip()
    if not query:
        return SuggestOut(query="", suggestions=[], empty_message=None)
    suggestions = fuzzy_suggest(query)
    empty_message = empty_suggest_message(query) if not suggestions else None
    return SuggestOut(query=query, suggestions=suggestions, empty_message=empty_message)


@router.post("", response_model=SearchResponse)
def search(body: SearchRequest):
    return run_ai_search(body.query)
