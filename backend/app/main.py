from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.categories import router as categories_router
from app.api.estimates import router as estimates_router
from app.api.health import router as health_router
from app.api.items import router as items_router
from app.api.options import router as options_router
from app.core.config import settings

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(categories_router)
app.include_router(items_router)
app.include_router(options_router)
app.include_router(estimates_router)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": settings.app_name}