# amplifier-config

**Hierarchical configuration management for Amplifier applications**

amplifier-config provides pure configuration mechanism with three-scope resolution (user, project, local), deep merge semantics, and YAML file I/O. Apps inject path conventions; the library handles resolution logic.

---

## Documentation

- **[Quick Start](#quick-start)** - Get started in 5 minutes
- **[API Reference](#api-reference)** - Complete API documentation
- **[User Guide](docs/USER_GUIDE.md)** - Application examples and patterns
- **[Technical Specification](docs/SPECIFICATION.md)** - Resolution algorithm and contracts

---

## Installation

```bash
# From PyPI (when published)
uv pip install amplifier-config

# From git (development)
uv pip install git+https://github.com/microsoft/amplifier-config@main

# For local development
cd amplifier-config
uv pip install -e .

# Or using uv sync for development with dependencies
uv sync --dev
```

---

## Quick Start

```python
from amplifier_config import ConfigManager, ConfigPaths, Scope
from pathlib import Path

# Define paths for your application (CLI example)
paths = ConfigPaths(
    user=Path.home() / ".amplifier" / "settings.yaml",
    project=Path(".amplifier/settings.yaml"),
    local=Path(".amplifier/settings.local.yaml"),
)

# Create configuration manager
config = ConfigManager(paths=paths)

# Get active profile (LOCAL > PROJECT > USER > None)
active_profile = config.get_active_profile()

# Set profile at local scope
config.set_active_profile("dev", scope=Scope.LOCAL)

# Get merged settings across all scopes
all_settings = config.get_merged_settings()

# Manage module source overrides
config.add_source_override(
    module_id="provider-anthropic",
    source="git+https://github.com/user/custom-provider@main",
    scope=Scope.PROJECT
)
```

---

## What This Library Provides

### Three-Scope Configuration Resolution

Configuration resolves in precedence order (highest wins):

1. **LOCAL** (highest) - Developer-specific overrides, typically not committed
2. **PROJECT** (middle) - Team-shared settings, committed to version control
3. **USER** (lowest) - User-global defaults

**→ See [Resolution Algorithm Specification](docs/SPECIFICATION.md#three-scope-resolution-algorithm) for complete technical details.**

### Deep Merge Semantics

Overlays merge recursively with overlay values taking precedence. This preserves unmodified values from lower scopes.

**→ See [Deep Merge Algorithm Specification](docs/SPECIFICATION.md#deep-merge-algorithm-specification) for complete algorithm and examples.**

### Path Injection

The library does NOT hardcode paths like `.amplifier/` or `~/.amplifier/`. Apps inject their path conventions; the library provides the resolution mechanism.

**→ See [Path Injection Contract](docs/SPECIFICATION.md#path-injection-contract) for complete specification and examples.**

---

## API Reference

### Core Classes

#### Scope

```python
from amplifier_config import Scope

class Scope(Enum):
    """Configuration scope levels."""
    USER = "user"       # User-global settings
    PROJECT = "project" # Project-shared settings
    LOCAL = "local"     # Developer-local overrides
```

#### ConfigPaths

```python
from amplifier_config import ConfigPaths
from pathlib import Path

@dataclass(frozen=True)
class ConfigPaths:
    """Injectable path configuration.

    Apps provide these paths based on their conventions.
    Library uses paths without knowing their semantic meanings.
    """
    user: Path      # Where user-global settings live
    project: Path   # Where project-shared settings live
    local: Path     # Where local overrides live
```

**Example: CLI paths**
```python
cli_paths = ConfigPaths(
    user=Path.home() / ".amplifier" / "settings.yaml",
    project=Path(".amplifier/settings.yaml"),
    local=Path(".amplifier/settings.local.yaml"),
)
```

**→ See [Application Examples](docs/USER_GUIDE.md#application-examples) for Web, Desktop, and Testing path conventions.**

#### ConfigManager

```python
from amplifier_config import ConfigManager, ConfigPaths, Scope

class ConfigManager:
    """Configuration management mechanism.

    Provides hierarchical resolution, deep merge, and file I/O.
    Does not make decisions about paths, display, or storage backend.
    """

    def __init__(self, paths: ConfigPaths):
        """Initialize with injectable paths.

        Args:
            paths: ConfigPaths defining where settings files live
        """
```

##### Profile Management

```python
# Get active profile
active = config.get_active_profile()
# Returns: str | None (None if no profile active at any scope)

# Set active profile
config.set_active_profile("dev", scope=Scope.LOCAL)

# Clear active profile
config.clear_active_profile(scope=Scope.LOCAL)

# Get project default profile
default = config.get_project_default()
# Returns: str | None

# Set project default
config.set_project_default("base")

# Clear project default
config.clear_project_default()
```

##### Settings Access

```python
# Get merged settings
settings = config.get_merged_settings()
# Returns: dict[str, Any] - Deep merge of USER < PROJECT < LOCAL

# Get module source overrides
sources = config.get_module_sources()
# Returns: dict[str, str] mapping module_id -> source_uri
```

##### Module Source Management

```python
# Add source override
config.add_source_override(
    module_id="provider-anthropic",
    source="git+https://github.com/user/custom-provider@main",
    scope=Scope.PROJECT
)

# Remove source override
removed = config.remove_source_override(
    module_id="provider-anthropic",
    scope=Scope.PROJECT
)
# Returns: True if removed, False if not found
```

##### Advanced Settings Management

```python
# Update arbitrary settings at a scope
config.update_settings(
    updates={"custom": {"feature": "enabled"}},
    scope=Scope.PROJECT
)
# Deep merges updates into PROJECT scope settings

# Get path for a scope
path = config.scope_to_path(Scope.LOCAL)
# Returns: Path object for the LOCAL scope
```

**→ See [Advanced Patterns](docs/USER_GUIDE.md#advanced-patterns) for multi-scope batch operations and more.**

### Utility Functions

#### deep_merge

```python
from amplifier_config import deep_merge

result = deep_merge(
    base={"a": {"b": 1, "c": 2}},
    overlay={"a": {"b": 999, "d": 3}}
)
# Returns: {"a": {"b": 999, "c": 2, "d": 3}}
# Overlay values replace base; unmodified base values preserved
```

**Parameters**:
- `base` (dict): Base dictionary
- `overlay` (dict): Overlay dictionary (values take precedence)

**Returns**: New dictionary with merged values (base and overlay unchanged)

**→ See [Deep Merge Algorithm Specification](docs/SPECIFICATION.md#deep-merge-algorithm-specification) for complete specification.**

---

## Settings File Format

```yaml
# settings.yaml (standard format)

# Profile management
profile:
  active: dev # Active profile name (set via set_active_profile)
  default: base # Project default profile (PROJECT scope only)

# Module source overrides
sources:
  provider-anthropic: git+https://github.com/user/custom-provider@main
  tool-filesystem: file:///home/dev/custom-tool

# Custom app-specific sections (library passes through via get_merged_settings)
custom:
  anything: apps can store custom configuration
  library: does not interpret these sections
```

**→ See [Settings File Schema](docs/SPECIFICATION.md#settings-file-schema) for complete schema specification.**

---

## Error Handling

```python
from amplifier_config import ConfigError, ConfigFileError, ConfigValidationError

try:
    config.set_active_profile("dev", scope=Scope.LOCAL)
except ConfigFileError as e:
    # Raised when file I/O fails (write errors, permission denied, etc.)
    print(f"File error: {e}")
except ConfigValidationError as e:
    # Raised when configuration data is invalid
    print(f"Validation error: {e}")
except ConfigError as e:
    # Base exception for all config errors
    print(f"Config error: {e}")
```

**Exception hierarchy**:
- `ConfigError` - Base exception for all configuration errors
- `ConfigFileError` - File I/O errors (extends ConfigError)
- `ConfigValidationError` - Validation errors (extends ConfigError)

**Graceful degradation**: Missing files return `None` or empty dict (not an exception).

**→ See [Error Handling Specification](docs/SPECIFICATION.md#error-handling-specification) for complete error handling contracts.**

---

## Design Philosophy

amplifier-config provides configuration **mechanism**, not policy:

- **How** to resolve scopes (USER < PROJECT < LOCAL)
- **How** to merge configurations (deep recursive merge)
- **How** to read/write files (YAML parsing)

Applications provide configuration **policy**:

- **Where** settings files live (path conventions)
- **What** settings mean (interpretation)
- **When** to reload (caching strategy)

This separation enables the library to work across diverse application types without modification.

**→ See [Design Philosophy and Rationale](docs/SPECIFICATION.md#design-philosophy-and-rationale) for complete design rationale.**

---

## Testing

### Running Tests

```bash
# Install development dependencies
uv pip install -e ".[dev]"

# Or using uv sync
uv sync --dev

# Run tests
pytest

# Run with coverage
pytest --cov=amplifier_config --cov-report=html
```

**→ See [Testing Strategy](docs/SPECIFICATION.md#testing-strategy) for complete testing specification.**

---

## Dependencies

**Runtime**:
- Python >=3.11 (stdlib: pathlib, dataclasses, typing)
- pyyaml >=6.0 (optional, for YAML file support)

**Development**:
- pytest >=8.0
- pytest-cov

**→ See [Dependencies Specification](docs/SPECIFICATION.md#dependencies) for rationale and philosophy.**

---

## Contributing

This project welcomes contributions and suggestions. Most contributions require you to agree to a
Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us
the rights to use your contribution. For details, visit https://cla.opensource.microsoft.com.

When you submit a pull request, a CLA bot will automatically determine whether you need to provide
a CLA and decorate the PR appropriately (e.g., status check, comment). Simply follow the instructions
provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or
contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.

---

## Trademarks

This project may contain trademarks or logos for projects, products, or services. Authorized use of Microsoft
trademarks or logos is subject to and must follow
[Microsoft's Trademark & Brand Guidelines](https://www.microsoft.com/en-us/legal/intellectualproperty/trademarks/usage/general).
Use of Microsoft trademarks or logos in modified versions of this project must not cause confusion or imply Microsoft sponsorship.
Any use of third-party trademarks or logos are subject to those third-party's policies.
