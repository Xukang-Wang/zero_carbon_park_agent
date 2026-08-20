"""
zero_carbon_park_agent 经济性分析 API 路由
"""
from fastapi import APIRouter, Query
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from schemas.water import APIResponse

router = APIRouter(prefix="/api/v1/economic", tags=["经济性分析"])


@router.get("/pv-economics")
async def get_pv_economics():
    """获取光伏项目经济性分析"""
    from datetime import datetime
    from data.mock_data import get_mock_data

    try:
        md = get_mock_data()
        data = md.get_pv_economics()
        data["generated_at"] = datetime.now().isoformat()
        return APIResponse(data=data)
    except Exception as e:
        return APIResponse(code=500, message=f"获取光伏经济性分析失败: {str(e)}")


@router.get("/storage-economics")
async def get_storage_economics():
    """获取储能项目经济性分析"""
    from datetime import datetime
    from data.mock_data import get_mock_data

    try:
        md = get_mock_data()
        data = md.get_storage_economics()
        data["generated_at"] = datetime.now().isoformat()
        return APIResponse(data=data)
    except Exception as e:
        return APIResponse(code=500, message=f"获取储能经济性分析失败: {str(e)}")


@router.get("/comprehensive")
async def get_comprehensive_economics():
    """获取综合能源项目经济性分析"""
    from datetime import datetime
    from data.mock_data import get_mock_data

    try:
        md = get_mock_data()
        data = md.get_comprehensive_economics()
        data["generated_at"] = datetime.now().isoformat()
        return APIResponse(data=data)
    except Exception as e:
        return APIResponse(code=500, message=f"获取综合经济性分析失败: {str(e)}")