"""
zero_carbon_park_agent 储能优化 Agent
负责零碳园区储能系统的充放电策略优化与收益分析
"""
import json
from typing import Dict, Any
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from agents.base_agent import BaseAgent


class StorageOptimizationAgent(BaseAgent):
    """储能优化 Agent

    调用储能优化工具，基于分时电价和储能状态制定最优充放电计划，
    通过 LLM 分析生成储能优化建议。
    """

    def __init__(self):
        super().__init__("storage_optimization_agent")
        from tools.storage_optimization_tool import StorageOptimizationTool
        self.register_tool(StorageOptimizationTool())

    @property
    def system_prompt(self) -> str:
        return """你是一个储能系统优化专家，负责零碳园区储能系统的充放电策略优化、峰谷套利与寿命管理。

你的职责：
1. 基于分时电价机制，制定储能系统的最优 24 小时充放电计划，最大化峰谷价差套利收益
2. 分析需量管理效果，通过削峰降低最大需量，减少基本电费（需量电费）支出
3. 评估电池退化成本，将循环寿命损耗纳入经济性分析，确保净收益最大化
4. 分析共享储能商业模式的投资回报，包括容量租赁、辅助服务等多重收益
5. 确保储能系统安全运行，SOC 在安全区间内，避免深度放电和过充

储能优化核心概念：
- 峰谷套利（Peak-Valley Arbitrage）：在谷段低电价时充电，峰段高电价时放电，赚取电价差
- 需量管理（Demand Charge Management）：通过储能放电削减峰值负荷，降低按需量计费的基本电费
- 电池退化（Battery Degradation）：每次充放电循环导致的容量衰减，需计算循环成本（元/kWh/cycle）
- SOC 约束：荷电状态（State of Charge）需保持在 20%-90% 安全区间，避免加速老化

优化原则：
- 经济性：谷段充电、峰段放电，最大化电价差收益，同时考虑需量电费节省
- 安全性：SOC 维持在 20%-90%，设定放电深度（DOD）上限，避免过放损伤电池
- 寿命管理：每日充放电循环不超过 1.5 次，将电池退化成本计入经济性评估
- 光储协同：与光伏出力曲线配合，在光伏大发时段充电，实现光储一体化运行"""

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        params = state.get("params", {})
        current_soc = state.get("storage_soc") or params.get("storage_soc", 50)
        electricity_price = params.get("electricity_price", None)
        peak_hours = params.get("peak_hours", None)

        # 调用储能优化工具
        tool = self.tools[0]
        storage_result = json.loads(tool.run(
            action="optimize",
            current_soc=current_soc,
            electricity_price=electricity_price,
            peak_hours=peak_hours,
        ))

        # 构建 LLM 分析提示词
        summary = storage_result.get("summary", {})
        schedule = storage_result.get("schedule", [])

        charge_hours = len([s for s in schedule if s["action"] == "charge"])
        discharge_hours = len([s for s in schedule if s["action"] == "discharge"])

        user_msg = f"""储能优化调度分析：

当前 SOC: {current_soc}%
充电时段数: {charge_hours}
放电时段数: {discharge_hours}

优化结果摘要：
{json.dumps(summary, ensure_ascii=False, indent=2)}

请分析该储能优化方案，给出专业的储能运行建议。"""

        try:
            llm_response = self._call_llm(user_msg)
        except Exception:
            llm_response = json.dumps({
                "analysis": f"储能系统在谷段充电 {charge_hours} 小时，峰段放电 {discharge_hours} 小时，实现峰谷套利",
                "daily_benefit": f"预计日收益 {summary.get('daily_arbitrage_revenue_cny', 0)} 元",
                "recommendation": "建议在光伏出力高峰期将多余电量存入储能，实现光储协同优化",
            }, ensure_ascii=False)

        return {
            "current_step": "storage_optimization",
            "storage_plan": {
                "schedule": schedule,
                "summary": summary,
                "strategy": storage_result.get("strategy", ""),
                "llm_analysis": llm_response,
            },
            "messages": [{"agent": self.name, "content": storage_result}],
        }