from fastapi import FastAPI
from smind_common.logging import get_logger
from smind_config.loader import load_settings

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

    api = FastAPI(title="smind-family api", version="0.1.0")

    @api.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

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
