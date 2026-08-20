"""
zero_carbon_park_agent 能源优化工作流（LangGraph）
实现"能源调度 → 储能优化 → VPP 聚合 → 报告生成"的全链路能源优化闭环
"""
import operator
from typing import TypedDict, List, Optional, Annotated, Dict, Any
from datetime import datetime
import uuid
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from langgraph.graph import StateGraph, END


class WorkflowState(TypedDict):
    """LangGraph 工作流状态定义"""
    # 工作流元信息
    workflow_id: str
    workflow_type: str
    current_step: str
    params: Dict[str, Any]

    # 预测数据
    pv_forecast: Optional[float]
    wind_forecast: Optional[float]
    load_forecast: Optional[float]
    storage_soc: Optional[float]

    # 能源调度结果
    dispatch_result: Optional[dict]

    # 储能优化结果
    storage_plan: Optional[dict]

    # VPP 聚合结果
    vpp_result: Optional[dict]

    # 报告
    report_content: Optional[str]

    # 控制
    error: Optional[str]

    # 消息历史
    messages: Annotated[List[dict], operator.add]


# ── 工作流节点定义 ────────────────────────────────────────────────────────

def energy_dispatch_node(state: WorkflowState) -> dict:
    """能源调度节点"""
    from agents.energy_dispatch_agent import EnergyDispatchAgent
    agent = EnergyDispatchAgent()
    result = agent.run(state)
    plan = result.get("dispatch_result", {}).get("plan", {})
    renewable_ratio = plan.get("renewable_ratio_percent", 0)
    print(f"  [能源调度] 可再生能源占比: {renewable_ratio}%")
    return result


def storage_optimization_node(state: WorkflowState) -> dict:
    """储能优化节点"""
    from agents.storage_optimization_agent import StorageOptimizationAgent
    agent = StorageOptimizationAgent()
    result = agent.run(state)
    summary = result.get("storage_plan", {}).get("summary", {})
    print(f"  [储能优化] 日收益: {summary.get('total_daily_benefit_cny', 0)} 元")
    return result


def vpp_aggregation_node(state: WorkflowState) -> dict:
    """VPP 聚合节点"""
    from agents.vpp_aggregation_agent import VPPAggregationAgent
    agent = VPPAggregationAgent()
    result = agent.run(state)
    vpp = result.get("vpp_result", {})
    print(f"  [VPP聚合] 聚合容量: {vpp.get('aggregated_capacity_mw', 0)} MW, 预计收益: {vpp.get('estimated_revenue_cny', 0)} 元")
    return result


def report_generation_node(state: WorkflowState) -> dict:
    """报告生成节点"""
    import json as _json

    # 收集各环节结果
    dispatch_result = state.get("dispatch_result", {})
    storage_plan = state.get("storage_plan", {})
    vpp_result = state.get("vpp_result", {})

    from agents.llm_client import get_llm_client, MockLLMClient
    client = get_llm_client()
    if not client.is_configured():
        client = MockLLMClient()

    report_prompt = f"""请生成零碳园区能源优化报告，包含以下内容：

## 能源调度结果
{_json.dumps(dispatch_result, ensure_ascii=False, indent=2)}

## 储能优化结果
{_json.dumps(storage_plan, ensure_ascii=False, indent=2)}

## VPP 聚合结果
{_json.dumps(vpp_result, ensure_ascii=False, indent=2)}

## 格式要求
- 使用 Markdown 格式
- 包含：能源调度概览、储能运行策略、VPP 市场参与、碳排放节省、经济效益分析
- 语言专业简洁"""

    try:
        report = client.chat([{"role": "user", "content": report_prompt}])
    except Exception:
        dispatch_plan = dispatch_result.get("plan", {})
        storage_summary = storage_plan.get("summary", {})
        vpp = vpp_result

        report = f"""# 零碳园区能源优化报告

## 能源调度概览
- 可再生能源占比: {dispatch_plan.get('renewable_ratio_percent', 'N/A')}%
- 碳排放节省: {dispatch_plan.get('estimated_carbon_saving_tco2', 'N/A')} tCO₂
- 综合用电成本: {dispatch_plan.get('total_cost_cny', 'N/A')} 元

## 储能运行策略
- 峰谷套利日收益: {storage_summary.get('daily_arbitrage_revenue_cny', 'N/A')} 元
- 需量管理月节省: {storage_summary.get('demand_charge_saving_monthly_cny', 'N/A')} 元
- 总日收益: {storage_summary.get('total_daily_benefit_cny', 'N/A')} 元

## VPP 市场参与
- 聚合容量: {vpp.get('aggregated_capacity_mw', 'N/A')} MW
- 上调容量: {vpp.get('adjustable_up_mw', 'N/A')} MW
- 下调容量: {vpp.get('adjustable_down_mw', 'N/A')} MW
- 预计收益: {vpp.get('estimated_revenue_cny', 'N/A')} 元

## 综合建议
1. 持续优化光储协同运行，提升可再生能源就地消纳率
2. 积极参与电力辅助服务市场，通过 VPP 聚合获取额外收益
3. 关注储能电池健康状态，合理安排充放电循环

---
*报告由 zero_carbon_park_agent 能源优化工作流自动生成*
"""

    print(f"  [报告生成] 完成")
    return {
        "current_step": "report_generation",
        "report_content": report,
        "messages": [{"agent": "report_generation", "content": "能源优化报告已生成"}],
    }


# ── 工作流图构建 ──────────────────────────────────────────────────────────

def build_energy_optimization_workflow() -> StateGraph:
    """构建能源优化工作流"""
    workflow = StateGraph(WorkflowState)

    # 添加节点
    workflow.add_node("energy_dispatch", energy_dispatch_node)
    workflow.add_node("storage_optimization", storage_optimization_node)
    workflow.add_node("vpp_aggregation", vpp_aggregation_node)
    workflow.add_node("report_generation", report_generation_node)

    # 添加边：能源调度 → 储能优化 → VPP 聚合 → 报告生成 → 结束
    workflow.set_entry_point("energy_dispatch")
    workflow.add_edge("energy_dispatch", "storage_optimization")
    workflow.add_edge("storage_optimization", "vpp_aggregation")
    workflow.add_edge("vpp_aggregation", "report_generation")
    workflow.add_edge("report_generation", END)

    return workflow.compile()


# ── 工作流执行入口 ────────────────────────────────────────────────────────

def run_energy_optimization_workflow(params: Dict[str, Any] = None) -> Dict[str, Any]:
    """执行能源优化工作流

    Args:
        params: {
            "pv_forecast": 1200.0,
            "wind_forecast": 800.0,
            "load_forecast": 1500.0,
            "storage_soc": 50,
            "storage_capacity_mw": 2.0,
            "interruptible_load_mw": 1.5,
            "ev_charging_mw": 0.8,
            "pv_capacity_mw": 2.0,
            "wind_capacity_mw": 1.5,
        }

    Returns:
        完整的工作流执行结果
    """
    if params is None:
        params = {
            "pv_forecast": 1200.0,
            "wind_forecast": 800.0,
            "load_forecast": 1500.0,
            "storage_soc": 50,
        }

    workflow_id = f"wf_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

    initial_state = {
        "workflow_id": workflow_id,
        "workflow_type": "energy_optimization",
        "current_step": "init",
        "params": params,
        "pv_forecast": params.get("pv_forecast"),
        "wind_forecast": params.get("wind_forecast"),
        "load_forecast": params.get("load_forecast"),
        "storage_soc": params.get("storage_soc"),
        "dispatch_result": None,
        "storage_plan": None,
        "vpp_result": None,
        "report_content": None,
        "error": None,
        "messages": [],
    }

    # 保存工作流记录
    try:
        from db.postgres_client import get_session
        from db.models import WorkflowExecution
        session = get_session()
        wf_record = WorkflowExecution(
            workflow_id=workflow_id,
            workflow_type="energy_optimization",
            status="running",
            started_at=datetime.now(),
        )
        session.add(wf_record)
        session.commit()
        session.close()
    except Exception as e:
        print(f"保存工作流记录失败: {e}")

    print(f"\n{'='*60}")
    print(f"工作流启动: {workflow_id}")
    print(f"类型: energy_optimization | 参数: {params}")
    print(f"{'='*60}")

    app = build_energy_optimization_workflow()
    result = app.invoke(initial_state)

    print(f"\n{'='*60}")
    print(f"工作流完成: {workflow_id}")
    print(f"状态: {result.get('current_step', 'unknown')}")
    print(f"报告长度: {len(result.get('report_content', ''))} 字符")
    print(f"{'='*60}\n")

    return result


if __name__ == "__main__":
    # 测试能源优化工作流
    print("测试能源优化工作流...")
    result = run_energy_optimization_workflow({
        "pv_forecast": 1200.0,
        "wind_forecast": 800.0,
        "load_forecast": 1500.0,
        "storage_soc": 50,
        "storage_capacity_mw": 2.0,
        "interruptible_load_mw": 1.5,
        "ev_charging_mw": 0.8,
    })
    print(f"\n最终报告:\n{result.get('report_content', '无')[:1000]}...")