"""
Configuration loader and parser for Driver Insight Agent.
"""
import os
import yaml
from typing import Any, Dict, Optional
from pathlib import Path


class Config:
    """Configuration manager for the Driver Insight Agent."""
    
    _instance: Optional['Config'] = None
    _config: Dict[str, Any] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._config:
            self.load_config()
    
    def load_config(self, config_path: Optional[str] = None) -> None:
        """Load configuration from YAML file."""
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(__file__), 
                'config.yaml'
            )
        
        with open(config_path, 'r') as f:
            self._config = yaml.safe_load(f)
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation.
        
        Example: config.get('cache.ttl_seconds')
        """
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        
        return value if value is not None else default
    
    def set(self, key: str, value: Any) -> None:
        """Set configuration value using dot notation."""
        keys = key.split('.')
        config = self._config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
    
    @property
    def cache_ttl(self) -> int:
        return self.get('cache.ttl_seconds', 3600)
    
    @property
    def cache_max_size(self) -> int:
        return self.get('cache.max_size', 1000)
    
    @property
    def max_workers(self) -> int:
        return self.get('concurrency.max_workers', 10)
    
    @property
    def batch_size(self) -> int:
        return self.get('concurrency.batch_size', 50)
    
    @property
    def default_page_size(self) -> int:
        return self.get('pagination.default_page_size', 100)
    
    @property
    def max_retry_attempts(self) -> int:
        return self.get('retry.max_attempts', 3)
    
    @property
    def backoff_base(self) -> int:
        return self.get('retry.backoff_base', 2)
    
    @property
    def summarization_max_tokens(self) -> int:
        return self.get('summarization.max_tokens', 500)


# Singleton instance
config = Config()
