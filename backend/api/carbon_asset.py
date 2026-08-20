"""
zero_carbon_park_agent 碳资产管理 API 路由
"""
from fastapi import APIRouter, Query
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from schemas.water import APIResponse

router = APIRouter(prefix="/api/v1/carbon-asset", tags=["碳资产管理"])


@router.get("/emissions")
async def get_scope_emissions():
    """获取Scope 1/2/3碳排放数据"""
    from datetime import datetime
    from data.mock_data import get_mock_data

    try:
        md = get_mock_data()
        data = md.get_scope_emissions()
        data["generated_at"] = datetime.now().isoformat()
        return APIResponse(data=data)
    except Exception as e:
        return APIResponse(code=500, message=f"获取碳排放数据失败: {str(e)}")


@router.get("/portfolio")
async def get_carbon_portfolio():
    """获取碳资产组合"""
    from datetime import datetime
    from data.mock_data import get_mock_data

    try:
        md = get_mock_data()
        data = md.get_carbon_portfolio()
        data["generated_at"] = datetime.now().isoformat()
        return APIResponse(data=data)
    except Exception as e:
        return APIResponse(code=500, message=f"获取碳资产组合失败: {str(e)}")


@router.get("/trading-strategy")
async def get_trading_strategy():
    """获取碳交易策略建议"""
    from datetime import datetime
    from data.mock_data import get_mock_data

    try:
        md = get_mock_data()
        data = md.get_trading_strategy()
        data["generated_at"] = datetime.now().isoformat()
        return APIResponse(data=data)
    except Exception as e:
        return APIResponse(code=500, message=f"获取交易策略失败: {str(e)}")


@router.get("/cbam-report")
async def get_cbam_report(product_type: str = Query("steel", description="产品类型: steel/aluminum/cement/fertilizer")):
    """获取CBAM合规报告"""
    from datetime import datetime
    from data.mock_data import get_mock_data

    try:
        md = get_mock_data()
        data = md.get_cbam_report(product_type)
        data["generated_at"] = datetime.now().isoformat()
        return APIResponse(data=data)
    except Exception as e:
        return APIResponse(code=500, message=f"获取CBAM报告失败: {str(e)}")