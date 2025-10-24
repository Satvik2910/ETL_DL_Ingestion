"""
Driver Insight Agent - Modular analytics agent for driver insights.
"""
__version__ = "1.0.0"
__author__ = "Driver Insight Team"
__description__ = "Modular analytics agent for comprehensive driver insights"

from agent.core import DriverInsightAgent
from agent.abstract_card import AgentAbstractCard

__all__ = ["DriverInsightAgent", "AgentAbstractCard"]
