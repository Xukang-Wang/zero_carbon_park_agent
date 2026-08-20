"""
zero_carbon_park_agent 水质异常处置工作流（LangGraph）
实现"异常检测→根因分析→调度决策→任务派发→报告生成"的全链路自动化闭环
"""
import operator
import math
from typing import TypedDict, List, Optional, Annotated, Dict, Any
from datetime import datetime
from collections import deque
import uuid
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from langgraph.graph import StateGraph, END


# ── 滑动窗口异常检测辅助函数 ──────────────────────────────────────────────

# 滑动窗口存储（用于模拟历史数据）
_sliding_window_store: Dict[str, deque] = {}


def _compute_anomaly_score(
    metric_name: str,
    current_value: float,
    window_size: int = 24,
    warning_threshold: float = None,
    critical_threshold: float = None,
) -> Dict[str, Any]:
    """基于滑动窗口和 Z-Score 的异常检测

    使用最近 window_size 个数据点的滚动均值和标准差，
    计算当前值的 Z-Score，结合阈值检测返回异常评分。

    Args:
        metric_name: 指标名称（如 "COD"）
        current_value: 当前预测值
        window_size: 滑动窗口大小（默认 24 小时）
        warning_threshold: 预警阈值（可选）
        critical_threshold: 严重阈值（可选）

    Returns:
        dict: 包含 z_score, anomaly_score, anomaly_level 等字段
    """
    # 初始化滑动窗口
    if metric_name not in _sliding_window_store:
        # 用当前值生成历史窗口（基于 metric_name 的确定性偏移，无随机性）
        seed = hash(metric_name) % 100
        offset_factor = (seed - 50) / 100.0  # -0.5 ~ 0.5
        historical = [current_value * (1.0 + offset_factor * (i / window_size - 0.5))
                      for i in range(window_size)]
        _sliding_window_store[metric_name] = deque(historical, maxlen=window_size)

    window = _sliding_window_store[metric_name]

    # 计算滚动均值和标准差
    if len(window) >= 2:
        mean_val = sum(window) / len(window)
        variance = sum((x - mean_val) ** 2 for x in window) / len(window)
        std_val = math.sqrt(variance) if variance > 0 else 1e-6
    else:
        mean_val = current_value
        std_val = 1e-6

    # Z-Score 计算
    z_score = (current_value - mean_val) / std_val if std_val > 0 else 0.0

    # 异常评分：综合 Z-Score 和阈值检测
    # Z-Score 贡献（0-50 分）：|Z| > 3 得满分 50，|Z| > 2 得 30，|Z| > 1 得 15
    z_score_contribution = 0.0
    abs_z = abs(z_score)
    if abs_z > 3:
        z_score_contribution = 50.0
    elif abs_z > 2:
        z_score_contribution = 30.0
    elif abs_z > 1:
        z_score_contribution = 15.0

    # 阈值贡献（0-50 分）
    threshold_contribution = 0.0
    threshold_exceeded = False
    if critical_threshold is not None and current_value > critical_threshold:
        threshold_contribution = 50.0
        threshold_exceeded = True
    elif warning_threshold is not None and current_value > warning_threshold:
        threshold_contribution = 30.0
        threshold_exceeded = True

    # 综合异常评分
    anomaly_score = round(z_score_contribution + threshold_contribution, 2)

    # 异常等级判定
    if anomaly_score >= 70:
        anomaly_level = "critical"
    elif anomaly_score >= 40:
        anomaly_level = "warning"
    elif anomaly_score >= 20:
        anomaly_level = "attention"
    else:
        anomaly_level = "normal"

    # 更新滑动窗口
    _sliding_window_store[metric_name].append(current_value)

    return {
        "metric": metric_name,
        "current_value": current_value,
        "rolling_mean": round(mean_val, 4),
        "rolling_std": round(std_val, 4),
        "z_score": round(z_score, 4),
        "anomaly_score": anomaly_score,
        "anomaly_level": anomaly_level,
        "threshold_exceeded": threshold_exceeded,
        "warning_threshold": warning_threshold,
        "critical_threshold": critical_threshold,
        "window_size": len(window),
    }


class WorkflowState(TypedDict):
    """LangGraph 工作流状态定义"""
    # 工作流元信息
    workflow_id: str
    workflow_type: str
    current_step: str
    params: Dict[str, Any]

    # 异常信息（由异常检测 Agent 填充）
    anomaly_type: Optional[str]
    anomaly_description: Optional[str]
    anomaly_severity: Optional[str]
    predicted_value: Optional[float]
    threshold: Optional[float]
    anomaly_score: Optional[float]

    # 分析结果（由根因分析 Agent 填充）
    root_cause_analysis: Optional[str]
    related_entities: Annotated[List[str], operator.add]
    historical_match: Optional[str]

    # 决策结果（由调度决策 Agent 填充）
    dispatch_plan: Optional[dict]
    actions: Annotated[List[dict], operator.add]

    # 执行结果（由任务派发 Agent 填充）
    task_id: Optional[str]
    notification_sent: bool

    # 报告（由报告生成 Agent 填充）
    report_content: Optional[str]

    # 控制
    human_approval_required: bool
    error: Optional[str]

    # 消息历史（所有 Agent 共享）
    messages: Annotated[List[dict], operator.add]


# ── 工作流节点定义 ────────────────────────────────────────────────────────

def anomaly_detection_node(state: WorkflowState) -> dict:
    """异常检测节点（集成滑动窗口 Z-Score 检测）"""
    from agents.anomaly_detection_agent import AnomalyDetectionAgent
    agent = AnomalyDetectionAgent()
    result = agent.run(state)

    # ── 滑动窗口 Z-Score 增强检测 ──
    predicted_value = result.get("predicted_value")
    anomaly_flags = result.get("anomaly_flags", [])

    if predicted_value is not None and anomaly_flags:
        # 对每个异常指标进行 Z-Score 分析
        first_flag = anomaly_flags[0]
        metric_name = first_flag.get("metric", "COD")
        warning_threshold = first_flag.get("warning_threshold", 250)
        critical_threshold = first_flag.get("threshold", 300)

        z_score_result = _compute_anomaly_score(
            metric_name=metric_name,
            current_value=predicted_value,
            window_size=24,
            warning_threshold=warning_threshold,
            critical_threshold=critical_threshold,
        )

        # 用 Z-Score 结果增强异常信息
        result["anomaly_score"] = z_score_result["anomaly_score"]
        result["z_score"] = z_score_result["z_score"]
        result["rolling_mean"] = z_score_result["rolling_mean"]
        result["rolling_std"] = z_score_result["rolling_std"]
        result["anomaly_level"] = z_score_result["anomaly_level"]

        # 如果 Z-Score 评级更高，升级严重程度
        if z_score_result["anomaly_level"] == "critical" and result.get("anomaly_severity") != "critical":
            result["anomaly_severity"] = "critical"
            result["anomaly_description"] = (
                f"{result.get('anomaly_description', '')} "
                f"[Z-Score: {z_score_result['z_score']:.2f}, "
                f"滚动均值: {z_score_result['rolling_mean']:.2f}, "
                f"滚动标准差: {z_score_result['rolling_std']:.2f}]"
            )
    else:
        result["anomaly_score"] = 0.0

    print(f"  [异常检测] {result.get('anomaly_description', '正常')} "
          f"(评分: {result.get('anomaly_score', 'N/A')})")
    return result


def root_cause_analysis_node(state: WorkflowState) -> dict:
    """根因分析节点"""
    from agents.root_cause_agent import RootCauseAgent
    agent = RootCauseAgent()
    result = agent.run(state)
    print(f"  [根因分析] 完成")
    return result


def dispatch_decision_node(state: WorkflowState) -> dict:
    """调度决策节点"""
    from agents.dispatch_decision_agent import DispatchDecisionAgent
    agent = DispatchDecisionAgent()
    result = agent.run(state)
    print(f"  [调度决策] 生成 {len(result.get('actions', []))} 项处置动作")
    return result


def should_approve(state: WorkflowState) -> str:
    """条件路由：是否需要人工审批"""
    if state.get("human_approval_required", False):
        return "human_approval"
    return "task_assignment"


def human_approval_node(state: WorkflowState) -> dict:
    """人工审批节点（Demo 中自动通过）"""
    print("  [人工审批] 自动通过（Demo 模式）")
    return {
        "current_step": "human_approval",
        "human_approval_required": False,
        "messages": [{"agent": "human_approval", "content": "处置方案已自动审批通过（Demo 模式）"}],
    }


def task_assignment_node(state: WorkflowState) -> dict:
    """任务派发节点"""
    from agents.task_assignment_agent import TaskAssignmentAgent
    agent = TaskAssignmentAgent()
    result = agent.run(state)
    print(f"  [任务派发] 工单: {result.get('task_id', 'N/A')}")
    return result


def report_generation_node(state: WorkflowState) -> dict:
    """报告生成节点"""
    from agents.report_generation_agent import ReportGenerationAgent
    agent = ReportGenerationAgent()
    result = agent.run(state)
    print(f"  [报告生成] 完成")
    return result


# ── 工作流图构建 ──────────────────────────────────────────────────────────

def build_water_anomaly_workflow() -> StateGraph:
    """构建水质异常处置工作流"""
    workflow = StateGraph(WorkflowState)

    # 添加节点
    workflow.add_node("anomaly_detection", anomaly_detection_node)
    workflow.add_node("root_cause_analysis", root_cause_analysis_node)
    workflow.add_node("dispatch_decision", dispatch_decision_node)
    workflow.add_node("human_approval", human_approval_node)
    workflow.add_node("task_assignment", task_assignment_node)
    workflow.add_node("report_generation", report_generation_node)

    # 添加边
    workflow.set_entry_point("anomaly_detection")
    workflow.add_edge("anomaly_detection", "root_cause_analysis")
    workflow.add_edge("root_cause_analysis", "dispatch_decision")

    # 条件路由：严重异常需人工审批
    workflow.add_conditional_edges(
        "dispatch_decision",
        should_approve,
        {
            "human_approval": "human_approval",
            "task_assignment": "task_assignment",
        }
    )

    workflow.add_edge("human_approval", "task_assignment")
    workflow.add_edge("task_assignment", "report_generation")
    workflow.add_edge("report_generation", END)

    return workflow.compile()


# ── 工作流执行入口 ────────────────────────────────────────────────────────

def run_water_anomaly_workflow(params: Dict[str, Any] = None) -> Dict[str, Any]:
    """执行水质异常处置工作流

    Args:
        params: {"device_id": "WQ-001", "anomaly_type": "cod_exceeded", ...}

    Returns:
        完整的工作流执行结果
    """
    if params is None:
        params = {"device_id": "WQ-001"}

    workflow_id = f"wf_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

    initial_state = {
        "workflow_id": workflow_id,
        "workflow_type": "water_anomaly",
        "current_step": "init",
        "params": params,
        "anomaly_type": None,
        "anomaly_description": None,
        "anomaly_severity": None,
        "predicted_value": None,
        "threshold": None,
        "anomaly_score": None,
        "root_cause_analysis": None,
        "related_entities": [],
        "historical_match": None,
        "dispatch_plan": None,
        "actions": [],
        "task_id": None,
        "notification_sent": False,
        "report_content": None,
        "human_approval_required": False,
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
            workflow_type="water_anomaly",
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
    print(f"类型: water_anomaly | 参数: {params}")
    print(f"{'='*60}")

    app = build_water_anomaly_workflow()
    result = app.invoke(initial_state)

    print(f"\n{'='*60}")
    print(f"工作流完成: {workflow_id}")
    print(f"状态: {result.get('current_step', 'unknown')}")
    print(f"报告长度: {len(result.get('report_content', ''))} 字符")
    print(f"{'='*60}\n")

    return result


# ── 日报生成工作流 ────────────────────────────────────────────────────────

def run_daily_report_workflow() -> Dict[str, Any]:
    """执行日报生成工作流"""
    workflow_id = f"dr_{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:6]}"

    # 收集当日数据
    from graph.graph_builder import get_knowledge_graph
    kg = get_knowledge_graph()
    carbon = kg.calculate_carbon_footprint()

    from agents.llm_client import get_llm_client, MockLLMClient
    client = get_llm_client()
    if not client.is_configured():
        client = MockLLMClient()

    today = datetime.now().strftime("%Y-%m-%d")
    report_prompt = f"""请生成 {today} 零碳园区日报，包含以下内容：

## 碳足迹数据
{json.dumps(carbon, ensure_ascii=False, indent=2)}

## 格式要求
- 使用 Markdown 格式
- 包含：碳足迹概览、可再生能源占比、异常事件汇总、明日预测
- 语言专业简洁"""

    import json as _json
    report = client.chat([{"role": "user", "content": report_prompt}])

    return {
        "workflow_id": workflow_id,
        "workflow_type": "daily_report",
        "report_content": report,
        "carbon_data": carbon,
        "generated_at": datetime.now().isoformat(),
    }


if __name__ == "__main__":
    # 测试水质异常工作流
    print("测试水质异常处置工作流...")
    result = run_water_anomaly_workflow({"device_id": "WQ-001"})
    print(f"\n最终报告:\n{result.get('report_content', '无')[:500]}...")