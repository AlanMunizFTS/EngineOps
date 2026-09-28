from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ops_platform.api.routers.activity import router as activity_router
from ops_platform.api.routers.admin import router as admin_router
from ops_platform.api.routers.auth import router as auth_router
from ops_platform.api.routers.export import router as export_router
from ops_platform.api.routers.file_tree import router as file_tree_router
from ops_platform.api.routers.issue_comments import router as issue_comments_router
from ops_platform.api.routers.issues import router as issues_router
from ops_platform.api.routers.kanban import router as kanban_router
from ops_platform.api.routers.labels import router as labels_router
from ops_platform.api.routers.piece_catalogs import router as piece_catalogs_router
from ops_platform.api.routers.pieces import router as pieces_router
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
    app.include_router(admin_router)
    app.include_router(projects_router)
    app.include_router(activity_router)
    app.include_router(labels_router)
    app.include_router(issues_router)
    app.include_router(issue_comments_router)
    app.include_router(kanban_router)
    app.include_router(piece_catalogs_router)
    app.include_router(pieces_router)
    app.include_router(file_tree_router)
    app.include_router(export_router)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
