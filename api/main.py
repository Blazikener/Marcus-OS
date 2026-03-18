"""
Marcus Intelligence — FastAPI backend entry point.
Wraps scrape.py, crawler.py, and browsing_agent.py subprocess.
"""

import os
import time
import logging
from dotenv import load_dotenv
load_dotenv()  # Must run before api.routes imports (which import api.auth which reads env vars)

try:
    import sentry_sdk
    if dsn := os.getenv("SENTRY_DSN"):
        sentry_sdk.init(dsn=dsn, traces_sample_rate=0.1)
except ImportError:
    pass

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware

from api.limiter import limiter
from api.routes import generate, run, status, results, runs, analytics, settings, billing

logger = logging.getLogger("marcus.api")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

app = FastAPI(
    title="Marcus Intelligence API",
    version="1.0.0",
    description="AI-powered test automation backend",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ─── Request logging middleware ───────────────────────────────────────────────
class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception as exc:
            elapsed = round((time.perf_counter() - start) * 1000)
            logger.error(
                "UNHANDLED %s %s — %dms — %s: %s",
                request.method, request.url.path, elapsed,
                type(exc).__name__, exc,
            )
            raise
        elapsed = round((time.perf_counter() - start) * 1000)
        level = logging.WARNING if response.status_code >= 400 else logging.INFO
        logger.log(
            level,
            "%s %s %d %dms",
            request.method, request.url.path, response.status_code, elapsed,
        )
        return response


app.add_middleware(RequestLoggingMiddleware)

# ─── CORS ────────────────────────────────────────────────────────────────────
ALLOWED_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://localhost:3001",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in ALLOWED_ORIGINS],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
)

# ─── Routers ─────────────────────────────────────────────────────────────────
app.include_router(generate.router,  prefix="/api", tags=["generate"])
app.include_router(run.router,       prefix="/api", tags=["run"])
app.include_router(status.router,    prefix="/api", tags=["status"])
app.include_router(results.router,   prefix="/api", tags=["results"])
app.include_router(runs.router,      prefix="/api", tags=["runs"])
app.include_router(analytics.router, prefix="/api", tags=["analytics"])
app.include_router(settings.router,  prefix="/api", tags=["settings"])
app.include_router(billing.router,   prefix="/api", tags=["billing"])


@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok", "service": "marcus-api"}

