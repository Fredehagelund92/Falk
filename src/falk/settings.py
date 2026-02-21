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
    include_semantic_metadata_in_prompt: bool = True  # False = omit vocabulary + gotchas; use tools


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
    message_history_max_messages: int | None = None  # None = no limit. N = keep last N messages (reduces tokens in long threads).


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
class SlackPolicyConfig:
    """Slack-specific delivery policy controls."""

    exports_dm_only: bool = True
    export_channel_allowlist: list[str] = field(default_factory=list)
    export_block_message: str = (
        "Export files are restricted to DMs. Ask me in DM if you need the file."
    )


@dataclass(frozen=True)
class RolePolicy:
    """Permissions for a single named role.

    metrics/dimensions of None means "all allowed".
    An empty list means "nothing allowed".
    """
    metrics: list[str] | None = None
    dimensions: list[str] | None = None


@dataclass(frozen=True)
class UserMapping:
    """Maps a single user_id to one or more roles."""
    user_id: str
    roles: list[str]


@dataclass(frozen=True)
class AccessConfig:
    """Access control configuration.

    Absent from falk_project.yaml = open access (identical to current behaviour).
    default_role: role applied when a user has no explicit mapping.
    None = no default role = open access for unlisted users.
    """
    roles: dict[str, RolePolicy] = field(default_factory=dict)
    users: list[UserMapping] = field(default_factory=list)
    default_role: str | None = None


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
    slack: SlackPolicyConfig
    access: AccessConfig

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
        include_semantic_metadata_in_prompt=bool(agent_config.get("include_semantic_metadata_in_prompt", True)),
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
        message_history_max_messages=advanced_config.get("message_history_max_messages"),
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

    # 6b. Parse slack policy config
    slack_config = config.get("slack") or {}
    allowlist_raw = slack_config.get("export_channel_allowlist") or []
    if isinstance(allowlist_raw, str):
        allowlist = [allowlist_raw]
    elif isinstance(allowlist_raw, list):
        allowlist = [str(v).strip() for v in allowlist_raw if str(v).strip()]
    else:
        allowlist = []
    slack = SlackPolicyConfig(
        exports_dm_only=bool(slack_config.get("exports_dm_only", True)),
        export_channel_allowlist=allowlist,
        export_block_message=str(
            slack_config.get(
                "export_block_message",
                "Export files are restricted to DMs. Ask me in DM if you need the file.",
            )
        ).strip()
        or "Export files are restricted to DMs. Ask me in DM if you need the file.",
    )

    # 7. Parse access control config
    access_raw = config.get("access_policies") or {}
    roles_raw = access_raw.get("roles") or {}
    roles: dict[str, RolePolicy] = {}
    for role_name, role_cfg in roles_raw.items():
        if not isinstance(role_cfg, dict):
            continue
        metrics_val = role_cfg.get("metrics")
        dimensions_val = role_cfg.get("dimensions")
        roles[str(role_name)] = RolePolicy(
            metrics=_string_list(metrics_val) if metrics_val is not None else None,
            dimensions=_string_list(dimensions_val) if dimensions_val is not None else None,
        )

    users_raw = access_raw.get("users") or []
    user_mappings: list[UserMapping] = []
    for entry in users_raw:
        if not isinstance(entry, dict):
            continue
        uid = str(entry.get("user_id") or "").strip()
        raw_roles = entry.get("roles") or []
        if uid and raw_roles:
            user_mappings.append(UserMapping(user_id=uid, roles=_string_list(raw_roles)))

    default_role_raw = access_raw.get("default_role")
    default_role = str(default_role_raw).strip() if default_role_raw else None

    access = AccessConfig(roles=roles, users=user_mappings, default_role=default_role)

    # 8. Parse connection (inline in falk_project.yaml)
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

    # 9. Resolve paths
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
    
    # Guardrails for production deployments.
    env_name = str(os.getenv("FALK_ENV", "")).strip().lower()
    if env_name in {"prod", "production"}:
        has_access_policy = bool(access.roles or access.users or access.default_role)
        if not has_access_policy:
            raise RuntimeError(
                "FALK_ENV=production requires access_policies in falk_project.yaml. "
                "Configure roles/users/default_role to avoid open-access behavior."
            )

    # 10. Build Settings object
    return Settings(
        project_root=project_root,
        bsl_models_path=bsl_path,
        connection=connection,
        agent=agent,
        advanced=advanced,
        observability=observability,
        session=session,
        slack=slack,
        access=access,
        slack_bot_token=os.getenv("SLACK_BOT_TOKEN"),
        slack_app_token=os.getenv("SLACK_APP_TOKEN"),
    )
