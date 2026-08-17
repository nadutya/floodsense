from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .model import compare, load_network, simulate

app = FastAPI(title="FloodSense Scenario API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_methods=["*"], allow_headers=["*"])


class RainSegment(BaseModel):
    minute: int = Field(ge=0)
    rainfall_mmh: float = Field(ge=0, le=120)

class Intervention(BaseModel):
    drain_id: str
    minute: int = Field(ge=0)


class ScenarioRequest(BaseModel):
    rainfall_mmh: float = Field(38, ge=0, le=120)
    duration_minutes: int = Field(90, ge=1)
    rainfall_schedule: Optional[List[RainSegment]] = None
    interventions: Optional[List[Intervention]] = None
    cleaned_drain_id: Optional[str] = None
    cleaning_minute: int = Field(18, ge=0)


class CompareRequest(BaseModel):
    rainfall_mmh: float = Field(38, ge=0, le=120)
    duration_minutes: int = Field(90, ge=1)
    rainfall_schedule: Optional[List[RainSegment]] = None
    interventions: Optional[List[Intervention]] = None
    drain_id: str
    cleaning_minute: int = Field(18, ge=0)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/network")
def network():
    return load_network()


@app.post("/api/scenarios/run")
def run_scenario(request: ScenarioRequest):
    try:
        return simulate(**request.dict())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/scenarios/compare")
def compare_scenarios(request: CompareRequest):
    try:
        schedule = [item.dict() for item in request.rainfall_schedule] if request.rainfall_schedule else None
        interventions = [item.dict() for item in request.interventions] if request.interventions else None
        return compare(request.rainfall_mmh, request.drain_id, request.cleaning_minute, request.duration_minutes, schedule, interventions)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
