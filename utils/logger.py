"""
Structured logging utility for Driver Insight Agent.
Provides JSON and text formatted logging with context support.
"""

import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict, Optional

from config import get_config


class StructuredLogger:
    """
    Structured logger that supports both JSON and text formats.
    Includes context management for adding metadata to log entries.
    """

    def __init__(self, name: str, context: Optional[Dict[str, Any]] = None):
        """
        Initialize the structured logger.

        Args:
            name: Logger name (typically module or service name).
            context: Default context to include in all log entries.
        """
        self.name = name
        self.context = context or {}
        self.logger = logging.getLogger(name)
        self._configure_logger()

    def _configure_logger(self):
        """Configure the logger based on configuration settings."""
        config = get_config()
        log_config = config.logging

        # Set log level
        level = getattr(logging, log_config.level.upper(), logging.INFO)
        self.logger.setLevel(level)

        # Remove existing handlers
        self.logger.handlers.clear()

        # Create handler
        if log_config.output == "stdout":
            handler = logging.StreamHandler(sys.stdout)
        else:
            handler = logging.FileHandler(log_config.output)

        # Set formatter
        if log_config.format == "json":
            handler.setFormatter(JSONFormatter())
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)

        self.logger.addHandler(handler)
        self.logger.propagate = False

    def _build_log_data(self, message: str, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Build log data with context and extra information.

        Args:
            message: Log message.
            extra: Additional data to include in the log.

        Returns:
            Dict containing all log data.
        """
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "service": get_config().service.name,
            "logger": self.name,
            "message": message,
        }

        # Add context
        if self.context:
            log_data["context"] = self.context

        # Add extra data
        if extra:
            log_data["extra"] = extra

        return log_data

    def debug(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """Log debug message."""
        log_data = self._build_log_data(message, extra)
        self.logger.debug(message, extra={"structured_data": log_data})

    def info(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """Log info message."""
        log_data = self._build_log_data(message, extra)
        self.logger.info(message, extra={"structured_data": log_data})

    def warning(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """Log warning message."""
        log_data = self._build_log_data(message, extra)
        self.logger.warning(message, extra={"structured_data": log_data})

    def error(self, message: str, extra: Optional[Dict[str, Any]] = None, exc_info: bool = False):
        """Log error message."""
        log_data = self._build_log_data(message, extra)
        self.logger.error(message, extra={"structured_data": log_data}, exc_info=exc_info)

    def critical(self, message: str, extra: Optional[Dict[str, Any]] = None, exc_info: bool = False):
        """Log critical message."""
        log_data = self._build_log_data(message, extra)
        self.logger.critical(message, extra={"structured_data": log_data}, exc_info=exc_info)

    def with_context(self, **kwargs) -> "StructuredLogger":
        """
        Create a new logger with additional context.

        Args:
            **kwargs: Additional context key-value pairs.

        Returns:
            New logger instance with merged context.
        """
        new_context = {**self.context, **kwargs}
        return StructuredLogger(self.name, context=new_context)


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for log records."""

    def format(self, record: logging.LogRecord) -> str:
        """
        Format the log record as JSON.

        Args:
            record: The log record to format.

        Returns:
            JSON formatted log string.
        """
        # Check if structured data is available
        if hasattr(record, "structured_data"):
            log_data = record.structured_data
            log_data["level"] = record.levelname
        else:
            # Fallback for standard log records
            log_data = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
            }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


def get_logger(name: str, context: Optional[Dict[str, Any]] = None) -> StructuredLogger:
    """
    Get a structured logger instance.

    Args:
        name: Logger name.
        context: Default context for the logger.

    Returns:
        StructuredLogger instance.
    """
    return StructuredLogger(name, context)
