"""
zero_carbon_park_agent 自然语言交互 Agent
通过自然语言回答园区运营相关的各类问题，路由到正确的工具并返回答案
"""
import json
from typing import Dict, Any
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from agents.base_agent import BaseAgent


class NLInteractionAgent(BaseAgent):
    """自然语言交互 Agent

    理解用户自然语言查询意图，路由到对应工具，返回自然语言响应。
    这是一个通用的问答入口，可以回答碳排放、新能源、经济分析等各类问题。
    """

    def __init__(self):
        super().__init__("nl_interaction_agent")
        from tools.prediction_tool import PredictionTool
        from tools.graph_query_tool import GraphQueryTool
        from tools.carbon_accounting_tool import CarbonAccountingTool
        from tools.power_prediction_tool import PowerPredictionTool
        from tools.evaluation_tool import EvaluationTool
        from tools.economic_analysis_tool import EconomicAnalysisTool

        self.register_tool(PredictionTool())
        self.register_tool(GraphQueryTool())
        self.register_tool(CarbonAccountingTool())
        self.register_tool(PowerPredictionTool())
        self.register_tool(EvaluationTool())
        self.register_tool(EconomicAnalysisTool())

    @property
    def system_prompt(self) -> str:
        return """你是零碳园区的AI智能助手，能够通过自然语言回答园区运营相关的各类专业问题。

你可以回答的问题类型：
1. 碳排放查询：Scope 1/2/3 排放量、碳足迹追溯、碳配额盈余/缺口、CCER 持有量、CBAM 合规状态
2. 新能源预测：光伏/风电未来 24 小时出力预测、容量因子、累计发电量预估
3. 零碳评价：园区零碳指标达标情况、可再生能源占比、认证进度、各指标得分
4. 经济效益：光伏/储能/综合能源项目的 IRR、NPV、LCOE、投资回收期
5. 能源图谱：能源流向追溯、变压器/线路/设备信息查询、拓扑结构分析
6. 水质预测：COD/氨氮/硝氮未来 24 小时预测值、超标预警、异常趋势分析

领域特定查询示例：
- "园区今天的光伏出力预测是多少？储能SOC什么时候达到90%？"
- "Scope 2 碳排放占比多少？与去年同期相比变化趋势如何？"
- "CCER 当前市场价多少？现在卖出 CCER 是否合适？"
- "CBAM 正式实施后，我们出口欧盟的钢铁产品每吨需要额外支付多少碳关税？"
- "1号变压器的负荷率是多少？有没有过载风险？"
- "COD 在未来 6 小时内会超过 300 mg/L 的严重阈值吗？"
- "园区当前的绿电占比是多少？离零碳认证还差多少？"

回答原则：
- 准确专业：基于实际数据和工具返回结果回答，引用具体数值
- 简洁明了：用通俗易懂的语言解释专业概念，但保留关键术语
- 数据支撑：引用具体的数值和指标，标注数据来源
- 建议可行：给出可操作的建议，优先推荐高收益低风险方案"""

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        params = state.get("params", {})
        query = params.get("query", "")

        if not query:
            response_text = "您好！我是零碳园区AI助手，请问有什么可以帮您？"
            return {
                "current_step": "nl_interaction",
                "nl_response": response_text,
                "messages": [{"agent": self.name, "content": response_text}],
            }

        # 用 LLM 理解查询意图并路由
        routing_msg = f"""用户查询: {query}

请判断用户意图属于以下哪一类，并选择对应的 action：
1. carbon_emission - 碳排放、碳足迹、碳配额相关问题
2. power_prediction - 光伏、风电、新能源出力预测
3. zero_carbon_evaluation - 零碳园区评价、认证、达标
4. economic_analysis - 投资回报、经济性分析、回收期
5. energy_graph - 能源流向、设备信息、图谱查询
6. water_quality - 水质预测、水质指标
7. general - 一般性问题

请只返回 action 值，不要返回其他内容。"""

        try:
            intent = self._call_llm(routing_msg).strip().lower()
        except Exception:
            intent = self._simple_route(query)

        # 根据意图路由到对应工具
        tool_results = self._execute_tool(intent, query, params)

        # 用 LLM 生成自然语言回答
        answer_msg = f"""用户问题: {query}

工具返回数据:
{json.dumps(tool_results, ensure_ascii=False, indent=2)}

请用自然、友好的语言回答用户的问题，直接给出答案，包含关键数据。"""

        try:
            response_text = self._call_llm(answer_msg, temperature=0.5)
        except Exception:
            from agents.llm_client import MockLLMClient
            response_text = MockLLMClient._nl_query_response(query)

        return {
            "current_step": "nl_interaction",
            "nl_response": response_text,
            "nl_intent": intent,
            "nl_tool_results": tool_results,
            "messages": [{"agent": self.name, "content": response_text}],
        }

    @staticmethod
    def _simple_route(query: str) -> str:
        """简单的关键词路由（LLM 不可用时的 fallback）"""
        keywords = {
            "carbon_emission": ["碳排", "碳足迹", "碳配额", "碳资产", "CCER", "CBAM", "碳交易"],
            "power_prediction": ["光伏", "风电", "新能源", "发电", "出力", "功率预测"],
            "zero_carbon_evaluation": ["零碳", "评价", "认证", "达标", "指标"],
            "economic_analysis": ["投资", "经济", "回收期", "IRR", "NPV", "回报", "收益"],
            "energy_graph": ["图谱", "能源流向", "设备", "追溯", "变压器"],
            "water_quality": ["水质", "COD", "氨氮", "硝氮", "污水"],
        }

        for intent, kws in keywords.items():
            if any(kw in query for kw in kws):
                return intent
        return "general"

    def _execute_tool(self, intent: str, query: str, params: Dict) -> Dict:
        """根据意图执行对应工具"""
        try:
            if intent == "carbon_emission":
                result = json.loads(self.tools[2].run(action="scope_emissions"))
            elif intent == "power_prediction":
                source = "pv" if "光伏" in query else "wind"
                result = json.loads(self.tools[3].run(source=source))
            elif intent == "zero_carbon_evaluation":
                result = json.loads(self.tools[4].run(action="evaluate"))
            elif intent == "economic_analysis":
                if "储能" in query:
                    result = json.loads(self.tools[5].run(action="storage_economics"))
                elif "综合" in query:
                    result = json.loads(self.tools[5].run(action="comprehensive_energy"))
                else:
                    result = json.loads(self.tools[5].run(action="pv_economics"))
            elif intent == "energy_graph":
                result = json.loads(self.tools[1].run(action="overview"))
            elif intent == "water_quality":
                device_id = params.get("device_id", "WQ-001")
                result = json.loads(self.tools[0].run(device_id=device_id))
            else:
                # 综合查询：返回多个工具的结果概览
                result = {
                    "carbon_data": json.loads(self.tools[2].run(action="scope_emissions")),
                    "graph_overview": json.loads(self.tools[1].run(action="overview")),
                    "zero_carbon_status": json.loads(self.tools[4].run(action="evaluate")),
                }
            return result
        except Exception as e:
            return {"error": str(e)}