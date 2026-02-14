"""Project validation — checks configuration, semantic layer, and connections.

This module provides comprehensive validation for falk projects:
- Configuration file validation (falk_project.yaml)
- Semantic layer validation (BSL models)
- Connection testing (warehouse connectivity)
- Agent initialization checks
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of a single validation check."""
    
    check_name: str
    passed: bool
    message: str
    details: list[str] = field(default_factory=list)
    warning: bool = False  # True if this is a warning, not a failure


@dataclass
class ValidationSummary:
    """Aggregate validation results."""
    
    results: list[ValidationResult] = field(default_factory=list)
    
    @property
    def passed(self) -> bool:
        """All critical checks passed (warnings don't fail)."""
        return all(r.passed or r.warning for r in self.results)
    
    @property
    def failed_checks(self) -> list[ValidationResult]:
        """Critical checks that failed."""
        return [r for r in self.results if not r.passed and not r.warning]
    
    @property
    def warnings(self) -> list[ValidationResult]:
        """Non-critical warnings."""
        return [r for r in self.results if not r.passed and r.warning]
    
    @property
    def passed_checks(self) -> list[ValidationResult]:
        """Checks that passed."""
        return [r for r in self.results if r.passed]


def validate_project(
    *,
    project_root: Path | None = None,
    check_connection: bool = True,
    check_agent: bool = True,
) -> ValidationSummary:
    """Run all project validations.
    
    Args:
        project_root: Project directory (defaults to current directory)
        check_connection: Test warehouse connection
        check_agent: Test agent initialization
        
    Returns:
        ValidationSummary with all check results
    """
    summary = ValidationSummary()
    
    # Find project root
    if project_root is None:
        project_root = _find_project_root()
    
    if not project_root:
        summary.results.append(ValidationResult(
            check_name="Project Root",
            passed=False,
            message="No falk project found in current directory or parents",
            details=["Run 'falk init' to create a new project"],
        ))
        return summary
    
    # 1. Validate configuration
    summary.results.append(_validate_config(project_root))
    
    # 2. Validate semantic models
    summary.results.append(_validate_semantic_models(project_root))
    
    # 3. Validate knowledge files
    summary.results.append(_validate_knowledge(project_root))
    
    # 4. Test connection (optional)
    if check_connection:
        summary.results.append(_validate_connection(project_root))
    
    # 5. Test agent initialization (optional)
    if check_agent:
        summary.results.append(_validate_agent(project_root))
    
    return summary


def _find_project_root() -> Path | None:
    """Find project root by looking for falk_project.yaml."""
    current = Path.cwd()
    
    # Check current directory
    if (current / "falk_project.yaml").exists():
        return current
    
    # Check parent directories
    for parent in current.parents:
        if (parent / "falk_project.yaml").exists():
            return parent
    
    return None


def _validate_config(project_root: Path) -> ValidationResult:
    """Validate falk_project.yaml structure and required fields."""
    config_path = project_root / "falk_project.yaml"
    
    if not config_path.exists():
        return ValidationResult(
            check_name="Configuration",
            passed=False,
            message=f"Not a falk project (no falk_project.yaml found)",
            details=[
                f"Looked in: {config_path}",
                "Run 'falk init my-project' to create a new project",
            ],
        )
    
    try:
        with open(config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f)
        
        if not config:
            return ValidationResult(
                check_name="Configuration",
                passed=False,
                message="Configuration file is empty",
            )
        
        details = []
        issues = []
        
        # Check required sections
        if "project" not in config:
            issues.append("Missing 'project' section")
        else:
            if "name" not in config["project"]:
                issues.append("Missing 'project.name'")
        
        if "agent" not in config:
            issues.append("Missing 'agent' section")
        else:
            agent = config["agent"]
            if "provider" not in agent:
                issues.append("Missing 'agent.provider'")
            if "model" not in agent:
                issues.append("Missing 'agent.model'")
            else:
                details.append(f"Model: {agent['provider']}/{agent['model']}")
        
        # Check semantic models path
        if "semantic_models" in config:
            sem_path = project_root / config["semantic_models"]
            if not sem_path.exists():
                issues.append(f"Semantic models file not found: {sem_path}")
            else:
                details.append(f"Semantic models: {config['semantic_models']}")
        
        # Warnings for optional sections
        if "extensions" not in config:
            details.append("No extensions configured (optional)")
        
        if issues:
            return ValidationResult(
                check_name="Configuration",
                passed=False,
                message=f"Configuration validation failed ({len(issues)} issues)",
                details=issues,
            )
        
        return ValidationResult(
            check_name="Configuration",
            passed=True,
            message="Configuration is valid",
            details=details,
        )
    
    except yaml.YAMLError as e:
        return ValidationResult(
            check_name="Configuration",
            passed=False,
            message="Invalid YAML syntax",
            details=[str(e)],
        )
    except Exception as e:
        return ValidationResult(
            check_name="Configuration",
            passed=False,
            message=f"Failed to validate configuration: {e}",
        )


def _validate_semantic_models(project_root: Path) -> ValidationResult:
    """Validate BSL semantic models structure."""
    # Try to load settings to get semantic models path
    try:
        from falk.settings import load_settings
        settings = load_settings()
        models_path = settings.bsl_models_path
    except Exception:
        # Fallback to default
        models_path = project_root / "semantic_models.yaml"
    
    if not models_path.exists():
        return ValidationResult(
            check_name="Semantic Models",
            passed=False,
            message=f"Semantic models file not found: {models_path}",
        )
    
    try:
        with open(models_path, encoding="utf-8") as f:
            models = yaml.safe_load(f)
        
        if not models:
            return ValidationResult(
                check_name="Semantic Models",
                passed=False,
                message="Semantic models file is empty",
            )
        
        if "semantic_models" not in models:
            return ValidationResult(
                check_name="Semantic Models",
                passed=False,
                message="Missing 'semantic_models' key in file",
            )
        
        semantic_models = models["semantic_models"]
        if not semantic_models:
            return ValidationResult(
                check_name="Semantic Models",
                passed=False,
                message="No semantic models defined",
            )
        
        details = []
        issues = []
        warnings = []
        
        # Validate each model
        model_count = len(semantic_models)
        metric_count = 0
        dimension_count = 0
        
        for model in semantic_models:
            model_name = model.get("name", "unnamed")
            
            # Check required fields
            if "name" not in model:
                issues.append(f"Model missing 'name' field")
                continue
            
            if "model" not in model:
                issues.append(f"Model '{model_name}' missing 'model' field (SQL table/view)")
            
            # Count metrics
            metrics = model.get("metrics", [])
            metric_count += len(metrics)
            
            for metric in metrics:
                metric_name = metric.get("name", "unnamed")
                if "name" not in metric:
                    issues.append(f"Metric in model '{model_name}' missing 'name'")
                if "type" not in metric:
                    issues.append(f"Metric '{metric_name}' missing 'type'")
                if "description" not in metric:
                    warnings.append(f"Metric '{metric_name}' missing description")
            
            # Count dimensions
            dimensions = model.get("dimensions", [])
            dimension_count += len(dimensions)
            
            for dim in dimensions:
                dim_name = dim.get("name", "unnamed")
                if "name" not in dim:
                    issues.append(f"Dimension in model '{model_name}' missing 'name'")
                if "type" not in dim:
                    issues.append(f"Dimension '{dim_name}' missing 'type'")
                if "description" not in dim:
                    warnings.append(f"Dimension '{dim_name}' missing description")
        
        details.append(f"Models: {model_count}")
        details.append(f"Metrics: {metric_count}")
        details.append(f"Dimensions: {dimension_count}")
        
        if metric_count == 0:
            issues.append("No metrics defined")
        
        if issues:
            return ValidationResult(
                check_name="Semantic Models",
                passed=False,
                message=f"Semantic models validation failed ({len(issues)} issues)",
                details=issues + warnings,
            )
        
        # Return with warnings if any
        if warnings:
            return ValidationResult(
                check_name="Semantic Models",
                passed=False,  # Mark as not passed
                message=f"Semantic models valid with {len(warnings)} warnings",
                details=details + warnings,
                warning=True,  # But it's just a warning
            )
        
        return ValidationResult(
            check_name="Semantic Models",
            passed=True,
            message="Semantic models are valid",
            details=details,
        )
    
    except yaml.YAMLError as e:
        return ValidationResult(
            check_name="Semantic Models",
            passed=False,
            message="Invalid YAML syntax in semantic models",
            details=[str(e)],
        )
    except Exception as e:
        return ValidationResult(
            check_name="Semantic Models",
            passed=False,
            message=f"Failed to validate semantic models: {e}",
        )


def _validate_knowledge(project_root: Path) -> ValidationResult:
    """Check knowledge directory structure."""
    knowledge_dir = project_root / "knowledge"
    
    if not knowledge_dir.exists():
        return ValidationResult(
            check_name="Knowledge Files",
            passed=False,
            message="Knowledge directory not found (optional but recommended)",
            details=["Create knowledge/ directory with business.md and gotchas.md"],
            warning=True,
        )
    
    details = []
    warnings = []
    
    # Check for recommended files
    if not (knowledge_dir / "business.md").exists():
        warnings.append("Missing business.md (business context)")
    else:
        details.append("Found business.md")
    
    if not (knowledge_dir / "gotchas.md").exists():
        warnings.append("Missing gotchas.md (data quality notes)")
    else:
        details.append("Found gotchas.md")
    
    # Count total knowledge files
    md_files = list(knowledge_dir.glob("*.md"))
    details.append(f"Total files: {len(md_files)}")
    
    if warnings:
        return ValidationResult(
            check_name="Knowledge Files",
            passed=False,
            message=f"Knowledge directory exists with {len(warnings)} missing files",
            details=details + warnings,
            warning=True,
        )
    
    return ValidationResult(
        check_name="Knowledge Files",
        passed=True,
        message="Knowledge files present",
        details=details,
    )


def _validate_connection(project_root: Path) -> ValidationResult:
    """Test warehouse connection."""
    try:
        from falk.settings import load_settings
        settings = load_settings()
        connection_type = settings.connection.get("type", "unknown")
        
        # For DuckDB, check if database file exists
        if connection_type == "duckdb":
            db_path = project_root / settings.connection.get("database", "data/warehouse.duckdb")
            if not db_path.exists():
                return ValidationResult(
                    check_name="Warehouse Connection",
                    passed=False,
                    message=f"DuckDB file not found: {db_path.name}",
                    details=[
                        f"Expected location: {db_path}",
                        "For new projects: Create database file or load sample data",
                        "Run with --no-connection to skip this check",
                    ],
                    warning=True,  # This is expected for new projects
                )
        
        # Try to actually connect
        from falk.agent import DataAgent
        agent = DataAgent()
        
        # Get database info from settings
        database = settings.connection.get("database") or settings.connection.get("project_id") or "unknown"
        
        # Try to get connection object (ibis_connection is the actual property)
        conn = agent.ibis_connection
        if conn is None:
            return ValidationResult(
                check_name="Warehouse Connection",
                passed=False,
                message="Failed to establish warehouse connection",
                details=["Check connection settings in falk_project.yaml"],
            )
        
        return ValidationResult(
            check_name="Warehouse Connection",
            passed=True,
            message=f"Connected to {connection_type}",
            details=[f"Database: {database}"],
        )
    
    except Exception as e:
        error_msg = str(e)
        details = [error_msg]
        
        # Provide helpful hints based on error
        if "Cannot open file" in error_msg or "No such file" in error_msg:
            details.append("Database file not found - normal for new projects")
            details.append("Create your database or load sample data")
        elif "Connection refused" in error_msg:
            details.append("Check that the warehouse is running and accessible")
        elif "authentication" in error_msg.lower() or "credentials" in error_msg.lower():
            details.append("Check credentials in .env file")
        else:
            details.append("Check connection settings in falk_project.yaml")
        
        details.append("Use --no-connection to skip this check")
        
        return ValidationResult(
            check_name="Warehouse Connection",
            passed=False,
            message="Connection test failed",
            details=details,
            warning=True,  # Don't fail validation for connection issues in new projects
        )


def _validate_agent(project_root: Path) -> ValidationResult:
    """Test agent initialization."""
    try:
        from falk import build_agent
        
        # Build agent (uses settings internally)
        agent = build_agent()
        
        # Check that agent has core components
        if not agent:
            return ValidationResult(
                check_name="Agent Initialization",
                passed=False,
                message="Agent build returned None",
            )
        
        details = []
        
        # Get agent info if available
        if hasattr(agent, 'model'):
            details.append(f"Model: {agent.model}")
        
        if hasattr(agent, 'tools'):
            tool_count = len(agent.tools) if agent.tools else 0
            details.append(f"Tools: {tool_count}")
        
        return ValidationResult(
            check_name="Agent Initialization",
            passed=True,
            message="Agent initialized successfully",
            details=details,
        )
    
    except Exception as e:
        error_msg = str(e)
        details = [error_msg]
        
        # Provide helpful hints
        if "Cannot open file" in error_msg or "No such file" in error_msg:
            details.append("Database file not found - this prevents agent initialization")
            details.append("Create your database file first")
        elif "API" in error_msg or "api_key" in error_msg.lower():
            details.append("Check API keys in .env file")
        
        details.append("Use --no-agent to skip this check")
        
        return ValidationResult(
            check_name="Agent Initialization",
            passed=False,
            message="Failed to initialize agent",
            details=details,
            warning=True,  # Don't fail validation for this in new projects
        )
