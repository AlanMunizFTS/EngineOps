from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ops_platform.api.routers.auth import router as auth_router


def create_app() -> FastAPI:
    app = FastAPI(title="Engineering Ops Platform API")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth_router)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
