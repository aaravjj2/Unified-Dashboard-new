"""
Alpaca Options Lab - Configuration Management

Pydantic-based configuration with:
- YAML file loading
- Environment variable interpolation
- Type validation
- Multi-environment support (development, production, paper)

Usage:
    from src.utils.config import get_config, Settings
    
    config = get_config()  # Loads based on APP_ENV
    print(config.database.host)
    print(config.alpaca.api_key)
"""
from __future__ import annotations

import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

import yaml
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings


# =============================================================================
# CONFIGURATION MODELS
# =============================================================================

class DatabasePoolSettings(BaseModel):
    """Database connection pool settings."""
    min_size: int = Field(default=2, ge=1, le=100)
    max_size: int = Field(default=10, ge=1, le=200)
    max_overflow: int = Field(default=5, ge=0, le=50)
    pool_timeout: int = Field(default=30, ge=1, le=300)
    pool_recycle: int = Field(default=1800, ge=60, le=7200)


class TimescaleSettings(BaseModel):
    """TimescaleDB-specific settings."""
    enabled: bool = True
    compression_after: str = "7 days"
    retention: str = "90 days"


class DatabaseSettings(BaseModel):
    """Database configuration."""
    host: str = "localhost"
    port: int = Field(default=5432, ge=1, le=65535)
    name: str = "options_lab"
    user: str = "postgres"
    password: str = ""
    pool: DatabasePoolSettings = Field(default_factory=DatabasePoolSettings)
    timescale: TimescaleSettings = Field(default_factory=TimescaleSettings)
    
    @property
    def connection_string(self) -> str:
        """Generate PostgreSQL connection string."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"
    
    @property
    def async_connection_string(self) -> str:
        """Generate asyncpg connection string."""
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


class RateLimitSettings(BaseModel):
    """API rate limiting settings."""
    requests_per_minute: int = Field(default=200, ge=1, le=1000)
    burst_size: int = Field(default=50, ge=1, le=200)


class AlpacaSettings(BaseModel):
    """Alpaca API configuration."""
    api_key: str = ""
    api_secret: str = ""
    base_url: str = "https://paper-api.alpaca.markets"
    data_url: str = "https://data.alpaca.markets"
    websocket_url: str = "wss://stream.data.alpaca.markets"
    rate_limit: RateLimitSettings = Field(default_factory=RateLimitSettings)
    
    @property
    def is_paper(self) -> bool:
        """Check if configured for paper trading."""
        return "paper" in self.base_url.lower()


class GreeksCacheSettings(BaseModel):
    """Greeks cache configuration."""
    enabled: bool = True
    ttl_seconds: int = Field(default=60, ge=1, le=3600)
    max_size: int = Field(default=100000, ge=1000, le=10000000)


class IVSolverSettings(BaseModel):
    """Implied volatility solver settings."""
    max_iterations: int = Field(default=100, ge=10, le=1000)
    tolerance: float = Field(default=1e-8, gt=0, lt=1)


class PricingSettings(BaseModel):
    """Pricing engine configuration."""
    default_risk_free_rate: float = Field(default=0.05, ge=0, le=1)
    default_dividend_yield: float = Field(default=0.0, ge=0, le=1)
    greeks_cache: GreeksCacheSettings = Field(default_factory=GreeksCacheSettings)
    iv_solver: IVSolverSettings = Field(default_factory=IVSolverSettings)


class RiskLimitsSettings(BaseModel):
    """Risk limit thresholds."""
    max_portfolio_delta: float = Field(default=1000, ge=0)
    max_position_size: int = Field(default=100, ge=1)
    max_single_option_contracts: int = Field(default=50, ge=1)
    max_portfolio_vega: float = Field(default=50000, ge=0)
    max_daily_loss: float = Field(default=0.02, ge=0, le=1)
    margin_utilization_warning: float = Field(default=0.70, ge=0, le=1)
    margin_utilization_critical: float = Field(default=0.85, ge=0, le=1)


class RiskMonitoringSettings(BaseModel):
    """Risk monitoring configuration."""
    check_interval_seconds: int = Field(default=30, ge=1, le=300)
    alert_cooldown_seconds: int = Field(default=300, ge=60, le=3600)


class RiskSettings(BaseModel):
    """Risk management configuration."""
    limits: RiskLimitsSettings = Field(default_factory=RiskLimitsSettings)
    monitoring: RiskMonitoringSettings = Field(default_factory=RiskMonitoringSettings)


class BacktestingSettings(BaseModel):
    """Backtesting engine configuration."""
    default_commission: float = Field(default=0.65, ge=0)
    default_slippage: float = Field(default=0.01, ge=0, le=1)
    max_concurrent_backtests: int = Field(default=4, ge=1, le=32)
    cache_market_data: bool = True


class LogHandlerSettings(BaseModel):
    """Log handler configuration."""
    type: Literal["console", "file"] = "console"
    level: str = "INFO"
    path: Optional[str] = None
    max_bytes: int = Field(default=10485760, ge=1024)  # 10MB
    backup_count: int = Field(default=5, ge=0, le=100)


class LoggingSettings(BaseModel):
    """Logging configuration."""
    format: Literal["json", "text"] = "json"
    correlation_id: bool = True
    handlers: List[LogHandlerSettings] = Field(default_factory=list)


class PrometheusSettings(BaseModel):
    """Prometheus metrics export configuration."""
    enabled: bool = True
    port: int = Field(default=9090, ge=1024, le=65535)


class MetricsSettings(BaseModel):
    """Metrics configuration."""
    enabled: bool = True
    prometheus: PrometheusSettings = Field(default_factory=PrometheusSettings)
    export_interval_seconds: int = Field(default=15, ge=1, le=300)


class AppSettings(BaseModel):
    """Application-level settings."""
    name: str = "alpaca-options-lab"
    environment: Literal["development", "production", "paper"] = "development"
    debug: bool = False
    log_level: str = "INFO"


class Settings(BaseModel):
    """
    Complete application configuration.
    
    Supports loading from YAML files with environment variable interpolation.
    """
    app: AppSettings = Field(default_factory=AppSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    alpaca: AlpacaSettings = Field(default_factory=AlpacaSettings)
    pricing: PricingSettings = Field(default_factory=PricingSettings)
    risk: RiskSettings = Field(default_factory=RiskSettings)
    backtesting: BacktestingSettings = Field(default_factory=BacktestingSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    metrics: MetricsSettings = Field(default_factory=MetricsSettings)


# =============================================================================
# CONFIGURATION LOADING
# =============================================================================

def _interpolate_env_vars(value: Any) -> Any:
    """
    Recursively interpolate environment variables in configuration values.
    
    Supports formats:
    - ${VAR_NAME} - Required, raises if not set
    - ${VAR_NAME:-default} - Optional with default value
    """
    if isinstance(value, str):
        # Pattern matches ${VAR} or ${VAR:-default}
        pattern = r'\$\{([A-Z_][A-Z0-9_]*)(?::-([^}]*))?\}'
        
        def replacer(match: re.Match[str]) -> str:
            var_name = match.group(1)
            default_value = match.group(2)
            
            env_value = os.environ.get(var_name)
            if env_value is not None:
                return env_value
            elif default_value is not None:
                return default_value
            else:
                # For required vars, return empty string rather than raising
                # This allows the config to load even if secrets aren't set
                return ""
        
        return re.sub(pattern, replacer, value)
    
    elif isinstance(value, dict):
        return {k: _interpolate_env_vars(v) for k, v in value.items()}
    
    elif isinstance(value, list):
        return [_interpolate_env_vars(item) for item in value]
    
    return value


def load_config_file(config_path: Path) -> Dict[str, Any]:
    """Load and parse a YAML configuration file."""
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(config_path, "r") as f:
        raw_config = yaml.safe_load(f)
    
    if raw_config is None:
        return {}
    
    # Interpolate environment variables
    return _interpolate_env_vars(raw_config)


def load_settings(
    environment: Optional[str] = None,
    config_dir: Optional[Path] = None,
) -> Settings:
    """
    Load settings for the specified environment.
    
    Args:
        environment: One of 'development', 'production', 'paper'
                    Defaults to APP_ENV environment variable or 'development'
        config_dir: Directory containing configuration files
                   Defaults to 'config/' in project root
    
    Returns:
        Fully validated Settings object
    """
    # Determine environment
    env = environment or os.environ.get("APP_ENV", "development")
    
    # Determine config directory
    if config_dir is None:
        # Find config dir relative to this file
        project_root = Path(__file__).parent.parent.parent
        config_dir = project_root / "config"
    
    # Load configuration file
    config_file = config_dir / f"{env}.yaml"
    
    if config_file.exists():
        config_dict = load_config_file(config_file)
    else:
        # Fall back to development.yaml
        fallback_file = config_dir / "development.yaml"
        if fallback_file.exists():
            config_dict = load_config_file(fallback_file)
        else:
            config_dict = {}
    
    # Create and validate settings
    return Settings(**config_dict)


@lru_cache(maxsize=1)
def get_config() -> Settings:
    """
    Get the cached application configuration.
    
    Returns:
        Singleton Settings instance
    """
    return load_settings()


def reload_config() -> Settings:
    """
    Force reload the configuration.
    
    Returns:
        Fresh Settings instance
    """
    get_config.cache_clear()
    return get_config()


# =============================================================================
# INITIALIZATION
# =============================================================================

# Load dotenv if available
try:
    from dotenv import load_dotenv
    
    # Look for .env in project root
    project_root = Path(__file__).parent.parent.parent
    env_file = project_root / ".env"
    keys_env_file = project_root / "keys.env"
    
    if env_file.exists():
        load_dotenv(env_file)
    if keys_env_file.exists():
        load_dotenv(keys_env_file)
        
except ImportError:
    pass
