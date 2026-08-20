"""
zero_carbon_park_agent 报告生成 Agent
汇总事件全过程数据，生成结构化的异常处置报告
"""
import json
from typing import Dict, Any
from pathlib import Path
from datetime import datetime
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from agents.base_agent import BaseAgent


class ReportGenerationAgent(BaseAgent):
    """报告生成 Agent

    LLM 汇总事件全过程，生成结构化处置报告（Markdown 格式）
    """

    def __init__(self):
        super().__init__("report_generation_agent")

    @property
    def system_prompt(self) -> str:
        return """你是一个零碳园区的报告撰写专家，擅长生成结构化的异常处置报告。

报告要求：
1. 格式规范：使用 Markdown 格式，包含事件概述、根因分析、处置方案、预计影响、后续跟进
2. 数据准确：引用实际的预测值、阈值、碳排放数据
3. 语言专业：使用工业废水处理和水务管理的专业术语
4. 可操作性：给出明确的后续跟进建议

报告结构：
- 事件概述（时间、类型、严重程度、预测值）
- 根因分析（上游来源、排放变化、历史对比）
- 处置方案（具体动作、优先级、执行人）
- 预计影响（恢复时间、碳排放、资源回收）
- 后续跟进（监控计划、评估节点）"""

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        # 汇总所有 Agent 的输出
        report_context = {
            "workflow_id": state.get("workflow_id", ""),
            "anomaly_type": state.get("anomaly_type", ""),
            "anomaly_description": state.get("anomaly_description", ""),
            "anomaly_severity": state.get("anomaly_severity", ""),
            "predicted_value": state.get("predicted_value"),
            "threshold": state.get("threshold"),
            "root_cause_analysis": state.get("root_cause_analysis", ""),
            "dispatch_plan": state.get("dispatch_plan", {}),
            "task_id": state.get("task_id", ""),
            "historical_match": state.get("historical_match", ""),
            "detected_at": datetime.now().isoformat(),
        }

        user_msg = f"""请根据以下信息生成异常处置报告：

{json.dumps(report_context, ensure_ascii=False, indent=2)}"""

        try:
            report = self._call_llm(user_msg, temperature=0.5)
        except Exception:
            from agents.llm_client import MockLLMClient
            report = MockLLMClient._report_response("")

        # 保存报告到数据库
        try:
            from db.postgres_client import get_session
            from db.models import WorkflowExecution

            session = get_session()
            wf = session.query(WorkflowExecution).filter_by(
                workflow_id=state.get("workflow_id", "")
            ).first()
            if wf:
                wf.report_content = report
                wf.status = "completed"
                wf.completed_at = datetime.now()
                session.commit()
            session.close()
        except Exception as e:
            print(f"保存报告失败: {e}")

        return {
            "current_step": "report_generation",
            "report_content": report,
            "messages": [{"agent": self.name, "content": "报告已生成"}],
        }