from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import create_tables
from app.routers import auth as auth_router
from app.routers import buses as buses_router
from app.routers import routes as routes_router
from app.routers import stops as stops_router
from app.routers import public as public_router
from app.routers import ws as ws_router


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version=settings.app_version)

    # CORS setup - add your Netlify domain in config.cors_origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(auth_router.router)
    app.include_router(buses_router.router)
    app.include_router(routes_router.router)
    app.include_router(stops_router.router)
    app.include_router(public_router.router)
    app.include_router(ws_router.router)

    @app.get("/")
    async def root():
        return {"status": "ok", "name": settings.app_name, "version": settings.app_version}

    return app


app = create_app()


# Development only: auto-create tables
@app.on_event("startup")
async def on_startup():
    create_tables()
