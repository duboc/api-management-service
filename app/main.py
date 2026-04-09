import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from google.api_core import exceptions as gcp_exceptions

from app.config import settings
from app.routers import api_keys, dashboard, gateway, proxy
from app.services.api_keys_service import ApiKeysService
from app.services.gateway_service import GatewayService
from app.services.gcloud_runner import GcloudError
from app.services.proxy_service import ProxyService

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "Starting API Gateway Manager for project: %s",
        settings.gcp_project_id,
    )
    app.state.gateway_service = GatewayService(settings.gcp_project_id)
    app.state.proxy_service = ProxyService(
        settings.gcp_project_id, settings.vertex_ai_region
    )
    app.state.api_keys_service = ApiKeysService(settings.gcp_project_id)
    app.state.gateway_managed_service = ""

    # Try to fetch managed service from existing gateway API
    if settings.gateway_api_id:
        try:
            api_info = await app.state.gateway_service.get_api(
                settings.gateway_api_id
            )
            app.state.gateway_managed_service = api_info.managed_service
            logger.info(
                "Gateway managed service: %s",
                app.state.gateway_managed_service,
            )
        except Exception:
            logger.info(
                "Could not fetch managed service for %s",
                settings.gateway_api_id,
            )

    yield
    logger.info("Shutting down API Gateway Manager")


app = FastAPI(
    title="API Gateway Manager",
    description="Manage API Gateway + Cloud Run proxy for Vertex AI predictions",
    version="0.2.0",
    lifespan=lifespan,
)

# --- Exception handlers ---


@app.exception_handler(GcloudError)
async def gcloud_error_handler(request, exc):
    return JSONResponse(status_code=502, content={"detail": str(exc)})


@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(gcp_exceptions.NotFound)
async def not_found_handler(request, exc):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(gcp_exceptions.PermissionDenied)
async def permission_denied_handler(request, exc):
    return JSONResponse(status_code=403, content={"detail": str(exc)})


@app.exception_handler(gcp_exceptions.InvalidArgument)
async def invalid_argument_handler(request, exc):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(gcp_exceptions.AlreadyExists)
async def already_exists_handler(request, exc):
    return JSONResponse(status_code=409, content={"detail": str(exc)})


# --- Routers ---

app.include_router(dashboard.router)
app.include_router(gateway.router)
app.include_router(proxy.router)
app.include_router(api_keys.router)

# --- Static files ---

static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
async def serve_index():
    return FileResponse(os.path.join(static_dir, "index.html"))
