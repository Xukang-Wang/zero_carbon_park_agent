from typing import Literal, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from backend.services import operations as service
from backend.services import operations_workflow as workflow

router = APIRouter(prefix="/api/v1/operations", tags=["园区分析工作台"])


class ScenarioRequest(BaseModel):
    day: Optional[str] = None
    strategy: Literal["balanced", "economic", "carbon"] = "balanced"
    pv_scale: float = Field(default=1, ge=.5, le=2, allow_inf_nan=False)
    load_scale: float = Field(default=1, ge=.5, le=1.5, allow_inf_nan=False)
    capacity_kwh: float = Field(default=5000, ge=0, le=20000, allow_inf_nan=False)


class RunRequest(BaseModel):
    day: Optional[str] = None
    strategy: Literal["balanced", "economic", "carbon"] = "balanced"


def checked(fn, *args):
    try:
        return fn(*args)
    except (ValueError, KeyError, TypeError) as exc:
        raise HTTPException(422, str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(503, "模拟数据尚未生成，请运行 scripts/generate_operations_data.py") from exc


@router.get("/overview")
def overview(day: Optional[str] = None, days: int = Query(1, ge=1, le=30)):
    return checked(service.overview, day, days)


@router.post("/scenario")
def scenario(body: ScenarioRequest):
    return checked(service.scenario, body.day, body.strategy, body.pv_scale, body.load_scale, body.capacity_kwh)


@router.get("/agents")
def agents():
    return {"nodes": workflow.AGENTS, "edges": [{"source": d, "target": n["id"]} for n in workflow.AGENTS for d in n["depends"]]}


@router.post("/runs")
def create_run(body: RunRequest):
    return checked(workflow.execute, body.day, body.strategy)


@router.get("/runs")
def runs():
    return workflow.history()


@router.get("/runs/{run_id}")
def run(run_id: str):
    result = workflow.get_run(run_id)
    if not result:
        raise HTTPException(404, "运行记录不存在")
    return result
