import sys
from pathlib import Path

# Ensure satquery-ai root is in sys.path regardless of where uvicorn is launched
_satquery_ai_root = Path(__file__).resolve().parent.parent.parent
if str(_satquery_ai_root) not in sys.path:
    sys.path.insert(0, str(_satquery_ai_root))

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.config import settings
from backend.app.api.routes import router
from backend.app.exceptions import SatQueryException
from backend.app.logging import logger
from backend.app.db.session import init_db_engine, dispose_db_engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Application startup: initialize connection pool
    logger.info("Initializing SatQuery AI application lifecycle...")
    await init_db_engine()
    yield
    # Application shutdown: cleanly dispose connection pool
    logger.info("Shutting down SatQuery AI application lifecycle...")
    await dispose_db_engine()


app = FastAPI(
    title=settings.app.name,
    version=settings.app.version,
    description="Agentic Remote-Sensing Intelligence Platform for Single-Image VQA, Grounding, Bi-temporal Change, and Optical-SAR Cross-Modal Analysis.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.app.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


from fastapi.exceptions import RequestValidationError, ResponseValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

@app.exception_handler(SatQueryException)
async def satquery_exception_handler(request: Request, exc: SatQueryException):
    logger.error(f"SatQuery exception [{exc.code}]: {exc.message}")
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict()
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    logger.warning(f"HTTP exception [{exc.status_code}] on {request.url.path}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": "HTTP_ERROR",
                "message": exc.detail if isinstance(exc.detail, str) else str(exc.detail),
                "details": {"status_code": exc.status_code},
                "job_id": None
            }
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(f"Request validation error on {request.url.path}: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "INVALID_REQUEST",
                "message": "Invalid request parameters or payload.",
                "details": exc.errors(),
                "job_id": None
            }
        }
    )


@app.exception_handler(ResponseValidationError)
async def response_validation_exception_handler(request: Request, exc: ResponseValidationError):
    logger.error(f"Response serialization error on {request.url.path}: {exc.errors()}")
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "RESPONSE_SERIALIZATION_ERROR",
                "message": "Internal response schema serialization mismatch.",
                "details": str(exc.errors()),
                "job_id": None
            }
        }
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled exception on {request.method} {request.url.path}: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": str(exc) if settings.app.debug else "An unexpected server error occurred.",
                "details": {},
                "job_id": None
            }
        }
    )


# Attach API router
app.include_router(router)

# Frontend alias routes (Part 38: /jobs/{job_id}/status, /results, /trace, /video/{job_id}/status)
alias_router = APIRouter(include_in_schema=False)

@alias_router.get("/jobs/{job_id}/status")
@alias_router.get("/jobs/{job_id}")
async def alias_job_status(job_id: str):
    from backend.app.api.routes import get_job_status
    from backend.app.db.session import get_session_maker
    session_factory = get_session_maker()
    async with session_factory() as session:
        return await get_job_status(job_id=job_id, db=session)

@alias_router.get("/results/{request_id}")
async def alias_results(request_id: str):
    from backend.app.api.routes import get_job_results
    from backend.app.db.session import get_session_maker
    session_factory = get_session_maker()
    async with session_factory() as session:
        return await get_job_results(request_id=request_id, db=session)

@alias_router.get("/trace/{job_id}")
async def alias_trace(job_id: str):
    from backend.app.api.routes import get_job_trace
    from backend.app.db.session import get_session_maker
    session_factory = get_session_maker()
    async with session_factory() as session:
        return await get_job_trace(job_id=job_id, db=session)

@alias_router.get("/video/{job_id}/status")
@alias_router.get("/video/{job_id}")
async def alias_video_status(job_id: str):
    from backend.app.api.routes import get_video_analysis_result
    from backend.app.db.session import get_session_maker
    session_factory = get_session_maker()
    async with session_factory() as session:
        return await get_video_analysis_result(job_id=job_id, db=session)

app.include_router(alias_router)



@app.get("/")
async def root():
    return {
        "app": settings.app.name,
        "version": settings.app.version,
        "status": "online",
        "docs": "/docs",
        "health": "/api/health",
        "models": "/api/models"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.app.main:app",
        host=settings.app.host,
        port=settings.app.port,
        reload=settings.app.debug
    )
