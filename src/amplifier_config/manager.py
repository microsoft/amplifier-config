"""Configuration manager for three-scope settings system."""

import logging
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore

from .exceptions import ConfigFileError
from .models import ConfigPaths
from .models import Scope
from .utils import deep_merge

logger = logging.getLogger(__name__)


class ConfigManager:
    """Manages configuration across user/project/local scopes.

    This class provides a three-scope configuration system with proper
    precedence handling. Applications inject paths via ConfigPaths to
    define their configuration policy.

    Resolution order (highest to lowest priority):
    1. Local settings (machine-specific)
    2. Project settings (repository)
    3. User settings (global)

    Args:
        paths: Configuration file paths for all three scopes
    """

    def __init__(self, paths: ConfigPaths):
        """Initialize configuration manager with injected paths.

        Args:
            paths: ConfigPaths defining where config files are located
        """
        self.paths = paths

    # ===== Active Profile Management =====

    def get_active_profile(self) -> str | None:
        """Get active profile name from merged settings.

        Resolution order:
        1. Local settings (highest priority)
        2. Project settings
        3. User settings
        4. None

        Returns:
            Active profile name or None if not set
        """
        # Check local settings first (highest priority)
        local = self._read_yaml(self.paths.local)
        if local and "profile" in local and "active" in local["profile"]:
            return local["profile"]["active"]

        # Check project settings
        project = self._read_yaml(self.paths.project)
        if project and "profile" in project and "active" in project["profile"]:
            return project["profile"]["active"]

        # Check user settings (lowest priority)
        user = self._read_yaml(self.paths.user)
        if user and "profile" in user and "active" in user["profile"]:
            return user["profile"]["active"]

        return None

    def set_active_profile(self, name: str, scope: Scope = Scope.LOCAL) -> None:
        """Set active profile in specified scope.

        Args:
            name: Profile name to activate
            scope: Target scope (default: LOCAL)
        """
        target_path = self._scope_to_path(scope)
        self._update_yaml(target_path, {"profile": {"active": name}})
        logger.info(f"Set active profile to '{name}' in {scope.value} scope")

    def clear_active_profile(self, scope: Scope = Scope.LOCAL) -> None:
        """Clear active profile from specified scope.

        Args:
            scope: Target scope (default: LOCAL)
        """
        target_path = self._scope_to_path(scope)
        settings = self._read_yaml(target_path)

        if settings and "profile" in settings and "active" in settings["profile"]:
            del settings["profile"]["active"]
            # Clean up empty profile section
            if not settings["profile"]:
                del settings["profile"]
            self._write_yaml(target_path, settings)
            logger.info(f"Cleared active profile from {scope.value} scope")

    # ===== Project Default Management =====

    def get_project_default(self) -> str | None:
        """Get project default profile name.

        Only reads from project scope (by definition).

        Returns:
            Project default profile name or None
        """
        project = self._read_yaml(self.paths.project)
        if project and "profile" in project and "default" in project["profile"]:
            return project["profile"]["default"]
        return None

    def set_project_default(self, name: str) -> None:
        """Set project default profile (always in project scope).

        Args:
            name: Profile name to set as project default
        """
        self._update_yaml(self.paths.project, {"profile": {"default": name}})
        logger.info(f"Set project default profile to '{name}'")

    def clear_project_default(self) -> None:
        """Clear project default profile."""
        settings = self._read_yaml(self.paths.project)

        if settings and "profile" in settings and "default" in settings["profile"]:
            del settings["profile"]["default"]
            # Clean up empty profile section
            if not settings["profile"]:
                del settings["profile"]
            self._write_yaml(self.paths.project, settings)
            logger.info("Cleared project default profile")

    # ===== Module Source Overrides =====

    def get_module_sources(self) -> dict[str, str]:
        """Get merged module source overrides from all scopes.

        Merge order (later overrides earlier):
        1. User settings (lowest priority)
        2. Project settings
        3. Local settings (highest priority)

        Returns:
            Dictionary mapping module_id -> source_uri
        """
        sources = {}

        # Start with user settings (lowest priority)
        user = self._read_yaml(self.paths.user)
        if user and "sources" in user:
            sources.update(user["sources"])

        # Override with project settings
        project = self._read_yaml(self.paths.project)
        if project and "sources" in project:
            sources.update(project["sources"])

        # Override with local settings (highest priority)
        local = self._read_yaml(self.paths.local)
        if local and "sources" in local:
            sources.update(local["sources"])

        return sources

    def add_source_override(self, module_id: str, source: str, scope: Scope = Scope.PROJECT) -> None:
        """Add module source override to specified scope.

        Args:
            module_id: Module identifier
            source: Source URI (git URL or file path)
            scope: Target scope (default: PROJECT)
        """
        target_path = self._scope_to_path(scope)
        self._update_yaml(target_path, {"sources": {module_id: source}})
        logger.info(f"Added {scope.value} source override for '{module_id}': {source}")

    def remove_source_override(self, module_id: str, scope: Scope = Scope.PROJECT) -> bool:
        """Remove module source override from specified scope.

        Args:
            module_id: Module identifier
            scope: Target scope (default: PROJECT)

        Returns:
            True if removed, False if not found
        """
        target_path = self._scope_to_path(scope)
        settings = self._read_yaml(target_path)

        if not settings or "sources" not in settings or module_id not in settings["sources"]:
            return False

        del settings["sources"][module_id]

        # Clean up empty sources section
        if not settings["sources"]:
            del settings["sources"]

        self._write_yaml(target_path, settings)
        logger.info(f"Removed {scope.value} source override for '{module_id}'")
        return True

    # ===== Merged Settings =====

    def get_merged_settings(self) -> dict[str, Any]:
        """Get merged settings from all scopes.

        Merge order (later overrides earlier):
        1. User settings (lowest priority)
        2. Project settings
        3. Local settings (highest priority)

        Returns:
            Merged settings dictionary
        """
        merged = {}

        # Start with user settings (lowest priority)
        user = self._read_yaml(self.paths.user)
        if user:
            merged = deep_merge(merged, user)

        # Merge project settings
        project = self._read_yaml(self.paths.project)
        if project:
            merged = deep_merge(merged, project)

        # Merge local settings (highest priority)
        local = self._read_yaml(self.paths.local)
        if local:
            merged = deep_merge(merged, local)

        return merged

    # ===== Generic Settings Update =====

    def update_settings(self, updates: dict[str, Any], scope: Scope = Scope.PROJECT) -> None:
        """Update arbitrary settings at specified scope.

        For advanced use cases that need to update settings beyond the
        standard active profile and module sources.

        Args:
            updates: Dictionary of updates to deep merge into settings
            scope: Target scope (default: PROJECT)
        """
        target_path = self._scope_to_path(scope)
        self._update_yaml(target_path, updates)

    def scope_to_path(self, scope: Scope) -> Path:
        """Get path for a given scope.

        Public accessor for scope-to-path mapping.

        Args:
            scope: Scope enum value

        Returns:
            Path for the given scope
        """
        return self._scope_to_path(scope)

    # ===== Private Helpers =====

    def _scope_to_path(self, scope: Scope) -> Path:
        """Convert Scope enum to Path.

        Args:
            scope: Scope enum value

        Returns:
            Path for the given scope
        """
        scope_map = {
            Scope.USER: self.paths.user,
            Scope.PROJECT: self.paths.project,
            Scope.LOCAL: self.paths.local,
        }
        return scope_map[scope]

    def _read_yaml(self, path: Path) -> dict[str, Any] | None:
        """Read YAML file.

        Args:
            path: Path to YAML file

        Returns:
            Dictionary from YAML or None if file doesn't exist
        """
        if not yaml:
            logger.warning("PyYAML not available - cannot read configuration files")
            return None

        if not path.exists():
            return None

        try:
            with open(path) as f:
                data = yaml.safe_load(f)
                return data if data else {}
        except Exception as e:
            logger.warning(f"Failed to read configuration from {path}: {e}")
            return None

    def _write_yaml(self, path: Path, data: dict[str, Any]) -> None:
        """Write YAML file.

        Args:
            path: Path to YAML file
            data: Dictionary to write

        Raises:
            ConfigFileError: If write fails
        """
        if not yaml:
            raise ConfigFileError("PyYAML not available - cannot write configuration files")

        # Ensure directory exists
        path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(path, "w") as f:
                yaml.dump(data, f, default_flow_style=False, sort_keys=False)
        except Exception as e:
            raise ConfigFileError(f"Failed to write configuration to {path}: {e}") from e

    def _update_yaml(self, path: Path, updates: dict[str, Any]) -> None:
        """Update YAML file with deep merge.

        Args:
            path: Path to YAML file
            updates: Updates to merge into existing data
        """
        existing = self._read_yaml(path) or {}
        merged = deep_merge(existing, updates)
        self._write_yaml(path, merged)
