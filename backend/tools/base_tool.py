"""
zero_carbon_park_agent Agent 工具基类
定义可扩展的 Agent 工具注册与调用接口
"""
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict

logger = logging.getLogger(__name__)


class BaseTool(ABC):
    """Agent 工具基类

    所有工具需实现此接口，新工具只需实现 name、description、run 三个方法
    即可被 Agent 动态发现和调用。
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """工具名称（唯一标识）"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """工具描述（供 LLM 理解工具用途）"""
        pass

    @abstractmethod
    def run(self, **kwargs) -> str:
        """工具执行逻辑

        Returns:
            str: 工具执行结果（JSON 字符串或自然语言描述）
        """
        pass

    def _log_execution(self, **kwargs) -> None:
        """记录工具执行日志"""
        logger.info(f"Tool [{self.name}] executing with params: {kwargs}")

    def execute(self, **kwargs) -> str:
        """带日志和异常处理的工具执行入口

        子类应重写 run() 实现具体逻辑，调用方通过 execute() 统一调用。
        """
        self._log_execution(**kwargs)
        try:
            result = self.run(**kwargs)
            logger.info(f"Tool [{self.name}] executed successfully")
            return result
        except Exception as e:
            logger.error(f"Tool [{self.name}] execution failed: {e}", exc_info=True)
            import json
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    def to_langchain_tool(self):
        """转换为 LangChain 兼容的 Tool 格式"""
        from langchain.tools import tool

        @tool(self.name, description=self.description)
        def _tool(**kwargs) -> str:
            return self.run(**kwargs)

        return _tool

    def to_openai_function(self) -> Dict[str, Any]:
        """转换为 OpenAI function calling 格式"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self._get_parameters_schema(),
            }
        }

    def _get_parameters_schema(self) -> Dict[str, Any]:
        """子类可重写以提供参数 schema"""
        return {
            "type": "object",
            "properties": {},
            "required": [],
        }