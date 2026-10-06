from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.core.config import get_settings
from app.core.exceptions import SmartOpsError
from app.core.logging import configure_logging
from app.db.base import Base
from app.db.session import engine
from app.services.llm import build_llm_service
from app.services.files import FileAccessError
from app.tools.registry import build_tool_registry

settings = get_settings()
configure_logging(settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.state.llm = build_llm_service(settings)
app.state.tools = build_tool_registry()
app.state.settings = settings
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    length = request.headers.get("content-length")
    if length and int(length) > settings.max_request_bytes:
        return JSONResponse(status_code=413, content={"detail": "Request body too large"})
    return await call_next(request)


@app.exception_handler(SmartOpsError)
async def handle_smartops_error(_: Request, exc: SmartOpsError):
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.exception_handler(FileAccessError)
async def handle_file_access_error(_: Request, exc: FileAccessError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


app.include_router(router)


@app.get("/", include_in_schema=False)
def web_app() -> FileResponse:
    return FileResponse("app/static/index.html")

