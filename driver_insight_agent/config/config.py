"""Configuration management for Driver Insight Agent."""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class CacheConfig(BaseModel):
    """Cache configuration settings."""
    ttl_seconds: int = Field(default=3600, description="Default TTL for cache entries")
    persistent_cache: bool = Field(default=True, description="Enable persistent caching")
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis connection URL")
    max_cache_size: int = Field(default=10000, description="Maximum cached items")


class ExecutionConfig(BaseModel):
    """Execution configuration settings."""
    max_concurrent_requests: int = Field(default=10, description="Max concurrent requests")
    request_timeout_seconds: int = Field(default=30, description="Request timeout")
    retry_attempts: int = Field(default=3, description="Number of retry attempts")
    retry_backoff_multiplier: float = Field(default=2.0, description="Backoff multiplier")
    max_retry_delay: int = Field(default=60, description="Maximum retry delay")


class DataConfig(BaseModel):
    """Data processing configuration settings."""
    default_batch_size: int = Field(default=1000, description="Default batch size")
    max_batch_size: int = Field(default=10000, description="Maximum batch size")
    chunk_size: int = Field(default=500, description="Chunk size for processing")
    max_results_per_request: int = Field(default=50000, description="Max results per request")


class ToolConfig(BaseModel):
    """Individual tool configuration."""
    enabled: bool = Field(default=True, description="Tool enabled status")
    timeout: int = Field(default=10, description="Tool timeout in seconds")


class ToolsConfig(BaseModel):
    """Tools configuration settings."""
    driver_tool: ToolConfig = Field(default_factory=ToolConfig)
    trip_tool: ToolConfig = Field(default_factory=ToolConfig)
    score_tool: ToolConfig = Field(default_factory=ToolConfig)
    trend_tool: ToolConfig = Field(default_factory=ToolConfig)


class SummarizationConfig(BaseModel):
    """Summarization configuration settings."""
    max_summary_tokens: int = Field(default=2000, description="Maximum summary tokens")
    include_metadata: bool = Field(default=True, description="Include metadata in summaries")
    compression_ratio: float = Field(default=0.3, description="Target compression ratio")


class LoggingConfig(BaseModel):
    """Logging configuration settings."""
    level: str = Field(default="INFO", description="Logging level")
    structured: bool = Field(default=True, description="Use structured logging")
    include_timestamps: bool = Field(default=True, description="Include timestamps")


class Config(BaseModel):
    """Main configuration class."""
    cache: CacheConfig = Field(default_factory=CacheConfig)
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    data: DataConfig = Field(default_factory=DataConfig)
    tools: ToolsConfig = Field(default_factory=ToolsConfig)
    summarization: SummarizationConfig = Field(default_factory=SummarizationConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)


class ConfigManager:
    """Configuration manager for loading and managing configuration."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration manager."""
        self.config_path = config_path or self._get_default_config_path()
        self._config: Optional[Config] = None
    
    def _get_default_config_path(self) -> str:
        """Get default configuration file path."""
        current_dir = Path(__file__).parent
        return str(current_dir / "config.yaml")
    
    def load_config(self) -> Config:
        """Load configuration from file."""
        if self._config is not None:
            return self._config
        
        try:
            with open(self.config_path, 'r') as f:
                config_data = yaml.safe_load(f)
            
            # Override with environment variables
            config_data = self._apply_env_overrides(config_data)
            
            self._config = Config(**config_data)
            return self._config
        
        except FileNotFoundError:
            # Use default configuration if file not found
            self._config = Config()
            return self._config
        
        except Exception as e:
            raise RuntimeError(f"Failed to load configuration: {e}")
    
    def _apply_env_overrides(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply environment variable overrides to configuration."""
        env_mappings = {
            'REDIS_URL': ['cache', 'redis_url'],
            'MAX_CONCURRENT_REQUESTS': ['execution', 'max_concurrent_requests'],
            'DEFAULT_BATCH_SIZE': ['data', 'default_batch_size'],
            'LOG_LEVEL': ['logging', 'level'],
        }
        
        for env_var, config_path in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                # Navigate to the nested configuration
                current = config_data
                for key in config_path[:-1]:
                    if key not in current:
                        current[key] = {}
                    current = current[key]
                
                # Convert value to appropriate type
                final_key = config_path[-1]
                if final_key in ['max_concurrent_requests', 'default_batch_size']:
                    current[final_key] = int(env_value)
                else:
                    current[final_key] = env_value
        
        return config_data
    
    def get_config(self) -> Config:
        """Get loaded configuration."""
        if self._config is None:
            return self.load_config()
        return self._config


# Global configuration instance
config_manager = ConfigManager()


def get_config() -> Config:
    """Get the global configuration instance."""
    return config_manager.get_config()