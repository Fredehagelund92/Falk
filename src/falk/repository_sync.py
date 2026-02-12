"""Repository synchronization for falk.

Allows pulling semantic models from multiple Git repositories.
This enables distributed teams to maintain their own metrics definitions.
"""
from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import git
from git import Repo


@dataclass
class RepositorySource:
    """Configuration for an external repository."""
    name: str
    url: str
    branch: str = "main"
    path: str = "semantic_models.yaml"
    auth: str | None = None  # "token" to use GH_TOKEN/GITHUB_TOKEN


@dataclass
class SyncResult:
    """Result of syncing a repository."""
    source: RepositorySource
    success: bool
    local_path: Path | None = None
    error: str | None = None
    commit_hash: str | None = None
    is_new: bool = False
    is_updated: bool = False


class RepositorySync:
    """Manages syncing semantic models from external repositories."""
    
    def __init__(self, cache_dir: Path):
        """Initialize repository sync.
        
        Args:
            cache_dir: Directory to store cloned repositories
        """
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def sync_source(self, source: RepositorySource) -> SyncResult:
        """Sync a single repository source.
        
        Args:
            source: Repository configuration
            
        Returns:
            SyncResult with details about the sync operation
        """
        repo_dir = self.cache_dir / source.name
        
        try:
            # Check if repo already exists locally
            if repo_dir.exists():
                result = self._pull_existing(source, repo_dir)
            else:
                result = self._clone_new(source, repo_dir)
            
            # Verify the semantic model file exists
            if result.success and result.local_path:
                model_path = result.local_path / source.path
                if not model_path.exists():
                    return SyncResult(
                        source=source,
                        success=False,
                        local_path=result.local_path,
                        error=f"Semantic model file not found: {source.path}",
                    )
            
            return result
        
        except Exception as e:
            return SyncResult(
                source=source,
                success=False,
                error=str(e),
            )
    
    def _clone_new(self, source: RepositorySource, repo_dir: Path) -> SyncResult:
        """Clone a new repository.
        
        Args:
            source: Repository configuration
            repo_dir: Local directory to clone into
            
        Returns:
            SyncResult
        """
        # Build clone URL with auth if needed
        clone_url = self._build_auth_url(source)
        
        # Clone the repository
        repo = Repo.clone_from(
            clone_url,
            repo_dir,
            branch=source.branch,
            depth=1,  # Shallow clone for speed
        )
        
        return SyncResult(
            source=source,
            success=True,
            local_path=repo_dir,
            commit_hash=repo.head.commit.hexsha[:8],
            is_new=True,
        )
    
    def _pull_existing(self, source: RepositorySource, repo_dir: Path) -> SyncResult:
        """Pull updates for an existing repository.
        
        Args:
            source: Repository configuration
            repo_dir: Local directory of the repository
            
        Returns:
            SyncResult
        """
        repo = Repo(repo_dir)
        
        # Get current commit
        old_commit = repo.head.commit.hexsha[:8]
        
        # Fetch and pull updates
        origin = repo.remote("origin")
        
        # Update remote URL with auth if needed
        if source.auth:
            auth_url = self._build_auth_url(source)
            origin.set_url(auth_url)
        
        origin.fetch()
        origin.pull(source.branch)
        
        # Get new commit
        new_commit = repo.head.commit.hexsha[:8]
        is_updated = old_commit != new_commit
        
        return SyncResult(
            source=source,
            success=True,
            local_path=repo_dir,
            commit_hash=new_commit,
            is_updated=is_updated,
        )
    
    def _build_auth_url(self, source: RepositorySource) -> str:
        """Build Git URL with authentication if needed.
        
        Args:
            source: Repository configuration
            
        Returns:
            URL with authentication token if auth is enabled
        """
        if not source.auth or source.auth != "token":
            return source.url
        
        # Look for GitHub token in environment
        token = os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
        if not token:
            raise ValueError(
                f"Repository '{source.name}' requires auth, but "
                "GH_TOKEN/GITHUB_TOKEN not found in environment"
            )
        
        # Convert HTTPS URL to authenticated URL
        # https://github.com/org/repo -> https://x-access-token:TOKEN@github.com/org/repo
        if source.url.startswith("https://github.com/"):
            return source.url.replace(
                "https://github.com/",
                f"https://x-access-token:{token}@github.com/",
            )
        
        return source.url
    
    def sync_all(self, sources: list[RepositorySource]) -> list[SyncResult]:
        """Sync all repository sources.
        
        Args:
            sources: List of repository configurations
            
        Returns:
            List of SyncResults
        """
        results = []
        for source in sources:
            result = self.sync_source(source)
            results.append(result)
        
        return results
    
    def get_semantic_model_paths(self, results: list[SyncResult]) -> list[Path]:
        """Get paths to all synced semantic model files.
        
        Args:
            results: List of SyncResults from sync_all
            
        Returns:
            List of paths to semantic model YAML files
        """
        paths = []
        for result in results:
            if result.success and result.local_path:
                model_path = result.local_path / result.source.path
                if model_path.exists():
                    paths.append(model_path)
        
        return paths
    
    def clean_cache(self) -> None:
        """Remove all cached repositories."""
        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)
            self.cache_dir.mkdir(parents=True, exist_ok=True)


def parse_repository_config(config: dict[str, Any]) -> tuple[bool, list[RepositorySource]]:
    """Parse repository configuration from falk_project.yaml.
    
    Args:
        config: Raw config dict from YAML
        
    Returns:
        Tuple of (enabled, sources)
    """
    if not config:
        return False, []
    
    enabled = config.get("enabled", False)
    sources_config = config.get("sources", [])
    
    sources = []
    for src in sources_config:
        if not isinstance(src, dict):
            continue
        
        # Skip if missing required fields
        if "name" not in src or "url" not in src:
            continue
        
        sources.append(RepositorySource(
            name=src["name"],
            url=src["url"],
            branch=src.get("branch", "main"),
            path=src.get("path", "semantic_models.yaml"),
            auth=src.get("auth"),
        ))
    
    return enabled, sources

