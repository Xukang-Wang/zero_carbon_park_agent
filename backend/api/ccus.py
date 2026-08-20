"""
zero_carbon_park_agent CCUS 碳捕集 API 路由
"""
from fastapi import APIRouter, Query
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from schemas.water import APIResponse

router = APIRouter(prefix="/api/v1/ccus", tags=["CCUS碳捕集"])


@router.get("/analysis")
async def get_ccus_analysis():
    """获取CCUS项目分析"""
    from data.mock_data import get_mock_data
    from datetime import datetime
    try:
        md = get_mock_data()
        data = md.get_ccus()
        data["generated_at"] = datetime.now().isoformat()
        return APIResponse(data=data)
    except Exception as e:
        return APIResponse(code=500, message=f"获取CCUS分析失败: {str(e)}")


@router.get("/utilization")
async def get_co2_utilization():
    """获取CO2利用路径分析"""
    from data.mock_data import get_mock_data
    try:
        md = get_mock_data()
        data = md.get_ccus()
        return APIResponse(data={
            "utilization_paths": data["utilization"],
            "total_capacity_tco2_per_year": sum(p["capacity_tco2_per_year"] for p in data["utilization"]),
        })
    except Exception as e:
        return APIResponse(code=500, message=f"获取CO2利用路径失败: {str(e)}")