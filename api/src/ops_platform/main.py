from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ops_platform.api.routers.activity import router as activity_router
from ops_platform.api.routers.auth import router as auth_router
from ops_platform.api.routers.catalog import router as catalog_router
from ops_platform.api.routers.machines import router as machines_router
from ops_platform.api.routers.plants import router as plants_router
from ops_platform.api.routers.projects import router as projects_router


def create_app() -> FastAPI:
    app = FastAPI(title="Engineering Ops Platform API")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth_router)
    app.include_router(projects_router)
    app.include_router(plants_router)
    app.include_router(machines_router)
    app.include_router(catalog_router)
    app.include_router(activity_router)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
