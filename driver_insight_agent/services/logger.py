"""Structured logging service for Driver Insight Agent."""

import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict, Optional

from ..config import get_config


class StructuredLogger:
    """Structured logger with contextual information."""
    
    def __init__(self, name: str = "driver_insight_agent"):
        """Initialize the structured logger.
        
        Args:
            name: Logger name
        """
        self.logger = logging.getLogger(name)
        self._setup_logger()
    
    def _setup_logger(self):
        """Setup logger configuration based on config settings."""
        try:
            config = get_config()
            log_config = config.logging
        except RuntimeError:
            # Fallback configuration if config not loaded
            log_config = type('LogConfig', (), {
                'level': 'INFO',
                'format': 'json',
                'file': None
            })()
        
        # Set log level
        level = getattr(logging, log_config.level.upper(), logging.INFO)
        self.logger.setLevel(level)
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Create formatter
        if log_config.format.lower() == 'json':
            formatter = JsonFormatter()
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # File handler (if configured)
        if log_config.file:
            file_handler = logging.FileHandler(log_config.file)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
        
        # Prevent duplicate logs
        self.logger.propagate = False
    
    def _log_with_context(self, level: int, message: str, context: Optional[Dict[str, Any]] = None, **kwargs):
        """Log message with contextual information.
        
        Args:
            level: Log level
            message: Log message
            context: Additional context dictionary
            **kwargs: Additional keyword arguments
        """
        extra_context = {
            'timestamp': datetime.utcnow().isoformat(),
            'service': 'driver_insight_agent',
        }
        
        if context:
            extra_context.update(context)
        
        if kwargs:
            extra_context.update(kwargs)
        
        # Use extra parameter for structured logging
        self.logger.log(level, message, extra=extra_context)
    
    def debug(self, message: str, context: Optional[Dict[str, Any]] = None, **kwargs):
        """Log debug message."""
        self._log_with_context(logging.DEBUG, message, context, **kwargs)
    
    def info(self, message: str, context: Optional[Dict[str, Any]] = None, **kwargs):
        """Log info message."""
        self._log_with_context(logging.INFO, message, context, **kwargs)
    
    def warning(self, message: str, context: Optional[Dict[str, Any]] = None, **kwargs):
        """Log warning message."""
        self._log_with_context(logging.WARNING, message, context, **kwargs)
    
    def error(self, message: str, context: Optional[Dict[str, Any]] = None, **kwargs):
        """Log error message."""
        self._log_with_context(logging.ERROR, message, context, **kwargs)
    
    def critical(self, message: str, context: Optional[Dict[str, Any]] = None, **kwargs):
        """Log critical message."""
        self._log_with_context(logging.CRITICAL, message, context, **kwargs)
    
    def log_api_request(self, method: str, url: str, status_code: Optional[int] = None, 
                       duration: Optional[float] = None, **kwargs):
        """Log API request with standardized format.
        
        Args:
            method: HTTP method
            url: Request URL
            status_code: Response status code
            duration: Request duration in seconds
            **kwargs: Additional context
        """
        context = {
            'event_type': 'api_request',
            'http_method': method,
            'url': url,
            'status_code': status_code,
            'duration_seconds': duration,
        }
        context.update(kwargs)
        
        if status_code and status_code >= 400:
            self.error(f"API request failed: {method} {url}", context)
        else:
            self.info(f"API request: {method} {url}", context)
    
    def log_cache_operation(self, operation: str, key: str, hit: Optional[bool] = None, **kwargs):
        """Log cache operation with standardized format.
        
        Args:
            operation: Cache operation (get, set, delete, etc.)
            key: Cache key
            hit: Whether it was a cache hit (for get operations)
            **kwargs: Additional context
        """
        context = {
            'event_type': 'cache_operation',
            'operation': operation,
            'cache_key': key,
            'cache_hit': hit,
        }
        context.update(kwargs)
        
        self.debug(f"Cache {operation}: {key}", context)
    
    def log_mcp_tool_invocation(self, tool_name: str, success: bool, duration: Optional[float] = None, **kwargs):
        """Log MCP tool invocation with standardized format.
        
        Args:
            tool_name: Name of the MCP tool
            success: Whether the invocation was successful
            duration: Invocation duration in seconds
            **kwargs: Additional context
        """
        context = {
            'event_type': 'mcp_tool_invocation',
            'tool_name': tool_name,
            'success': success,
            'duration_seconds': duration,
        }
        context.update(kwargs)
        
        if success:
            self.info(f"MCP tool invocation successful: {tool_name}", context)
        else:
            self.error(f"MCP tool invocation failed: {tool_name}", context)
    
    def log_validation_result(self, data_type: str, valid: bool, errors: Optional[list] = None, **kwargs):
        """Log validation result with standardized format.
        
        Args:
            data_type: Type of data being validated
            valid: Whether validation passed
            errors: List of validation errors (if any)
            **kwargs: Additional context
        """
        context = {
            'event_type': 'validation',
            'data_type': data_type,
            'valid': valid,
            'validation_errors': errors,
        }
        context.update(kwargs)
        
        if valid:
            self.debug(f"Validation passed: {data_type}", context)
        else:
            self.warning(f"Validation failed: {data_type}", context)


class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON.
        
        Args:
            record: Log record to format
            
        Returns:
            JSON formatted log string
        """
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }
        
        # Add extra fields from the record
        for key, value in record.__dict__.items():
            if key not in ('name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                          'filename', 'module', 'lineno', 'funcName', 'created',
                          'msecs', 'relativeCreated', 'thread', 'threadName',
                          'processName', 'process', 'getMessage', 'exc_info',
                          'exc_text', 'stack_info'):
                log_data[key] = value
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, default=str)


# Global logger instance
_logger: Optional[StructuredLogger] = None


def get_logger(name: str = "driver_insight_agent") -> StructuredLogger:
    """Get the global logger instance.
    
    Args:
        name: Logger name
        
    Returns:
        StructuredLogger: The logger instance
    """
    global _logger
    if _logger is None:
        _logger = StructuredLogger(name)
    return _logger