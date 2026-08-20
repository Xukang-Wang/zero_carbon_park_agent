"""
zero_carbon_park_agent 碳足迹 API 路由
"""
from fastapi import APIRouter, Query
from schemas.water import APIResponse

router = APIRouter(prefix="/api/v1/carbon", tags=["碳足迹"])


@router.get("/footprint")
async def get_carbon_footprint():
    """查询碳足迹汇总"""
    from graph.graph_builder import get_knowledge_graph
    kg = get_knowledge_graph()
    result = kg.calculate_carbon_footprint()
    return APIResponse(data=result)


@router.get("/trend")
async def get_carbon_trend(days: int = Query(default=7, ge=1, le=30)):
    """碳足迹趋势数据（从静态JSON加载）"""
    from data.mock_data import get_mock_data

    md = get_mock_data()
    trend = md.get_carbon_trend(days)
    return APIResponse(data={"trend": trend})