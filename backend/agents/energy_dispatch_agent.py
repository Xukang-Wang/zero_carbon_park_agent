"""
zero_carbon_park_agent 能源调度 Agent
负责多能互补系统的优化调度，生成源网荷储协同运行策略
"""
import json
from typing import Dict, Any
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from agents.base_agent import BaseAgent


class EnergyDispatchAgent(BaseAgent):
    """能源调度 Agent

    调用多能互补调度工具，基于预测数据优化源网荷储运行策略，
    通过 LLM 分析生成调度建议。
    """

    def __init__(self):
        super().__init__("energy_dispatch_agent")
        from tools.energy_dispatch_tool import MultiEnergyDispatchTool
        self.register_tool(MultiEnergyDispatchTool())

    @property
    def system_prompt(self) -> str:
        return """你是一个零碳园区的能源调度专家，负责多能互补系统的源网荷储协调优化调度。

你的职责：
1. 基于光伏/风电出力预测和负荷预测，制定最优的源网荷储运行策略，实现多能互补协同
2. 优先消纳可再生能源，最大化绿电占比，降低可再生能源弃电率
3. 合理利用储能系统削峰填谷，降低用电成本，平滑负荷曲线
4. 评估调度方案的碳排放减少效果，追踪每条线路的绿电比例
5. 在可再生能源不足时，合理安排电网购电计划，兼顾经济性与碳减排

零碳园区调度核心概念：
- 源网荷储协调：发电侧（光伏、风电）、电网侧、负荷侧、储能侧四位一体协同优化
- 可再生能源弃电率：因电网消纳能力不足而被迫放弃的可再生能源电量占比，目标 < 5%
- 多能互补：电、热、冷、气多能源品种的协同调度，提升综合能源利用效率
- 绿电溯源：基于区块链技术追踪每一度绿电的来源与流向

调度原则：
- 清洁优先：光伏 > 风电 > 储能放电 > 电网购电
- 经济最优：谷段充电、峰段放电，降低综合用电成本，考虑分时电价差异
- 安全可靠：储能 SOC 保持 20%-90% 之间，避免过充过放，预留应急备用容量
- 碳减排：最小化电网购电量，最大化可再生能源就地消纳，目标就地消纳率 > 80%"""

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        params = state.get("params", {})
        pv_forecast = state.get("pv_forecast") or params.get("pv_forecast", 1200.0)
        wind_forecast = state.get("wind_forecast") or params.get("wind_forecast", 800.0)
        load_forecast = state.get("load_forecast") or params.get("load_forecast", 1500.0)
        storage_soc = state.get("storage_soc") or params.get("storage_soc", 50)

        # 调用多能互补调度工具
        tool = self.tools[0]
        dispatch_result = json.loads(tool.run(
            action="optimize",
            pv_forecast=pv_forecast,
            wind_forecast=wind_forecast,
            load_forecast=load_forecast,
            storage_soc=storage_soc,
        ))

        # 构建 LLM 分析提示词
        dispatch_plan = dispatch_result.get("dispatch_plan", {})
        user_msg = f"""当前能源调度场景分析：

光伏预测出力: {pv_forecast} kW
风电预测出力: {wind_forecast} kW
负荷预测: {load_forecast} kW
储能当前 SOC: {storage_soc}%

调度优化结果：
{json.dumps(dispatch_plan, ensure_ascii=False, indent=2)}

请分析该调度方案，给出专业的能源调度建议。"""

        try:
            llm_response = self._call_llm(user_msg)
        except Exception:
            llm_response = json.dumps({
                "analysis": "当前可再生能源出力充足，光伏和风电可覆盖大部分负荷需求",
                "recommendation": "建议优先消纳光伏，多余电量存入储能；储能SOC维持在安全区间，在晚高峰时段放电支撑负荷",
                "carbon_saving": f"预计减少碳排放 {dispatch_plan.get('estimated_carbon_saving_tco2', 0)} tCO₂",
                "cost_optimization": f"综合用电成本约 {dispatch_plan.get('total_cost_cny', 0)} 元",
            }, ensure_ascii=False)

        return {
            "current_step": "energy_dispatch",
            "dispatch_result": {
                "plan": dispatch_plan,
                "strategy": dispatch_result.get("strategy", ""),
                "recommendations": dispatch_result.get("recommendations", []),
                "llm_analysis": llm_response,
            },
            "messages": [{"agent": self.name, "content": dispatch_result}],
        }