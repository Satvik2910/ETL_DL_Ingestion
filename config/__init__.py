"""
Configuration module for Driver Insight Agent.
Handles loading and managing configuration from YAML and environment variables.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from pydantic import BaseModel, Field


class APIConfig(BaseModel):
    """API configuration settings."""
    base_url: str = Field(default="https://external.driver.api")
    timeout: int = Field(default=30)
    max_retries: int = Field(default=3)
    retry_delay: int = Field(default=1)


class PaginationConfig(BaseModel):
    """Pagination configuration settings."""
    page_size: int = Field(default=100)
    max_pages: int = Field(default=50)


class RedisConfig(BaseModel):
    """Redis configuration settings."""
    host: str = Field(default="localhost")
    port: int = Field(default=6379)
    db: int = Field(default=0)
    password: Optional[str] = Field(default=None)


class CacheConfig(BaseModel):
    """Cache configuration settings."""
    enabled: bool = Field(default=True)
    ttl: int = Field(default=600)
    type: str = Field(default="memory")
    redis: RedisConfig = Field(default_factory=RedisConfig)


class MCPToolServerConfig(BaseModel):
    """MCP Tool Server configuration settings."""
    url: str = Field(default="http://localhost:8081/mcp-tools")
    timeout: int = Field(default=10)
    enabled: bool = Field(default=True)


class ValidationConfig(BaseModel):
    """Validation configuration settings."""
    required_fields: list[str] = Field(default=["driver_id", "name"])
    strict_mode: bool = Field(default=False)


class LoggingConfig(BaseModel):
    """Logging configuration settings."""
    level: str = Field(default="INFO")
    format: str = Field(default="json")
    output: str = Field(default="stdout")


class ServiceConfig(BaseModel):
    """Service configuration settings."""
    name: str = Field(default="driver-insight-agent")
    version: str = Field(default="1.0.0")
    port: int = Field(default=8080)
    host: str = Field(default="0.0.0.0")


class Config(BaseModel):
    """Main configuration class."""
    api: APIConfig = Field(default_factory=APIConfig)
    pagination: PaginationConfig = Field(default_factory=PaginationConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    mcp_tool_server: MCPToolServerConfig = Field(default_factory=MCPToolServerConfig)
    validation: ValidationConfig = Field(default_factory=ValidationConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    service: ServiceConfig = Field(default_factory=ServiceConfig)


class ConfigLoader:
    """
    Configuration loader that reads from YAML file and overrides with environment variables.
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the configuration loader.

        Args:
            config_path: Path to the YAML configuration file.
        """
        self.config_path = config_path or self._get_default_config_path()
        self._config: Optional[Config] = None

    @staticmethod
    def _get_default_config_path() -> str:
        """Get the default configuration file path."""
        current_dir = Path(__file__).parent.parent
        return str(current_dir / "config.yaml")

    def _load_yaml_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(self.config_path, "r") as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            print(f"Warning: Config file not found at {self.config_path}, using defaults")
            return {}
        except yaml.YAMLError as e:
            print(f"Warning: Error parsing YAML config: {e}, using defaults")
            return {}

    def _apply_env_overrides(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Apply environment variable overrides to configuration."""
        # API overrides
        if api_url := os.getenv("API_BASE_URL"):
            config_dict.setdefault("api", {})["base_url"] = api_url
        if api_timeout := os.getenv("API_TIMEOUT"):
            config_dict.setdefault("api", {})["timeout"] = int(api_timeout)
        if api_retries := os.getenv("API_MAX_RETRIES"):
            config_dict.setdefault("api", {})["max_retries"] = int(api_retries)

        # Cache overrides
        if cache_enabled := os.getenv("CACHE_ENABLED"):
            config_dict.setdefault("cache", {})["enabled"] = cache_enabled.lower() == "true"
        if cache_ttl := os.getenv("CACHE_TTL"):
            config_dict.setdefault("cache", {})["ttl"] = int(cache_ttl)
        if cache_type := os.getenv("CACHE_TYPE"):
            config_dict.setdefault("cache", {})["type"] = cache_type

        # Redis overrides
        if redis_host := os.getenv("REDIS_HOST"):
            config_dict.setdefault("cache", {}).setdefault("redis", {})["host"] = redis_host
        if redis_port := os.getenv("REDIS_PORT"):
            config_dict.setdefault("cache", {}).setdefault("redis", {})["port"] = int(redis_port)
        if redis_password := os.getenv("REDIS_PASSWORD"):
            config_dict.setdefault("cache", {}).setdefault("redis", {})["password"] = redis_password

        # MCP Tool Server overrides
        if mcp_url := os.getenv("MCP_TOOL_SERVER_URL"):
            config_dict.setdefault("mcp_tool_server", {})["url"] = mcp_url
        if mcp_enabled := os.getenv("MCP_ENABLED"):
            config_dict.setdefault("mcp_tool_server", {})["enabled"] = mcp_enabled.lower() == "true"

        # Service overrides
        if service_port := os.getenv("SERVICE_PORT"):
            config_dict.setdefault("service", {})["port"] = int(service_port)
        if service_host := os.getenv("SERVICE_HOST"):
            config_dict.setdefault("service", {})["host"] = service_host

        # Logging overrides
        if log_level := os.getenv("LOG_LEVEL"):
            config_dict.setdefault("logging", {})["level"] = log_level
        if log_format := os.getenv("LOG_FORMAT"):
            config_dict.setdefault("logging", {})["format"] = log_format

        return config_dict

    def load(self) -> Config:
        """
        Load configuration from YAML and apply environment overrides.

        Returns:
            Config: The loaded configuration object.
        """
        if self._config is not None:
            return self._config

        config_dict = self._load_yaml_config()
        config_dict = self._apply_env_overrides(config_dict)

        self._config = Config(**config_dict)
        return self._config

    def reload(self) -> Config:
        """
        Reload configuration from file and environment.

        Returns:
            Config: The reloaded configuration object.
        """
        self._config = None
        return self.load()


# Global configuration instance
_config_loader = ConfigLoader()


def get_config() -> Config:
    """
    Get the global configuration instance.

    Returns:
        Config: The configuration object.
    """
    return _config_loader.load()


def reload_config() -> Config:
    """
    Reload the global configuration.

    Returns:
        Config: The reloaded configuration object.
    """
    return _config_loader.reload()
