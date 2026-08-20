"""
园区综合监控 API - 实时监测、节点管理、调度优化
所有数据从静态 JSON 文件加载，替换为真实数据时只需替换 JSON 文件
"""
from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from schemas.water import APIResponse

router = APIRouter(prefix="/api/v1/park", tags=["园区监控"])


class DispatchOptimizeRequest(BaseModel):
    strategy: str = "balanced"


@router.get("/snapshot")
async def get_park_snapshot():
    """获取园区完整状态快照（从静态JSON加载）"""
    try:
        from data.mock_data import get_mock_data
        data = get_mock_data().get_park_snapshot()
        data["timestamp"] = datetime.now().isoformat()
        return APIResponse(data=data)
    except Exception as e:
        return APIResponse(code=500, message=f"获取园区快照失败: {str(e)}")


@router.get("/nodes")
async def get_all_nodes():
    """获取园区所有节点列表（从静态JSON加载）"""
    try:
        from data.mock_data import get_mock_data
        return APIResponse(data=get_mock_data().get_park_nodes())
    except Exception as e:
        return APIResponse(code=500, message=f"获取节点列表失败: {str(e)}")


@router.get("/alerts")
async def get_park_alerts(limit: int = Query(20, ge=1, le=100)):
    """获取园区告警列表"""
    try:
        from services.monitoring_service import get_monitoring_service
        monitor = get_monitoring_service()
        summary = monitor.get_node_status_summary()
        summary["alerts"] = summary.get("active_alerts", [])[:limit]
        return APIResponse(data=summary)
    except Exception as e:
        return APIResponse(code=500, message=f"获取告警列表失败: {str(e)}")


@router.post("/alerts/{node_id}/acknowledge")
async def acknowledge_alert(node_id: str):
    """确认告警"""
    try:
        from services.monitoring_service import get_monitoring_service
        monitor = get_monitoring_service()
        success = monitor.acknowledge_alert(node_id, "")
        return APIResponse(data={"acknowledged": success})
    except Exception as e:
        return APIResponse(code=500, message=f"确认告警失败: {str(e)}")


@router.post("/dispatch/optimize")
async def optimize_dispatch(request: DispatchOptimizeRequest):
    """执行调度优化（源网荷储协同）"""
    try:
        from services.park_service import get_park_service
        service = get_park_service()
        result = service.get_dispatch_optimization(request.strategy)
        return APIResponse(data=result)
    except Exception as e:
        return APIResponse(code=500, message=f"调度优化失败: {str(e)}")


@router.get("/dispatch/strategies")
async def get_dispatch_strategies():
    """获取可用调度策略列表"""
    return APIResponse(data={
        "strategies": [
            {"id": "economic", "name": "经济最优", "description": "最小化用电成本，优先峰谷套利"},
            {"id": "low_carbon", "name": "低碳优先", "description": "最大化可再生能源消纳，最小化碳排放"},
            {"id": "balanced", "name": "平衡模式", "description": "兼顾经济性与低碳，综合最优"},
            {"id": "safety_first", "name": "安全优先", "description": "优先保障供能安全，最小化失负荷风险"},
            {"id": "peak_shaving", "name": "削峰填谷", "description": "利用储能平抑负荷峰谷差"},
            {"id": "price_arbitrage", "name": "价差套利", "description": "利用峰谷电价差获取收益"},
        ],
    })


@router.get("/power-flow")
async def get_power_flow():
    """获取园区功率流向（从静态JSON加载）"""
    try:
        from data.mock_data import get_mock_data
        return APIResponse(data=get_mock_data().get_park_power_flow())
    except Exception as e:
        return APIResponse(code=500, message=f"获取功率流向失败: {str(e)}")


@router.get("/vpp/aggregation")
async def get_vpp_aggregation():
    """获取虚拟电厂聚合状态（从静态JSON加载）"""
    try:
        from services.park_service import get_park_service
        service = get_park_service()
        return APIResponse(data=service.get_vpp_aggregation())
    except Exception as e:
        return APIResponse(code=500, message=f"获取VPP聚合状态失败: {str(e)}")


@router.get("/trend/hourly")
async def get_hourly_trend(hours: int = Query(24, ge=1, le=168)):
    """获取园区逐小时趋势数据（从静态JSON加载）"""
    try:
        from data.mock_data import get_mock_data
        trend = get_mock_data().get_park_hourly_trend(hours)
        return APIResponse(data={"trend": trend})
    except Exception as e:
        return APIResponse(code=500, message=f"获取趋势数据失败: {str(e)}")