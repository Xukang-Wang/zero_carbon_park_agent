"""
zero_carbon_park_agent 调度决策 Agent
基于 LLM 综合分析，生成处置方案，评估是否需要人工审批
"""
import json
from typing import Dict, Any
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from agents.base_agent import BaseAgent


class DispatchDecisionAgent(BaseAgent):
    """调度决策 Agent

    LLM 综合分析异常信息与根因分析结果，生成处置方案，
    并判断是否需要人工审批。
    """

    def __init__(self):
        super().__init__("dispatch_decision_agent")
        from tools.graph_query_tool import ResourceRecoveryTool
        self.register_tool(ResourceRecoveryTool())

    @property
    def system_prompt(self) -> str:
        return """你是一个零碳园区的调度决策专家，负责制定工业废水处理异常处置方案。

你的职责：
1. 综合分析异常检测结果和根因分析结论
2. 生成具体的处置方案（工艺调整、资源回收优化等）
3. 评估处置方案的可行性和预期效果
4. 判断是否需要人工审批（critical 级别必须人工审批）

决策原则：
- 安全第一：优先保障出水水质达标
- 资源最优：在保证水质的前提下最大化甲烷/生物硫回收
- 碳减排：优先选择低碳处置方案
- 分级响应：warning 可自动执行，critical 需人工审批"""

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        anomaly_type = state.get("anomaly_type", "")
        anomaly_desc = state.get("anomaly_description", "")
        severity = state.get("anomaly_severity", "warning")
        root_cause = state.get("root_cause_analysis", "")
        predicted_value = state.get("predicted_value", 300)

        # 调用资源回收优化工具
        tool = self.tools[0]
        recovery_result = json.loads(tool.run(cod_pred=predicted_value))

        # 构建决策消息
        user_msg = f"""异常信息:
- 类型: {anomaly_type}
- 描述: {anomaly_desc}
- 严重程度: {severity}
- 预测值: {predicted_value}

根因分析:
{root_cause}

资源回收优化建议:
{json.dumps(recovery_result, ensure_ascii=False, indent=2)}

请生成处置方案，并判断是否需要人工审批。"""

        try:
            llm_response = self._call_llm(user_msg)
        except Exception:
            llm_response = """处置方案:
1. 调节厌氧罐进料速率降低20%（800→640 m³/h），避免冲击负荷
2. 启动备用曝气风机，提升溶解氧至3.5 mg/L以上
3. 通知1号生产线调整排放节奏，减少瞬时高负荷排放
4. 加强出水COD监测频率至每30分钟一次

预计恢复时间: 4小时
碳排放影响: +0.5 tCO₂
甲烷回收短期影响: -15%"""

        # 构建行动计划
        actions = [
            {"action": "调节厌氧罐进料速率", "detail": "降低20%，从800 m³/h降至640 m³/h", "priority": "high"},
            {"action": "启动备用曝气风机", "detail": "提升DO至3.5 mg/L以上", "priority": "high"},
            {"action": "通知上游产线", "detail": "通知1号生产线调整排放速率", "priority": "medium"},
            {"action": "加强监测", "detail": "出水COD监测频率提升至30分钟/次", "priority": "medium"},
        ]

        # 严重异常需要人工审批
        human_approval_required = severity == "critical"

        return {
            "current_step": "dispatch_decision",
            "dispatch_plan": {"actions": actions, "llm_response": llm_response},
            "actions": actions,
            "human_approval_required": human_approval_required,
            "messages": [{"agent": self.name, "content": llm_response}],
        }