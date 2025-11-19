from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

from app.api.routes import keywords, papers, subscribers
from app.db.session import init_db
from app.scheduler import start_scheduler, stop_scheduler

app = FastAPI(title="Daily Paper Insights API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    start_scheduler()


@app.on_event("shutdown")
def on_shutdown() -> None:
    stop_scheduler()


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(papers.router, prefix="/api")
app.include_router(keywords.router, prefix="/api")
app.include_router(subscribers.router, prefix="/api")

frontend_path = Path(__file__).resolve().parents[2] / "frontend"
if frontend_path.exists():
    app.mount(
        "/dashboard",
        StaticFiles(directory=frontend_path, html=True),
        name="dashboard",
    )


@app.get("/", include_in_schema=False)
def root_redirect() -> RedirectResponse:
    if frontend_path.exists():
        return RedirectResponse(url="/dashboard/")
    return RedirectResponse(url="/health")