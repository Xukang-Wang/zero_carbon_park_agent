"""
zero_carbon_park_agent 零碳园区评价指标工具
供 Agent 按国家级标准评估园区零碳达标情况
"""
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.base_tool import BaseTool

logger = logging.getLogger(__name__)


class EvaluationTool(BaseTool):
    """零碳园区评价指标工具

    按国家级标准评估园区零碳达标情况，支持评价打分和认证进度查询。
    """

    @property
    def name(self) -> str:
        return "zero_carbon_evaluation"

    @property
    def description(self) -> str:
        return (
            "零碳园区评价指标工具，按国家级标准评估园区零碳达标情况。"
            "action 可选值: evaluate (零碳评价), certification_progress (认证进度查询)"
        )

    def run(self, action: str = "evaluate", **kwargs) -> str:
        """零碳园区评价指标

        Args:
            action: 操作类型，"evaluate"（零碳评价）或 "certification_progress"（认证进度）
            **kwargs: 额外参数（预留）

        Returns:
            str: JSON 格式的评价结果或错误信息
        """
        if action not in ("evaluate", "certification_progress"):
            return json.dumps({"error": f"无效 action: {action}，支持 evaluate / certification_progress"}, ensure_ascii=False)

        logger.info(f"EvaluationTool run: action={action}, kwargs={kwargs}")
        from graph.graph_builder import get_knowledge_graph

        try:
            if action == "evaluate":
                kg = get_knowledge_graph()
                result = kg.evaluate_zero_carbon_indicators()
            elif action == "certification_progress":
                result = self._get_certification_progress()

            return json.dumps(result, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"EvaluationTool failed: {e}", exc_info=True)
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    @staticmethod
    def _get_certification_progress() -> Dict:
        """获取零碳园区认证进度"""
        return {
            "certification_progress": {
                "current_stage": "第二阶段：资料审核与现场核查",
                "completed_steps": [
                    "第一阶段：申报材料提交",
                    "碳排放基线核算",
                    "减排路径方案设计",
                    "可再生能源装机核查",
                ],
                "pending_steps": [
                    "第二阶段：现场核查（待确认）",
                    "第三阶段：专家评审",
                    "第四阶段：公示与发证",
                ],
                "timeline": {
                    "第一阶段完成": "2026-03-15",
                    "现场核查预计": "2026-09-01",
                    "专家评审预计": "2026-10-15",
                    "预计发证日期": "2026-12-31",
                },
                "estimated_completion_date": "2026-12-31",
                "status": "进行中",
                "notes": "当前已通过初审，各项指标基本达标，等待现场核查安排",
            },
        }

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "操作类型: evaluate / certification_progress",
                    "enum": ["evaluate", "certification_progress"],
                },
            },
            "required": ["action"],
        }