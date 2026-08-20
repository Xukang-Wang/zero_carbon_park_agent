"""
zero_carbon_park_agent 储能管理 API 路由
"""
from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Optional
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from schemas.water import APIResponse

router = APIRouter(prefix="/api/v1/storage", tags=["储能管理"])


class StorageOptimizeRequest(BaseModel):
    current_soc: float = 50.0
    electricity_price: Optional[list] = None
    target_soc: float = 80.0
    strategy: str = "peak_shaving"  # peak_shaving / price_arbitrage / backup


@router.get("/status")
async def get_storage_status():
    """获取储能系统当前状态"""
    from datetime import datetime
    from data.mock_data import get_mock_data

    try:
        md = get_mock_data()
        energy_status = md.get_energy_status()
        battery_data = energy_status["storage"]

        return APIResponse(data={
            "timestamp": datetime.now().isoformat(),
            "battery": {
                "id": battery_data["id"],
                "name": battery_data["name"],
                "type": "li_ion",
                "capacity_kwh": battery_data["capacity_kwh"],
                "rated_power_kw": 2500,
                "current_soc": battery_data["current_soc"],
                "available_energy_kwh": round(battery_data["capacity_kwh"] * battery_data["current_soc"] / 100, 1),
                "soc_min": 20,
                "soc_max": 90,
                "health_soh": 95.2,
                "temperature_c": 28.5,
                "cycle_count": 1200,
                "status": "online",
            },
            "operation": {
                "current_power_kw": battery_data.get("charge_power_kw", 0) - battery_data.get("discharge_power_kw", 0),
                "mode": battery_data["status"],
                "efficiency_round_trip": 0.92,
                "self_discharge_rate_per_day": 0.01,
            },
            "alerts": [
                {
                    "level": "info",
                    "message": "储能系统运行正常",
                    "timestamp": datetime.now().isoformat(),
                }
            ],
        })
    except Exception as e:
        return APIResponse(code=500, message=f"获取储能状态失败: {str(e)}")


@router.post("/optimize")
async def optimize_storage(request: StorageOptimizeRequest):
    """触发储能优化调度"""
    from datetime import datetime, timedelta
    from data.mock_data import get_mock_data

    try:
        md = get_mock_data()
        now = datetime.now()
        prices = request.electricity_price or md.get_grid_price()

        # 生成充放电策略
        schedule = []
        soc = request.current_soc
        capacity_kwh = 5000

        for i in range(24):
            hour = (now + timedelta(hours=i)).strftime("%H:00")
            price = prices[i] if i < len(prices) else 0.5

            if request.strategy == "price_arbitrage":
                # 价差套利：低价充电，高价放电
                if price < 0.4 and soc < 90:
                    action = "charge"
                    power = min(2500, (90 - soc) / 100 * capacity_kwh)
                elif price > 0.6 and soc > 20:
                    action = "discharge"
                    power = min(2500, (soc - 20) / 100 * capacity_kwh)
                else:
                    action = "idle"
                    power = 0
            else:
                # 削峰填谷：基于SOC和时段
                hour_int = int(hour.split(":")[0])
                if 6 <= hour_int <= 9:
                    action = "discharge" if soc > 25 else "idle"
                    power = min(2000, (soc - 20) / 100 * capacity_kwh) if action == "discharge" else 0
                elif 13 <= hour_int <= 17:
                    action = "discharge" if soc > 25 else "idle"
                    power = min(1500, (soc - 20) / 100 * capacity_kwh) if action == "discharge" else 0
                elif 0 <= hour_int <= 6:
                    action = "charge" if soc < 85 else "idle"
                    power = min(2500, (90 - soc) / 100 * capacity_kwh) if action == "charge" else 0
                elif 22 <= hour_int <= 23:
                    action = "charge" if soc < 85 else "idle"
                    power = min(2500, (90 - soc) / 100 * capacity_kwh) if action == "charge" else 0
                else:
                    action = "idle"
                    power = 0

            # 更新SOC
            if action == "charge":
                soc = min(90, soc + power * 0.92 / capacity_kwh * 100)
            elif action == "discharge":
                soc = max(20, soc - power / 0.92 / capacity_kwh * 100)

            schedule.append({
                "time": hour,
                "action": action,
                "power_kw": round(power, 1),
                "soc_after": round(soc, 1),
                "electricity_price": price,
                "estimated_cost_yuan": round(power * price if action == "charge" else -power * price, 2),
            })

        return APIResponse(data={
            "optimized_at": now.isoformat(),
            "strategy": request.strategy,
            "initial_soc": request.current_soc,
            "final_soc": round(soc, 1),
            "schedule": schedule,
            "summary": {
                "total_charge_kwh": round(sum(s["power_kw"] for s in schedule if s["action"] == "charge"), 1),
                "total_discharge_kwh": round(sum(s["power_kw"] for s in schedule if s["action"] == "discharge"), 1),
                "total_cost_yuan": round(sum(s["estimated_cost_yuan"] for s in schedule), 2),
                "arbitrage_revenue_yuan": round(
                    sum(-s["estimated_cost_yuan"] for s in schedule if s["action"] == "discharge"), 2
                ),
                "carbon_reduction_tco2": round(
                    sum(s["power_kw"] for s in schedule if s["action"] == "discharge") * 0.581 / 1000, 2
                ),
            },
        })
    except Exception as e:
        return APIResponse(code=500, message=f"储能优化失败: {str(e)}")


@router.get("/shared-storage/analysis")
async def analyze_shared_storage():
    """共享储能商业模式分析"""
    from datetime import datetime
    from data.mock_data import get_mock_data

    try:
        md = get_mock_data()
        data = md.get_shared_storage()
        data["generated_at"] = datetime.now().isoformat()
        return APIResponse(data=data)
    except Exception as e:
        return APIResponse(code=500, message=f"共享储能分析失败: {str(e)}")