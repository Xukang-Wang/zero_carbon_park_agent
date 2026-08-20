"""
zero_carbon_park_agent 工业节能 API 路由
"""
from fastapi import APIRouter, Query
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from schemas.water import APIResponse

router = APIRouter(prefix="/api/v1/industrial-energy", tags=["工业节能"])


@router.get("/analysis")
async def get_industrial_energy_analysis():
    """获取工业节能诊断分析"""
    from data.mock_data import get_mock_data
    from datetime import datetime
    try:
        md = get_mock_data()
        data = md.get_industrial_energy()
        data["generated_at"] = datetime.now().isoformat()
        return APIResponse(data=data)
    except Exception as e:
        return APIResponse(code=500, message=f"获取工业节能分析失败: {str(e)}")


@router.get("/motors")
async def get_motor_list():
    """获取电机设备列表"""
    from data.mock_data import get_mock_data
    try:
        md = get_mock_data()
        data = md.get_industrial_energy()
        return APIResponse(data={"motors": data["motors"], "total": len(data["motors"])})
    except Exception as e:
        return APIResponse(code=500, message=f"获取电机列表失败: {str(e)}")