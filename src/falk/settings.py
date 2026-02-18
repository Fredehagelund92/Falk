"""Configuration for falk.

Loads configuration from:
1. falk_project.yaml (agent behavior, observability, access control)
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
    model: str = "gpt-5-mini"
    context: str = ""
    examples: list[str] = field(default_factory=list)
    rules: list[str] = field(default_factory=list)
    gotchas: list[str] = field(default_factory=list)
    welcome: str = ""
    custom_sections: list[dict[str, str]] = field(default_factory=list)
    knowledge_enabled: bool = True
    knowledge_business_path: str = "knowledge/business.md"
    knowledge_gotchas_path: str = "knowledge/gotchas.md"
    knowledge_load_mode: str = "startup"


@dataclass(frozen=True)
class AdvancedConfig:
    """Technical settings (hidden from analyst-facing config)."""
    auto_run: bool = False
    max_tokens: int = 4096
    temperature: float = 0.1
    max_rows_per_query: int = 10000
    query_timeout_seconds: int = 30  # tool/warehouse execution
    model_timeout_seconds: int = 60  # LLM request (single turn)
    slack_run_timeout_seconds: int = 120  # Whole Slack run (model + tools)
    tool_calls_limit: int = 8  # Max tool calls per run
    request_limit: int = 6  # Max LLM requests per run
    max_retries: int = 3
    retry_delay_seconds: int = 1
    log_level: str = "INFO"


@dataclass(frozen=True)
class ObservabilityConfig:
    """Observability configuration."""
    langfuse_sync: bool = True  # Flush after each trace


@dataclass(frozen=True)
class SessionConfig:
    """Session state storage configuration."""
    store: str = "memory"  # "memory" or "redis"
    url: str = "redis://localhost:6379"  # URL for redis store
    ttl: int = 3600  # Session TTL in seconds
    maxsize: int = 500  # Max sessions for memory store


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
    observability: ObservabilityConfig
    session: SessionConfig

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
    
    def _string_list(value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        if isinstance(value, list):
            return [str(v) for v in value if str(v).strip()]
        return []

    # 4. Parse agent config (analyst-facing)
    agent_config = config.get("agent") or {}
    knowledge_config = agent_config.get("knowledge") or {}
    custom_sections_raw = agent_config.get("custom_sections") or []
    custom_sections: list[dict[str, str]] = []
    if isinstance(custom_sections_raw, list):
        for section in custom_sections_raw:
            if not isinstance(section, dict):
                continue
            title = str(section.get("title") or "").strip()
            content = str(section.get("content") or "").strip()
            if title and content:
                custom_sections.append({"title": title, "content": content})

    knowledge_load_mode = str(knowledge_config.get("load_mode") or "startup").strip().lower()
    if knowledge_load_mode not in {"startup", "on_demand"}:
        knowledge_load_mode = "startup"

    agent = AgentConfig(
        provider=agent_config.get("provider", "openai"),
        model=agent_config.get("model", "gpt-5-mini"),
        context=agent_config.get("context", ""),
        examples=_string_list(agent_config.get("examples")),
        rules=_string_list(agent_config.get("rules")),
        gotchas=_string_list(agent_config.get("gotchas")),
        welcome=agent_config.get("welcome", ""),
        custom_sections=custom_sections,
        knowledge_enabled=bool(knowledge_config.get("enabled", True)),
        knowledge_business_path=str(knowledge_config.get("business_path") or "knowledge/business.md"),
        knowledge_gotchas_path=str(knowledge_config.get("gotchas_path") or "knowledge/gotchas.md"),
        knowledge_load_mode=knowledge_load_mode,
    )

    # 4b. Parse advanced config (technical settings)
    advanced_config = config.get("advanced") or {}
    advanced = AdvancedConfig(
        auto_run=advanced_config.get("auto_run", False),
        max_tokens=advanced_config.get("max_tokens", 4096),
        temperature=advanced_config.get("temperature", 0.1),
        max_rows_per_query=advanced_config.get("max_rows_per_query", 10000),
        query_timeout_seconds=advanced_config.get("query_timeout_seconds", 30),
        model_timeout_seconds=advanced_config.get("model_timeout_seconds", 60),
        slack_run_timeout_seconds=advanced_config.get("slack_run_timeout_seconds", 120),
        tool_calls_limit=advanced_config.get("tool_calls_limit", 8),
        request_limit=advanced_config.get("request_limit", 6),
        max_retries=advanced_config.get("max_retries", 3),
        retry_delay_seconds=advanced_config.get("retry_delay_seconds", 1),
        log_level=advanced_config.get("log_level", "INFO"),
    )
    
    # 5. Parse observability config
    observability_config = config.get("observability") or {}
    observability = ObservabilityConfig(
        langfuse_sync=observability_config.get("langfuse_sync", True),
    )
    
    # 6. Parse session config
    session_config = config.get("session") or {}
    session = SessionConfig(
        store=session_config.get("store", "memory"),
        url=session_config.get("url", "redis://localhost:6379"),
        ttl=session_config.get("ttl", 3600),
        maxsize=session_config.get("maxsize", 500),
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
    
    # 9. Build Settings object
    return Settings(
        project_root=project_root,
        bsl_models_path=bsl_path,
        connection=connection,
        agent=agent,
        advanced=advanced,
        observability=observability,
        session=session,
        slack_bot_token=os.getenv("SLACK_BOT_TOKEN"),
        slack_app_token=os.getenv("SLACK_APP_TOKEN"),
    )
