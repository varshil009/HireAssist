from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db.database import init_db
from .routers import candidates, pipeline, positions, search

app = FastAPI(title="HireAssist API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(positions.router, prefix="/api")
app.include_router(pipeline.router, prefix="/api")
app.include_router(candidates.router, prefix="/api")
app.include_router(search.router, prefix="/api")
