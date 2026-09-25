from fastapi import APIRouter

from ..db.database import get_connection
from ..models.schemas import PositionOut

router = APIRouter(prefix="/positions", tags=["positions"])


@router.get("", response_model=list[PositionOut])
def list_positions():
    with get_connection() as conn:
        rows = conn.execute("SELECT id, position_code, title FROM positions ORDER BY id").fetchall()
    return [PositionOut(id=r["id"], position_code=r["position_code"], title=r["title"]) for r in rows]
