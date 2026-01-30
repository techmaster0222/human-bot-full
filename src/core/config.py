"""
Configuration Management
Loads settings from YAML and environment variables.
"""

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from loguru import logger

# Try to load optional dependencies
try:
    import yaml

    HAS_YAML = True
except ImportError:
    HAS_YAML = False

try:
    from dotenv import load_dotenv

    HAS_DOTENV = True
except ImportError:
    HAS_DOTENV = False


@dataclass
class AdsPowerConfig:
    """AdsPower configuration"""

    api_url: str = "http://local.adspower.net:50325"
    api_key: str = ""
    default_group_id: str = ""


@dataclass
class ProxyConfig:
    """Proxy configuration"""

    provider: str = "iproyal"
    host: str = "geo.iproyal.com"
    port: int = 12321
    username: str = ""
    password: str = ""
    countries: list[str] = field(default_factory=lambda: ["US"])
    sticky_duration: int = 600


@dataclass
class BotConfig:
    """Bot behavior configuration"""

    typing_min_delay: float = 0.05
    typing_max_delay: float = 0.20
    typo_chance: float = 0.02
    mouse_speed: str = "human"
    min_session_duration: int = 300
    max_session_duration: int = 1800


@dataclass
class Config:
    """Main configuration container"""

    adspower: AdsPowerConfig = field(default_factory=AdsPowerConfig)
    proxy: ProxyConfig = field(default_factory=ProxyConfig)
    bot: BotConfig = field(default_factory=BotConfig)
    max_concurrent_profiles: int = 5
    log_level: str = "INFO"
    log_file: str = "logs/bot.log"


def find_project_root() -> Path:
    """Find project root directory"""
    current = Path.cwd()

    # Look for markers
    markers = ["main.py", "src", "config", ".env"]

    for parent in [current] + list(current.parents):
        if any((parent / marker).exists() for marker in markers):
            return parent

    return current


def load_env(env_path: Path = None) -> None:
    """Load environment variables from .env file"""
    if not HAS_DOTENV:
        logger.debug("python-dotenv not installed, skipping .env loading")
        return

    if env_path is None:
        env_path = find_project_root() / ".env"

    if env_path.exists():
        load_dotenv(env_path)
        logger.debug(f"Loaded environment from: {env_path}")
    else:
        logger.debug(f".env file not found at: {env_path}")


def load_yaml_config(config_path: Path = None) -> dict[str, Any]:
    """Load configuration from YAML file"""
    if not HAS_YAML:
        logger.debug("PyYAML not installed, using defaults")
        return {}

    if config_path is None:
        config_path = find_project_root() / "config" / "settings.yaml"

    if not config_path.exists():
        logger.debug(f"Config file not found: {config_path}")
        return {}

    try:
        with open(config_path) as f:
            config = yaml.safe_load(f) or {}
        logger.debug(f"Loaded config from: {config_path}")
        return config
    except Exception as e:
        logger.warning(f"Failed to load config: {e}")
        return {}


def load_config(config_path: Path = None, env_path: Path = None) -> Config:
    """
    Load configuration from files and environment.

    Priority (highest to lowest):
    1. Environment variables
    2. YAML config file
    3. Default values

    Args:
        config_path: Path to YAML config file
        env_path: Path to .env file

    Returns:
        Config instance
    """
    # Load .env first
    load_env(env_path)

    # Load YAML config
    yaml_config = load_yaml_config(config_path)

    # Build config with environment overrides
    config = Config()

    # AdsPower settings
    adspower_yaml = yaml_config.get("adspower", {})
    config.adspower = AdsPowerConfig(
        api_url=os.getenv(
            "ADSPOWER_API_URL", adspower_yaml.get("api_url", "http://local.adspower.net:50325")
        ),
        api_key=os.getenv("ADSPOWER_API_KEY", adspower_yaml.get("api_key", "")),
        default_group_id=os.getenv("ADSPOWER_GROUP_ID", adspower_yaml.get("default_group_id", "")),
    )

    # Proxy settings
    proxy_yaml = yaml_config.get("proxy", {})
    config.proxy = ProxyConfig(
        provider=proxy_yaml.get("provider", "iproyal"),
        host=os.getenv("IPROYAL_PROXY_HOST", proxy_yaml.get("host", "geo.iproyal.com")),
        port=int(os.getenv("IPROYAL_PROXY_PORT", proxy_yaml.get("port", 12321))),
        username=os.getenv("IPROYAL_USERNAME", proxy_yaml.get("username", "")),
        password=os.getenv("IPROYAL_PASSWORD", proxy_yaml.get("password", "")),
        countries=proxy_yaml.get("countries", ["US"]),
        sticky_duration=int(
            os.getenv("PROXY_STICKY_DURATION", proxy_yaml.get("sticky_duration", 600))
        ),
    )

    # Bot settings
    bot_yaml = yaml_config.get("bot", {})
    config.bot = BotConfig(
        typing_min_delay=float(bot_yaml.get("typing_min_delay", 0.05)),
        typing_max_delay=float(bot_yaml.get("typing_max_delay", 0.20)),
        typo_chance=float(bot_yaml.get("typo_chance", 0.02)),
        mouse_speed=bot_yaml.get("mouse_speed", "human"),
        min_session_duration=int(bot_yaml.get("min_session_duration", 300)),
        max_session_duration=int(bot_yaml.get("max_session_duration", 1800)),
    )

    # General settings
    config.max_concurrent_profiles = int(
        os.getenv("MAX_CONCURRENT_PROFILES", yaml_config.get("max_concurrent_profiles", 5))
    )
    config.log_level = os.getenv("LOG_LEVEL", yaml_config.get("log_level", "INFO"))
    config.log_file = yaml_config.get("log_file", "logs/bot.log")

    return config


def setup_logging(config: Config = None) -> None:
    """
    Configure loguru logging.

    Args:
        config: Config instance (uses defaults if not provided)
    """
    if config is None:
        config = Config()

    # Remove default handler
    logger.remove()

    # Console handler
    logger.add(
        sys.stderr,
        level=config.log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    )

    # File handler
    log_path = find_project_root() / config.log_file
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger.add(
        str(log_path), level="DEBUG", rotation="10 MB", retention="7 days", compression="zip"
    )

    logger.info(f"Logging configured: level={config.log_level}, file={log_path}")
