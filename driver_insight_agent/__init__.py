"""Driver Insight Agent - Comprehensive driver analytics and reporting system."""

__version__ = "1.0.0"
__author__ = "Driver Analytics Team"
__description__ = "Modular Driver Insight Agent for handling all driver analytics and reporting tasks"

from .agent.core import DriverInsightAgentCore
from .agent.abstract_card import DriverInsightAgentCard
from .agent.mcp_registry import get_mcp_registry

__all__ = [
    "DriverInsightAgentCore",
    "DriverInsightAgentCard", 
    "get_mcp_registry"
]