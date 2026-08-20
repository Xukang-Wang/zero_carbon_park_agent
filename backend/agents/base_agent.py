"""
zero_carbon_park_agent Agent 基类
所有专业 Agent 的父类，提供统一的 LLM 调用和工具调用接口
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))


class BaseAgent(ABC):
    """Agent 基类

    每个 Agent 拥有：
    - 系统提示词（定义角色和领域知识）
    - LLM 调用能力
    - 可选的工具列表
    """

    def __init__(self, name: str):
        self.name = name
        self.tools: List = []

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """Agent 的系统提示词"""
        pass

    def register_tool(self, tool):
        """注册工具"""
        self.tools.append(tool)

    def _get_llm(self):
        """获取 LLM 客户端（自动选择真实或模拟）"""
        from agents.llm_client import get_llm_client, MockLLMClient
        client = get_llm_client()
        if client.is_configured():
            return client
        return MockLLMClient()

    def _call_llm(self, user_message: str, temperature: float = 0.3) -> str:
        """调用 LLM"""
        llm = self._get_llm()
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_message},
        ]
        return llm.chat(messages, temperature=temperature)

    def _call_llm_with_tools(self, user_message: str) -> Dict:
        """带工具调用的 LLM 对话"""
        llm = self._get_llm()
        if isinstance(llm, type(self)._get_llm.__annotations__.get("return")):
            # 模拟客户端不支持工具调用，直接返回 chat 结果
            return {"content": llm.chat([{"role": "user", "content": user_message}])}

        tools = [t.to_openai_function() for t in self.tools]
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_message},
        ]
        return llm.chat_with_tools(messages, tools)

    @abstractmethod
    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Agent 执行逻辑

        Args:
            state: 当前工作流状态

        Returns:
            更新后的状态字典（部分 WorkflowState）
        """
        pass