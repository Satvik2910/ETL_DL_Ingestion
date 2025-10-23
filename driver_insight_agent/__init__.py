"""Driver Insight Agent - A modular agent for fetching and managing driver data efficiently."""

from .driver_insight_agent import DriverInsightAgent, get_driver_insight_agent, DriverInsightAgentError
from .config import load_config, get_config
from .app import app

__version__ = "1.0.0"
__author__ = "Driver Insight Team"
__description__ = "A modular agent responsible for fetching and managing driver data efficiently from external APIs"

__all__ = [
    "DriverInsightAgent",
    "get_driver_insight_agent", 
    "DriverInsightAgentError",
    "load_config",
    "get_config",
    "app",
]