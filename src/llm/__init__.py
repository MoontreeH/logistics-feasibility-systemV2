"""
LLM模块

提供自然语言理解能力，包括：
- 意图识别
- 实体抽取
- 参数校验
- 多轮对话
- 订单利润评估
- LLM-native对话引擎（真正以LLM为核心）
"""

from .client import SiliconFlowClient
from .intent_classifier import IntentClassifier
from .entity_extractor import EntityExtractor
from .parameter_validator import ParameterValidator
from .dialogue_manager import DialogueManager
from .cost_link_identifier import CostLinkIdentifier, CostLinkConfirmationHandler
from .order_profit_handler import (
    OrderProfitHandler,
    OrderProfitIntentDetector,
    OrderProfitInputCollector,
    should_trigger_profit_assessment
)
from .smart_parameter_collector import SmartParameterCollector, ParameterStatus
from .llm_native_engine import LLMMissionEngine, LLMMissionEngineV2, TaskType, DataSource, ConversationContext

__all__ = [
    "SiliconFlowClient",
    "IntentClassifier",
    "EntityExtractor",
    "ParameterValidator",
    "DialogueManager",
    "CostLinkIdentifier",
    "CostLinkConfirmationHandler",
    "OrderProfitHandler",
    "OrderProfitIntentDetector",
    "OrderProfitInputCollector",
    "should_trigger_profit_assessment",
    "SmartParameterCollector",
    "ParameterStatus",
    "LLMMissionEngine",
    "LLMMissionEngineV2",
    "TaskType",
    "DataSource",
    "ConversationContext",
]
