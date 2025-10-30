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
        user: Path to user-global settings file
        project: Path to project settings file
        local: Path to local (machine-specific) settings file
    """

    user: Path
    project: Path
    local: Path
