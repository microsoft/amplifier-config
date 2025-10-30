"""amplifier-config: Three-scope configuration management for Amplifier.

This library provides mechanism for managing configuration across three scopes:
- User global (typically ~/.amplifier/settings.yaml)
- Project (typically .amplifier/settings.yaml)
- Local/machine-specific (typically .amplifier/settings.local.yaml)

Applications inject paths to define their configuration policy. The library
provides the mechanism for reading, writing, and merging configuration.

Public API:
    ConfigManager: Main class for configuration operations
    ConfigPaths: Dataclass defining paths to all three config scopes
    Scope: Enum for USER/PROJECT/LOCAL scopes
    deep_merge: Utility function for deep dictionary merging
    ConfigError, ConfigFileError, ConfigValidationError: Exception types

Example:
    ```python
    from pathlib import Path
    from amplifier_config import ConfigManager, ConfigPaths, Scope

    # Application injects paths (policy)
    paths = ConfigPaths(
        user=Path.home() / ".amplifier" / "settings.yaml",
        project=Path(".amplifier") / "settings.yaml",
        local=Path(".amplifier") / "settings.local.yaml",
    )

    # Library provides mechanism
    config = ConfigManager(paths)

    # Read merged settings
    active_profile = config.get_active_profile()

    # Write to specific scope
    config.set_active_profile("dev", scope=Scope.LOCAL)
    ```
"""

from .exceptions import ConfigError
from .exceptions import ConfigFileError
from .exceptions import ConfigValidationError
from .manager import ConfigManager
from .models import ConfigPaths
from .models import Scope
from .utils import deep_merge

__version__ = "0.1.0"

__all__ = [
    "ConfigManager",
    "ConfigPaths",
    "Scope",
    "deep_merge",
    "ConfigError",
    "ConfigFileError",
    "ConfigValidationError",
]
