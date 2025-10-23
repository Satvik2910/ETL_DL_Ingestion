"""Configuration management for Driver Insight Agent."""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, Field


class APIConfig(BaseModel):
    """API configuration settings."""
    base_url: str = Field(..., description="Base URL for the driver API")
    pagination_size: int = Field(default=100, description="Number of items per page")
    max_retries: int = Field(default=3, description="Maximum number of retry attempts")
    timeout: float = Field(default=30.0, description="Request timeout in seconds")
    retry_delay: float = Field(default=1.0, description="Delay between retries in seconds")


class CacheConfig(BaseModel):
    """Cache configuration settings."""
    ttl: int = Field(default=600, description="Time to live in seconds")
    type: str = Field(default="memory", description="Cache type: memory or redis")
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis connection URL")
    max_size: int = Field(default=1000, description="Maximum cache size for memory cache")


class MCPToolsConfig(BaseModel):
    """MCP Tools configuration settings."""
    server_url: str = Field(..., description="URL of the MCP Tool Server")
    timeout: float = Field(default=10.0, description="Request timeout for MCP tools")
    max_retries: int = Field(default=2, description="Maximum retry attempts for MCP tools")


class ValidationConfig(BaseModel):
    """Validation configuration settings."""
    required_fields: List[str] = Field(default=["driver_id", "name"], description="Required fields in driver data")
    optional_fields: List[str] = Field(default=[], description="Optional fields in driver data")


class LoggingConfig(BaseModel):
    """Logging configuration settings."""
    level: str = Field(default="INFO", description="Logging level")
    format: str = Field(default="json", description="Log format: json or text")
    file: Optional[str] = Field(default=None, description="Log file path (optional)")


class ServerConfig(BaseModel):
    """Server configuration settings."""
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8080, description="Server port")
    debug: bool = Field(default=False, description="Debug mode")
    workers: int = Field(default=1, description="Number of worker processes")


class Config(BaseModel):
    """Main configuration class."""
    api: APIConfig
    cache: CacheConfig
    mcp_tools: MCPToolsConfig
    validation: ValidationConfig
    logging: LoggingConfig
    server: ServerConfig


class ConfigLoader:
    """Configuration loader utility."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the config loader.
        
        Args:
            config_path: Path to the configuration file. If None, uses default location.
        """
        if config_path is None:
            # Default to config.yaml in the same directory as this file
            config_dir = Path(__file__).parent
            config_path = config_dir / "config.yaml"
        
        self.config_path = Path(config_path)
    
    def load_config(self) -> Config:
        """Load configuration from YAML file.
        
        Returns:
            Config: Parsed configuration object
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If config file is invalid YAML
            ValueError: If config validation fails
        """
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
            # Override with environment variables if they exist
            config_data = self._apply_env_overrides(config_data)
            
            return Config(**config_data)
            
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Invalid YAML in config file: {e}")
        except Exception as e:
            raise ValueError(f"Configuration validation failed: {e}")
    
    def _apply_env_overrides(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply environment variable overrides to configuration.
        
        Environment variables should be prefixed with DIA_ (Driver Insight Agent)
        and use double underscores to separate nested keys.
        
        Example: DIA_API__BASE_URL=https://api.example.com
        
        Args:
            config_data: Original configuration data
            
        Returns:
            Dict: Configuration data with environment overrides applied
        """
        env_prefix = "DIA_"
        
        for key, value in os.environ.items():
            if not key.startswith(env_prefix):
                continue
            
            # Remove prefix and convert to lowercase
            config_key = key[len(env_prefix):].lower()
            
            # Split nested keys
            key_parts = config_key.split("__")
            
            # Navigate to the correct nested dictionary
            current_dict = config_data
            for part in key_parts[:-1]:
                if part not in current_dict:
                    current_dict[part] = {}
                current_dict = current_dict[part]
            
            # Set the value, attempting to convert to appropriate type
            final_key = key_parts[-1]
            current_dict[final_key] = self._convert_env_value(value)
        
        return config_data
    
    def _convert_env_value(self, value: str) -> Any:
        """Convert environment variable string to appropriate type.
        
        Args:
            value: Environment variable value as string
            
        Returns:
            Converted value (bool, int, float, or string)
        """
        # Try boolean conversion
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        
        # Try integer conversion
        try:
            return int(value)
        except ValueError:
            pass
        
        # Try float conversion
        try:
            return float(value)
        except ValueError:
            pass
        
        # Return as string
        return value


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get the global configuration instance.
    
    Returns:
        Config: The global configuration object
        
    Raises:
        RuntimeError: If configuration hasn't been loaded yet
    """
    global _config
    if _config is None:
        raise RuntimeError("Configuration not loaded. Call load_config() first.")
    return _config


def load_config(config_path: Optional[str] = None) -> Config:
    """Load and set the global configuration.
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        Config: The loaded configuration object
    """
    global _config
    loader = ConfigLoader(config_path)
    _config = loader.load_config()
    return _config


def reload_config(config_path: Optional[str] = None) -> Config:
    """Reload the global configuration.
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        Config: The reloaded configuration object
    """
    return load_config(config_path)