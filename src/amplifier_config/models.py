"""Data models for amplifier-config."""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class Scope(Enum):
    """Configuration scope enumeration.

    Determines which settings file to target for write operations.
    """

    USER = "user"
    PROJECT = "project"
    LOCAL = "local"


@dataclass(frozen=True)
class ConfigPaths:
    """Paths to the three configuration scopes.

    Immutable configuration for where settings files are located.
    Applications inject these paths to define their configuration policy.

    Attributes:
        user: Path to user-global settings file (required)
        project: Path to project settings file (optional - None when cwd is home)
        local: Path to local (machine-specific) settings file (optional - None when cwd is home)

    Note:
        When running from the home directory (~), project and local scopes are
        disabled to prevent confusion. In ~/.amplifier/, there should only ever
        be a settings.yaml (user scope), never a settings.local.yaml.
    """

    user: Path
    project: Path | None = None
    local: Path | None = None
