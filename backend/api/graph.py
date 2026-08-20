"""
zero_carbon_park_agent 知识图谱 API 路由
"""
from fastapi import APIRouter, Query
from schemas.water import APIResponse, GraphQueryRequest

router = APIRouter(prefix="/api/v1/graph", tags=["知识图谱"])


@router.get("/overview")
async def get_graph_overview():
    """获取图谱概览统计"""
    from graph.graph_builder import get_knowledge_graph
    kg = get_knowledge_graph()
    overview = kg.get_overview()
    return APIResponse(data=overview)


@router.post("/query")
async def execute_graph_query(request: GraphQueryRequest):
    """执行知识图谱查询"""
    from tools.graph_query_tool import GraphQueryTool
    import json

    tool = GraphQueryTool()
    result_str = tool.run(
        action=request.action,
        entity_id=request.entity_id,
        trace_direction=request.trace_direction,
    )
    return APIResponse(data=json.loads(result_str))


@router.get("/energy-trace")
async def trace_energy(
    entity_id: str = Query(default="WWTP-001", description="实体 ID"),
    trace_direction: str = Query(default="upstream", description="追溯方向"),
):
    """能源血缘追溯"""
    from graph.graph_builder import get_knowledge_graph
    kg = get_knowledge_graph()

    entity = kg.get_entity_info(entity_id)
    if entity is None:
        return APIResponse(code=404, message=f"实体 {entity_id} 不存在")

    trace = kg.trace_energy(entity_id, trace_direction)
    carbon = kg.calculate_carbon_footprint()

    return APIResponse(data={
        "entity": entity,
        "trace_path": trace,
        "carbon_contribution": {
            "renewable_ratio": carbon["renewable_ratio"],
            "estimated_carbon_tco2_per_hour": carbon["net_emission_tco2_per_h"],
        },
    })


@router.get("/entities")
async def get_entities_by_type(
    node_type: str = Query(default="EnergyLoad", description="节点类型"),
):
    """获取指定类型的所有实体"""
    from graph.graph_builder import get_knowledge_graph
    kg = get_knowledge_graph()
    entities = kg.get_all_entities_by_type(node_type)
    return APIResponse(data={"type": node_type, "entities": entities})