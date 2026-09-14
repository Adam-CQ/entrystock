from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel

from analytics import PACKAGE_VERSION

SERVICE_VERSION = PACKAGE_VERSION


class HealthResponse(BaseModel):
    status: Literal["ok"]


app = FastAPI(
    title="entrystock analytical service",
    version=SERVICE_VERSION,
    description="Typed HTTP boundary for reusable investor-analysis calculations.",
)


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    return HealthResponse(status="ok")
