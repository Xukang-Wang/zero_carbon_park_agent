"""
zero_carbon_park_agent 碳资产管理 Agent
负责零碳园区的碳配额管理、CCER开发、碳交易策略制定
"""
import json
from typing import Dict, Any
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from agents.base_agent import BaseAgent


class CarbonAssetAgent(BaseAgent):
    """碳资产管理 Agent

    负责碳配额管理、CCER 开发、碳交易策略制定、CBAM 合规分析。
    """

    def __init__(self):
        super().__init__("carbon_asset_agent")
        from tools.carbon_accounting_tool import CarbonAccountingTool
        self.register_tool(CarbonAccountingTool())

    @property
    def system_prompt(self) -> str:
        return """你是一个碳资产管理专家，负责零碳园区的碳配额管理、CCER开发、碳交易策略制定与国际碳合规。

你的职责：
1. 核算园区 Scope 1/2/3 碳排放，建立碳排放基线，识别减排重点领域
2. 管理碳配额、CCER、绿证（GEC）等碳资产组合，优化资产配置
3. 制定碳交易策略（买入/卖出/持有碳配额），基于市场价格信号做出决策
4. 分析 CBAM（碳边境调节机制）合规要求，评估出口产品碳关税影响
5. 跟踪 EU ETS 和中国全国碳市场价格走势，预判政策变化对碳资产的影响

碳资产管理核心概念：
- 欧盟碳市场（EU ETS）：全球最大的碳交易市场，碳价直接影响 CBAM 证书成本
- 中国全国碳排放权交易市场（China National ETS）：覆盖电力行业，逐步扩展至钢铁、水泥等行业
- CCER 方法论（Chinese Certified Emission Reduction）：中国核证自愿减排量，包括可再生能源、林业碳汇、甲烷回收等方法学
- 碳边境调节机制（CBAM）：欧盟对进口高碳产品征收碳关税，2026 年正式实施，要求报告嵌入碳排放

分析原则：
- 数据驱动：基于实时碳排放数据和碳市场价格（EU ETS、全国碳市场）做出决策
- 风险控制：碳交易设止损线（建议单笔交易不超过总持仓的 20%），避免单次大额交易
- 合规优先：确保满足 CBAM、EU ETS 等国际碳合规要求，避免碳关税惩罚
- 收益最大化：在合规前提下优化碳资产组合收益，碳价高位时适当减持盈余配额"""

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        # 获取碳相关数据
        carbon_data = state.get("carbon_data", {})
        params = state.get("params", {})

        # 调用碳核算工具
        tool = self.tools[0]
        scope_result = json.loads(tool.run(action="scope_emissions"))
        asset_result = json.loads(tool.run(action="carbon_asset_value"))
        trading_result = json.loads(tool.run(action="carbon_trading_strategy"))

        # 构建 LLM 分析消息
        user_msg = f"""碳排放数据:
{json.dumps(scope_result, ensure_ascii=False, indent=2)}

碳资产组合:
{json.dumps(asset_result, ensure_ascii=False, indent=2)}

交易策略:
{json.dumps(trading_result, ensure_ascii=False, indent=2)}

请综合分析碳资产管理现状，给出优化建议。"""

        try:
            llm_response = self._call_llm(user_msg)
        except Exception:
            from agents.llm_client import MockLLMClient
            llm_response = MockLLMClient._carbon_asset_response("")

        # 构建碳资产概览
        scope_data = scope_result
        asset_data = asset_result
        trading_data = trading_result

        carbon_asset_summary = {
            "total_emissions_tco2": scope_data.get("total_emissions_tco2", 0),
            "net_emissions_tco2": scope_data.get("net_emissions_tco2", 0),
            "carbon_offset_tco2": scope_data.get("carbon_offset_tco2", 0),
            "asset_portfolio_value_cny": asset_data.get("total_asset_value_cny", 0),
            "trading_position": trading_data.get("trading_strategy", {}).get("current_position", "未知"),
            "recommended_action": trading_data.get("trading_strategy", {}).get("recommended_action", "hold"),
        }

        return {
            "current_step": "carbon_asset_management",
            "carbon_asset_summary": carbon_asset_summary,
            "trading_recommendation": trading_data.get("trading_strategy", {}),
            "llm_analysis": llm_response,
            "messages": [{"agent": self.name, "content": llm_response}],
        }