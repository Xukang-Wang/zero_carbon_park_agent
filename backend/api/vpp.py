"""
zero_carbon_park_agent 虚拟电厂 API 路由
"""
from fastapi import APIRouter, Query
from pydantic import BaseModel
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from schemas.water import APIResponse

router = APIRouter(prefix="/api/v1/vpp", tags=["虚拟电厂"])


class VPPBidRequest(BaseModel):
    market_type: str = "spot"  # spot/ancillary/capacity
    volume_mwh: float = 10.0
    price_strategy: str = "competitive"  # competitive / aggressive / conservative


@router.get("/status")
async def get_vpp_status():
    """获取虚拟电厂聚合状态"""
    from datetime import datetime
    from graph.graph_builder import get_knowledge_graph
    from data.mock_data import get_mock_data

    try:
        kg = get_knowledge_graph()
        md = get_mock_data()
        load_entities = kg.get_all_entities_by_type("EnergyLoad")
        energy_status = md.get_energy_status()

        return APIResponse(data={
            "timestamp": datetime.now().isoformat(),
            "vpp_id": "VPP-ZC-001",
            "aggregated_capacity": {
                "total_capacity_mw": 10.5,
                "flexible_load_mw": 4.2,
                "storage_mw": energy_status["storage"]["capacity_kwh"] / 1000,
                "pv_mw": energy_status["pv_station"]["rated_capacity_kw"] / 1000,
                "wind_mw": 0.0,
            },
            "current_operation": {
                "total_power_mw": 6.5,
                "renewable_ratio": 0.48,
                "dispatchable_power_mw": 3.8,
                "status": "online",
            },
            "aggregated_resources": len(load_entities) + 3,
            "market_participation": {
                "spot_market": "active",
                "ancillary_service": "registered",
                "demand_response": "active",
                "capacity_market": "pending",
            },
        })
    except Exception as e:
        return APIResponse(code=500, message=f"获取VPP状态失败: {str(e)}")


@router.post("/bid")
async def submit_vpp_bid(request: VPPBidRequest):
    """提交VPP市场报价（基于静态定价策略）"""
    from datetime import datetime, timedelta

    try:
        now = datetime.now()

        # 静态定价策略
        price_strategies = {
            "competitive": {"spot_base": 0.45, "multiplier": 1.0},
            "aggressive": {"spot_base": 0.40, "multiplier": 0.9},
            "conservative": {"spot_base": 0.50, "multiplier": 1.1},
        }
        strategy = price_strategies.get(request.price_strategy, price_strategies["competitive"])

        if request.market_type == "spot":
            bid_price = round(strategy["spot_base"] * strategy["multiplier"], 2)
            bid_result = {
                "bid_id": f"BID_{now.strftime('%Y%m%d%H%M%S')}",
                "market_type": request.market_type,
                "bid_price_yuan_per_kwh": bid_price,
                "volume_mwh": request.volume_mwh,
                "bid_time": now.isoformat(),
                "delivery_period": {
                    "start": (now + timedelta(hours=1)).isoformat(),
                    "end": (now + timedelta(hours=2)).isoformat(),
                },
                "expected_revenue_yuan": round(bid_price * request.volume_mwh * 1000, 2),
                "win_probability": round(0.7 * strategy["multiplier"], 2),
                "status": "submitted",
            }
        elif request.market_type == "ancillary":
            bid_result = {
                "bid_id": f"BID_{now.strftime('%Y%m%d%H%M%S')}",
                "market_type": request.market_type,
                "service_type": "frequency_regulation",
                "capacity_mw": request.volume_mwh,
                "bid_price_yuan_per_mw": 60.00,
                "bid_time": now.isoformat(),
                "response_time_ms": 200,
                "duration_hours": 1,
                "expected_revenue_yuan": round(request.volume_mwh * 80.0, 2),
                "status": "submitted",
            }
        elif request.market_type == "capacity":
            bid_result = {
                "bid_id": f"BID_{now.strftime('%Y%m%d%H%M%S')}",
                "market_type": request.market_type,
                "capacity_mw": request.volume_mwh,
                "bid_price_yuan_per_kw_year": 280.00,
                "bid_time": now.isoformat(),
                "commitment_period": "2026-01-01 to 2026-12-31",
                "expected_annual_revenue_yuan": round(request.volume_mwh * 1000 * 300, 2),
                "status": "submitted",
            }
        else:
            return APIResponse(code=400, message=f"不支持的市场类型: {request.market_type}，请使用 spot/ancillary/capacity")

        return APIResponse(data=bid_result)
    except Exception as e:
        return APIResponse(code=500, message=f"VPP报价提交失败: {str(e)}")


@router.get("/resources")
async def get_vpp_resources():
    """获取可聚合资源列表"""
    from graph.graph_builder import get_knowledge_graph
    from data.mock_data import get_mock_data

    try:
        kg = get_knowledge_graph()
        md = get_mock_data()
        load_entities = kg.get_all_entities_by_type("EnergyLoad")
        energy_status = md.get_energy_status()

        resources = [
            {
                "id": "PV-001", "name": "1号光伏电站", "type": "renewable_generation",
                "capacity_mw": energy_status["pv_station"]["rated_capacity_kw"] / 1000,
                "controllable": True, "ramp_rate_mw_per_min": 2.5,
                "min_runtime_hours": 0, "status": "online",
            },
            {
                "id": "BAT-001", "name": "1号锂电池储能系统", "type": "energy_storage",
                "capacity_mw": energy_status["storage"]["capacity_kwh"] / 1000,
                "controllable": True, "ramp_rate_mw_per_min": 5.0,
                "min_runtime_hours": 0, "status": "online",
                "soc": energy_status["storage"]["current_soc"],
            },
            {
                "id": "GRID-001", "name": "市电馈线", "type": "grid_connection",
                "capacity_mw": 10.0, "controllable": False,
                "ramp_rate_mw_per_min": 5.0, "min_runtime_hours": 0, "status": "online",
            },
        ]

        for entity in load_entities:
            resources.append({
                "id": entity.get("id", entity) if isinstance(entity, dict) else entity,
                "name": entity.get("name", "未知负荷") if isinstance(entity, dict) else entity,
                "type": "flexible_load",
                "capacity_mw": round(entity.get("rated_power_kw", 1000) / 1000, 1) if isinstance(entity, dict) else 1.0,
                "controllable": True, "ramp_rate_mw_per_min": 0.3,
                "min_runtime_hours": 1, "status": "online",
            })

        return APIResponse(data={
            "total_resources": len(resources),
            "total_capacity_mw": round(sum(r["capacity_mw"] for r in resources), 1),
            "flexible_capacity_mw": round(
                sum(r["capacity_mw"] for r in resources if r["controllable"]), 1
            ),
            "resources": resources,
        })
    except Exception as e:
        return APIResponse(code=500, message=f"获取VPP资源列表失败: {str(e)}")