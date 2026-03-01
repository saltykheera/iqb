

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware     

from routes.health import router as health_router
from routes.config import router as config_router
from routes.score import router as score_router
from routes.benchmark import router as benchmark_router

app = FastAPI(
    title="M-Lab IQB API",
    description="Calculate Internet Quality Barometer scores via HTTP.",
    version="0.1.0",
)

# enable CORS for all origins for testing purposes ; in production X
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(config_router)
app.include_router(score_router)
app.include_router(benchmark_router)
