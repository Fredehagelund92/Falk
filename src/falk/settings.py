"""Configuration for falk.

Loads configuration from:
1. falk_project.yaml (agent behavior, extensions, access control)
2. semantic_models.yaml (BSL - metrics and dimensions)
3. Environment variables (.env)
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


@dataclass(frozen=True)
class AgentConfig:
    """Agent behavior configuration."""
    provider: str = "openai"
    model: str = "gpt-4o-mini"
    context: str = ""
    examples: list[str] = field(default_factory=list)
    rules: list[str] = field(default_factory=list)
    welcome: str = ""


@dataclass(frozen=True)
class AdvancedConfig:
    """Technical settings (hidden from analyst-facing config)."""
    auto_run: bool = False
    max_tokens: int = 4096
    temperature: float = 0.1
    max_rows_per_query: int = 10000
    query_timeout_seconds: int = 30
    max_retries: int = 3
    retry_delay_seconds: int = 1
    log_level: str = "INFO"


@dataclass(frozen=True)
class ExtensionConfig:
    """Extension configuration."""
    enabled: bool = False
    settings: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AccessConfig:
    """Data access control configuration."""
    access_policy: str | None = None  # Path to policy file; if set and exists, enabled


@dataclass(frozen=True)
class SkillsConfig:
    """Agent skills configuration (pydantic-ai-skills)."""
    enabled: bool = False
    directories: list[str] = field(default_factory=lambda: ["./skills"])


@dataclass(frozen=True)
class Settings:
    """Complete falk configuration."""
    # Core paths
    project_root: Path
    bsl_models_path: Path

    # Connection (inline dict from falk_project.yaml, passed to BSL get_connection)
    connection: dict[str, Any]

    # Configuration objects
    agent: AgentConfig
    advanced: AdvancedConfig
    extensions: dict[str, ExtensionConfig]
    access: AccessConfig
    skills: SkillsConfig
    
    # Optional paths
    access_policy_path: Path | None = None

    # Slack (from env)
    slack_bot_token: str | None = None
    slack_app_token: str | None = None


def _find_project_root() -> Path:
    """Find project root by looking for falk config files or .env file."""
    current = Path.cwd().resolve()
    
    # Check current directory and parents
    for path in [current] + list(current.parents):
        # Look for falk config files in project root
        if (path / "falk_project.yaml").exists():
            return path
        if (path / "semantic_models.yaml").exists():
            return path
        # Look for .env file
        if (path / ".env").exists():
            return path
    
    # Fallback to current directory
    return current


def _load_yaml_config(path: Path) -> dict[str, Any]:
    """Load and parse YAML config file."""
    if not path.exists():
        return {}
    
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_settings() -> Settings:
    """Load falk configuration.
    
    Process:
    1. Find project root
    2. Load .env file
    3. Load falk_project.yaml (if exists)
    4. Resolve all paths
    5. Build Settings object
    """
    # 1. Find project root
    project_root = _find_project_root()
    
    # 2. Load .env file
    env_file = project_root / ".env"
    if env_file.exists():
        load_dotenv(env_file)
    
    # 3. Load falk_project.yaml
    config_file = project_root / "falk_project.yaml"
    config = _load_yaml_config(config_file)
    
    # 4. Parse agent config (analyst-facing)
    agent_config = config.get("agent") or {}
    agent = AgentConfig(
        provider=agent_config.get("provider", "openai"),
        model=agent_config.get("model", "gpt-4o-mini"),
        context=agent_config.get("context", ""),
        examples=agent_config.get("examples", []),
        rules=agent_config.get("rules", []),
        welcome=agent_config.get("welcome", ""),
    )

    # 4b. Parse advanced config (technical settings)
    advanced_config = config.get("advanced") or {}
    advanced = AdvancedConfig(
        auto_run=advanced_config.get("auto_run", False),
        max_tokens=advanced_config.get("max_tokens", 4096),
        temperature=advanced_config.get("temperature", 0.1),
        max_rows_per_query=advanced_config.get("max_rows_per_query", 10000),
        query_timeout_seconds=advanced_config.get("query_timeout_seconds", 30),
        max_retries=advanced_config.get("max_retries", 3),
        retry_delay_seconds=advanced_config.get("retry_delay_seconds", 1),
        log_level=advanced_config.get("log_level", "INFO"),
    )
    
    # 5. Parse extensions
    extensions_config = config.get("extensions") or {}
    extensions = {}
    for name, ext_config in extensions_config.items():
        if isinstance(ext_config, dict):
            enabled = ext_config.get("enabled", False)
            # Remove 'enabled' from settings dict
            settings = {k: v for k, v in ext_config.items() if k != "enabled"}
            extensions[name] = ExtensionConfig(enabled=enabled, settings=settings)
        else:
            extensions[name] = ExtensionConfig(enabled=False)
    
    # 6. Parse access control
    access_config = config.get("access") or {}
    access = AccessConfig(
        access_policy=access_config.get("access_policy"),
    )
    
    # 6b. Parse skills configuration
    skills_config = config.get("skills") or {}
    skills = SkillsConfig(
        enabled=skills_config.get("enabled", False),
        directories=skills_config.get("directories", ["./skills"]),
    )
    
    # 7. Parse connection (inline in falk_project.yaml)
    connection = config.get("connection")
    if not connection or not isinstance(connection, dict):
        # Default: DuckDB warehouse for falk init
        connection = {"type": "duckdb", "database": "data/warehouse.duckdb"}
    else:
        connection = dict(connection)
    # Resolve relative database paths (e.g. DuckDB file) to project root
    if "database" in connection and isinstance(connection["database"], str):
        db_path = Path(connection["database"])
        if not db_path.is_absolute():
            connection = {**connection, "database": str(project_root / db_path)}

    # 8. Resolve paths
    paths_config = config.get("paths") or {}

    # BSL models path (project root / semantic_models.yaml)
    bsl_path = Path(
        os.getenv("BSL_MODELS_PATH")
        or paths_config.get("semantic_models")
        or "semantic_models.yaml"
    )
    if not bsl_path.is_absolute():
        bsl_path = project_root / bsl_path
    bsl_path = bsl_path.resolve()
    
    # Access policy (optional) — if set and file exists, enabled
    access_policy_path = None
    if access.access_policy:
        policy_file = project_root / access.access_policy
        if policy_file.exists():
            access_policy_path = policy_file.resolve()
    
    # 9. Build Settings object
    return Settings(
        project_root=project_root,
        bsl_models_path=bsl_path,
        connection=connection,
        agent=agent,
        advanced=advanced,
        extensions=extensions,
        access=access,
        skills=skills,
        access_policy_path=access_policy_path,
        slack_bot_token=os.getenv("SLACK_BOT_TOKEN"),
        slack_app_token=os.getenv("SLACK_APP_TOKEN"),
    )
