"""
zero_carbon_park_agent 任务派发 Agent
创建工单记录，模拟推送通知
"""
import json
from typing import Dict, Any
from pathlib import Path
from datetime import datetime
import sys
import uuid

sys.path.insert(0, str(Path(__file__).parent.parent))
from agents.base_agent import BaseAgent


class TaskAssignmentAgent(BaseAgent):
    """任务派发 Agent

    创建工单记录到数据库，模拟推送通知到运维人员
    """

    def __init__(self):
        super().__init__("task_assignment_agent")
        from tools.graph_query_tool import NotificationTool
        self.register_tool(NotificationTool())

    @property
    def system_prompt(self) -> str:
        return """你是一个零碳园区的运维调度员，负责将异常处置任务分派给相应团队。

你的职责：
1. 根据处置方案生成工单
2. 确定合适的执行团队和优先级
3. 推送通知到相关人员
4. 跟踪工单状态"""

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        severity = state.get("anomaly_severity", "warning")
        actions = state.get("actions", [])
        anomaly_desc = state.get("anomaly_description", "")

        # 生成工单
        task_id = f"TASK-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"

        # 确定优先级
        priority_map = {"critical": "P0", "warning": "P1", "info": "P2"}
        priority = priority_map.get(severity, "P1")

        # 构建通知消息
        notification_msg = f"""【zero_carbon_park_agent 异常处置工单】
工单编号: {task_id}
优先级: {priority}
异常描述: {anomaly_desc}
处置动作: {len(actions)} 项
请立即处理！"""

        # 发送通知
        tool = self.tools[0]
        tool.run(message=notification_msg, severity=severity)

        # 保存工单到数据库
        try:
            from db.postgres_client import get_session
            from db.models import AnomalyEvent
            session = get_session()
            event = AnomalyEvent(
                event_type="water_quality",
                severity=severity,
                source="WQ-001",
                description=anomaly_desc,
                predicted_value=state.get("predicted_value"),
                threshold_value=state.get("threshold"),
                detected_at=datetime.now(),
                workflow_id=state.get("workflow_id", ""),
                status="in_progress",
            )
            session.add(event)
            session.commit()
            session.close()
        except Exception as e:
            print(f"保存工单失败: {e}")

        return {
            "current_step": "task_assignment",
            "task_id": task_id,
            "notification_sent": True,
            "messages": [{"agent": self.name, "content": f"工单 {task_id} 已创建并通知运维团队"}],
        }