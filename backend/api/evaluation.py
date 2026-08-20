"""
zero_carbon_park_agent 零碳评价 API 路由
"""
from fastapi import APIRouter, Query
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from schemas.water import APIResponse

router = APIRouter(prefix="/api/v1/evaluation", tags=["零碳评价"])


@router.get("/indicators")
async def get_evaluation_indicators():
    """获取零碳园区评价指标"""
    from datetime import datetime
    from data.mock_data import get_mock_data

    try:
        md = get_mock_data()
        data = md.get_evaluation()
        data["generated_at"] = datetime.now().isoformat()
        return APIResponse(data=data)
    except Exception as e:
        return APIResponse(code=500, message=f"获取评价指标失败: {str(e)}")


@router.get("/certification-progress")
async def get_certification_progress():
    """获取认证进度"""
    from datetime import datetime
    from data.mock_data import get_mock_data

    try:
        md = get_mock_data()
        data = md.get_cert_progress()
        data["generated_at"] = datetime.now().isoformat()
        return APIResponse(data=data)
    except Exception as e:
        return APIResponse(code=500, message=f"获取认证进度失败: {str(e)}")