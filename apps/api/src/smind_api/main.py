import contextlib

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from smind_common.errors import SmindError
from smind_common.logging import get_logger
from smind_config.loader import load_settings

from smind_api.app_support import (
    error_code,
    health_report,
    map_exception_to_status,
    run_startup_checks,
)
from smind_api.routes.auth import router as auth_router
from smind_api.routes.ingestion import router as ingestion_router
from smind_api.routes.management import router as management_router
from smind_api.routes.me import router as me_router
from smind_api.routes.ops import router as ops_router
from smind_api.routes.search import router as search_router
from smind_api.routes.team import router as team_router
from smind_api.routes.workflow_config import router as workflow_config_router


def create_app() -> FastAPI:
    settings = load_settings()
    logger = get_logger("smind.api")
    logger.info("booting api for env=%s", settings.app_env)

    @contextlib.asynccontextmanager
    async def lifespan(api: FastAPI):
        # P2-01: apply migrations + self-check connectivity at startup.
        # Fail-loud: any failure raises here and aborts boot rather than
        # starting silently against an unusable database.
        run_startup_checks(settings.core_db_path, settings.vec_db_path)
        logger.info("startup migrations + connectivity self-check ok")
        yield
        # No global connection state to tear down: request-scoped connections
        # are owned by the generator dependencies (F2-01).

    api = FastAPI(title="smind-family api", version="0.1.0", lifespan=lifespan)

    # P2-02: CORS. Origins come from settings if configured; conservative
    # default for now. TODO(F7): tighten allow_origins / allow_credentials
    # before production (see FF-F2-conn-wiring.md §9.1).
    cors_origins = getattr(settings, "cors_origins", None) or ["*"]
    api.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    )

    # P2-03: global business-exception handler -> 4xx (not 500). Prefer
    # SmindError.code / type branches over fragile exact-string matching
    # (see app_support.map_exception_to_status; AP §7.2 anti-pattern 4).
    def _business_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        status_code = map_exception_to_status(exc)
        return JSONResponse(
            status_code=status_code,
            content={"detail": str(exc), "code": error_code(exc)},
        )

    api.add_exception_handler(SmindError, _business_exception_handler)
    api.add_exception_handler(ValueError, _business_exception_handler)

    @api.get("/healthz")
    def healthz() -> JSONResponse:
        # P2-04: real probe of core + vec (open -> SELECT 1 / vec table check
        # -> close via contextlib.closing). 503 + machine-readable reason on
        # any failure; never a silent static ok.
        status_code, body = health_report(
            settings.core_db_path, settings.vec_db_path
        )
        return JSONResponse(status_code=status_code, content=body)

    api.include_router(auth_router)
    api.include_router(team_router)
    api.include_router(me_router)
    api.include_router(workflow_config_router)
    api.include_router(ingestion_router)
    api.include_router(management_router)
    api.include_router(search_router)
    api.include_router(ops_router)

    return api


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8010)
