"""
zero_carbon_park_agent 零碳园区智慧能源与水务智能体系统 - 主入口
FastAPI 应用启动文件
"""
import sys
from pathlib import Path

# 确保 backend 目录在 Python 路径中
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from config import API_HOST, API_PORT


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    print("\n" + "=" * 60)
    print("  zero_carbon_park_agent 零碳园区智慧能源与水务智能体系统")
    print("  启动中...")
    print("=" * 60)

    # 初始化数据库
    try:
        from db.postgres_client import init_db
        init_db()
    except Exception as e:
        print(f"  数据库初始化: {e}")

    # 初始化知识图谱
    try:
        from graph.graph_builder import get_knowledge_graph
        get_knowledge_graph()
    except Exception as e:
        print(f"  知识图谱初始化: {e}")

    # 检查 LLM 配置
    from agents.llm_client import get_llm_client
    llm = get_llm_client()
    if llm.is_configured():
        print(f"  LLM: {llm.model} (已配置)")
    else:
        print("  LLM: 未配置 API Key，将使用模拟响应")
        print("  请在 .env 文件中配置 ZERO_CARBON_PARK_AGENT_LLM_API_KEY")

    print(f"\n  API 文档: http://localhost:{API_PORT}/docs")
    print(f"  ReDoc:    http://localhost:{API_PORT}/redoc")
    print("=" * 60 + "\n")

    yield

    print("\nzero_carbon_park_agent 已关闭")


# 创建 FastAPI 应用
app = FastAPI(
    title="zero_carbon_park_agent - 零碳园区智慧能源与水务智能体系统",
    description="基于 LangGraph 多智能体框架的 AI Agent 驱动的能源管理与水务治理一体化平台",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# 跨域中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
from api.water import router as water_router
from api.graph import router as graph_router
from api.carbon import router as carbon_router
from api.agent import router as agent_router
from api.energy import router as energy_router
from api.storage import router as storage_router
from api.vpp import router as vpp_router
from api.carbon_asset import router as carbon_asset_router
from api.evaluation import router as evaluation_router
from api.economic import router as economic_router
from api.biomass import router as biomass_router
from api.industrial_energy import router as industrial_energy_router
from api.ccus import router as ccus_router
from api.nl_interaction import router as nl_interaction_router
from api.park import router as park_router

app.include_router(water_router)
app.include_router(graph_router)
app.include_router(carbon_router)
app.include_router(agent_router)
app.include_router(energy_router)
app.include_router(storage_router)
app.include_router(vpp_router)
app.include_router(carbon_asset_router)
app.include_router(evaluation_router)
app.include_router(economic_router)
app.include_router(biomass_router)
app.include_router(industrial_energy_router)
app.include_router(ccus_router)
app.include_router(nl_interaction_router)
app.include_router(park_router)
from backend.api.operations import router as operations_router
app.include_router(operations_router)


@app.get("/")
async def root():
    """根路径"""
    return {
        "name": "zero_carbon_park_agent 零碳园区智慧能源与水务智能体系统",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "running",
    }


@app.get("/api/v1/health")
async def health_check():
    """健康检查"""
    from agents.llm_client import get_llm_client
    llm = get_llm_client()

    return {
        "status": "healthy",
        "llm_configured": llm.is_configured(),
        "model": llm.model,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=API_HOST,
        port=API_PORT,
        reload=True,
        log_level="info",
    )
