"""
zero_carbon_park_agent 能源管理 API 路由
"""
from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Optional
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from schemas.water import APIResponse

router = APIRouter(prefix="/api/v1/energy", tags=["能源管理"])


class EnergyOptimizeRequest(BaseModel):
    pv_forecast: Optional[list] = None
    wind_forecast: Optional[list] = None
    load_forecast: Optional[list] = None
    storage_soc: float = 50.0
    grid_price: Optional[list] = None


@router.get("/dispatch/status")
async def get_energy_status():
    """获取当前能源调度状态"""
    from datetime import datetime
    from data.mock_data import get_mock_data

    try:
        md = get_mock_data()
        data = md.get_energy_status()
        data["generated_at"] = datetime.now().isoformat()
        return APIResponse(data=data)
    except Exception as e:
        return APIResponse(code=500, message=f"获取能源调度状态失败: {str(e)}")


@router.post("/dispatch/optimize")
async def optimize_energy_dispatch(request: EnergyOptimizeRequest):
    """触发多能互补调度优化（基于静态数据）"""
    from datetime import datetime, timedelta
    from data.mock_data import get_mock_data

    try:
        md = get_mock_data()
        pv_forecast_raw = md.get_pv_forecast()
        load_forecast_raw = md.get_load_forecast()

        pv_forecast = request.pv_forecast or [f["power_kw"] for f in pv_forecast_raw]
        load_forecast = request.load_forecast or load_forecast_raw

        now = datetime.now()
        schedule = []
        for i in range(24):
            hour = (now + timedelta(hours=i)).strftime("%H:00")
            pv = pv_forecast[i] if i < len(pv_forecast) else 3000
            load = load_forecast[i] if i < len(load_forecast) else 5000
            net = pv - load
            if net > 0:
                charge = min(net * 0.8, 2500)
                discharge = 0
                grid_power = 0
            else:
                discharge = min(abs(net) * 0.6, 2500)
                grid_power = round(abs(net) - discharge, 1)
                charge = 0

            schedule.append({
                "time": hour,
                "pv_power_kw": round(pv, 1),
                "load_power_kw": round(load, 1),
                "charge_power_kw": round(charge, 1),
                "discharge_power_kw": round(discharge, 1),
                "grid_power_kw": round(grid_power, 1),
                "storage_soc": round(request.storage_soc + sum(
                    (s["charge_power_kw"] * 0.9 - s["discharge_power_kw"] / 0.9) / 5000
                    for s in schedule
                ), 1),
            })

        return APIResponse(data={
            "optimized_at": now.isoformat(),
            "horizon_hours": 24,
            "schedule": schedule,
            "summary": {
                "total_pv_generation_kwh": round(sum(s["pv_power_kw"] for s in schedule), 1),
                "total_load_kwh": round(sum(s["load_power_kw"] for s in schedule), 1),
                "total_grid_power_kwh": round(sum(s["grid_power_kw"] for s in schedule), 1),
                "renewable_ratio": round(
                    1 - sum(s["grid_power_kw"] for s in schedule) / sum(s["load_power_kw"] for s in schedule),
                    2
                ),
                "peak_shaving_times": sum(1 for s in schedule if s["discharge_power_kw"] > 0),
                "valley_filling_times": sum(1 for s in schedule if s["charge_power_kw"] > 0),
            },
        })
    except Exception as e:
        return APIResponse(code=500, message=f"调度优化失败: {str(e)}")


@router.get("/power-forecast")
async def get_power_forecast(source: str = Query("pv", description="能源类型: pv/wind")):
    """获取新能源功率预测"""
    from datetime import datetime
    from data.mock_data import get_mock_data

    try:
        md = get_mock_data()
        now = datetime.now()
        if source == "pv":
            forecast = md.get_pv_forecast()
        elif source == "wind":
            forecast = md.get_wind_forecast()
        else:
            return APIResponse(code=400, message=f"不支持的能源类型: {source}，请使用 pv 或 wind")

        return APIResponse(data={
            "source": source,
            "predicted_at": now.isoformat(),
            "horizon_hours": 24,
            "forecast": forecast,
            "total_energy_kwh": round(sum(f["power_kw"] for f in forecast), 1),
            "model_version": "simulation_v1",
        })
    except Exception as e:
        return APIResponse(code=500, message=f"功率预测失败: {str(e)}")


@router.get("/green-power/trace")
async def trace_green_power(entity_id: str = Query(..., description="实体ID")):
    """绿电溯源"""
    from graph.graph_builder import get_knowledge_graph

    try:
        kg = get_knowledge_graph()
        entity = kg.get_entity_info(entity_id)

        if entity is None:
            return APIResponse(code=404, message=f"实体 {entity_id} 不存在")

        upstream = kg.trace_energy(entity_id, "upstream")
        downstream = kg.trace_energy(entity_id, "downstream")
        carbon = kg.calculate_carbon_footprint()

        return APIResponse(data={
            "entity_id": entity_id,
            "entity": entity,
            "upstream_trace": upstream,
            "downstream_trace": downstream,
            "green_power_ratio": round(carbon.get("renewable_ratio", 0.41), 2),
            "carbon_offset_tco2_per_h": carbon.get("carbon_offset_tco2_per_h", 0),
            "certification": {
                "green_certificate_eligible": carbon.get("renewable_ratio", 0) > 0.3,
                "estimated_annual_green_kwh": round(carbon.get("renewable_power_kw", 3000) * 8760, 1),
            },
        })
    except Exception as e:
        return APIResponse(code=500, message=f"绿电溯源失败: {str(e)}")