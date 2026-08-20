"""
zero_carbon_park_agent 自然语言交互 API 路由
"""
from fastapi import APIRouter
from pydantic import BaseModel
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from schemas.water import APIResponse

router = APIRouter(prefix="/api/v1/nl-interaction", tags=["自然语言交互"])


class NLQueryRequest(BaseModel):
    query: str
    context: str = "zero_carbon_park"


@router.post("/query")
async def process_nl_query(request: NLQueryRequest):
    """处理自然语言查询"""
    from datetime import datetime
    try:
        from agents.nl_interaction_agent import NLInteractionAgent
        agent = NLInteractionAgent()
        answer = agent.run(request.query)
        return APIResponse(data={
            "query": request.query,
            "answer": answer,
            "timestamp": datetime.now().isoformat(),
            "context": request.context,
        })
    except Exception as e:
        return APIResponse(code=500, message=f"自然语言查询处理失败: {str(e)}")


@router.get("/examples")
async def get_query_examples():
    """获取示例查询"""
    return APIResponse(data={
        "examples": [
            "今天的碳排放量是多少？",
            "光伏发电预测功率是多少？",
            "储能系统当前SOC是多少？",
            "园区的碳排放强度是多少？",
            "VPP聚合容量有多少？",
            "光伏项目的投资回收期是多久？",
            "碳配额现在值多少钱？",
            "园区零碳评价得分是多少？",
        ]
    })