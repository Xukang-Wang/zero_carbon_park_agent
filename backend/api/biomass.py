"""
zero_carbon_park_agent 生物质能 API 路由
"""
from fastapi import APIRouter, Query
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from schemas.water import APIResponse

router = APIRouter(prefix="/api/v1/biomass", tags=["生物质能"])


@router.get("/chp-analysis")
async def get_chp_analysis():
    """获取生物质CHP分析"""
    from datetime import datetime
    from data.mock_data import get_mock_data

    try:
        md = get_mock_data()
        data = md.get_chp_analysis()
        data["generated_at"] = datetime.now().isoformat()
        return APIResponse(data=data)
    except Exception as e:
        return APIResponse(code=500, message=f"获取CHP分析失败: {str(e)}")


@router.get("/biogas-analysis")
async def get_biogas_analysis():
    """获取沼气工程分析"""
    from datetime import datetime
    from data.mock_data import get_mock_data

    try:
        md = get_mock_data()
        data = md.get_biogas_analysis()
        data["generated_at"] = datetime.now().isoformat()
        return APIResponse(data=data)
    except Exception as e:
        return APIResponse(code=500, message=f"获取沼气工程分析失败: {str(e)}")