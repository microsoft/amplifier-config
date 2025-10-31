# amplifier-config

**Hierarchical configuration management for Amplifier applications**

amplifier-config provides pure configuration mechanism with three-scope resolution (user, project, local), deep merge semantics, and YAML file I/O. Apps inject path conventions; the library handles resolution logic.

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

**Example resolution**:

```yaml
# ~/.amplifier/settings.yaml (USER scope)
profile:
  active: base  # Simple profile name

# .amplifier/settings.yaml (PROJECT scope - overrides user)
profile:
  default: developer-expertise:dev  # Collection syntax

# .amplifier/settings.local.yaml (LOCAL scope - overrides project)
profile:
  active: design-intelligence:designer  # Collection syntax - this wins!
```

Result: `config.get_active_profile()` returns `"design-intelligence:designer"`

**Note**: Config manager stores profile names as strings. The profile loader (amplifier-profiles) resolves collection syntax (`collection:name`).

### Deep Merge Semantics

Overlays merge recursively with overlay values taking precedence:

```yaml
# Base (USER)
config:
  providers:
    anthropic:
      model: claude-sonnet-4-5
      temperature: 0.5

# Overlay (PROJECT)
config:
  providers:
    anthropic:
      model: claude-opus-4-1  # Overrides model
      # temperature preserved from base
    openai:
      model: gpt-5  # Added

# Result (MERGED)
config:
  providers:
    anthropic:
      model: claude-opus-4-1        # From overlay
      temperature: 0.5            # From base (preserved)
    openai:
      model: gpt-5                # From overlay (added)
```

### Path Injection

The library does NOT hardcode paths like `.amplifier/` or `~/.amplifier/`. Different applications use different path conventions:

- **CLI**: `.amplifier/`, `~/.amplifier/`
- **Web**: `/var/amplifier/users/{id}/`, `/var/amplifier/workspaces/{id}/`
- **Desktop**: Platform-specific application data directories
- **Testing**: Temporary directories

Apps inject their path conventions; the library provides the resolution mechanism.

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

# Example: CLI paths
cli_paths = ConfigPaths(
    user=Path.home() / ".amplifier" / "settings.yaml",
    project=Path(".amplifier/settings.yaml"),
    local=Path(".amplifier/settings.local.yaml"),
)

# Example: Web paths
web_paths = ConfigPaths(
    user=Path(f"/var/amplifier/users/{user_id}/settings.yaml"),
    project=Path(f"/var/amplifier/workspaces/{workspace_id}/settings.yaml"),
    local=Path(f"/var/amplifier/workspaces/{workspace_id}/settings.local.yaml"),
)
```

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
# Returns: str | None
# None if no profile is active at any scope

# Set active profile
config.set_active_profile("dev", scope=Scope.LOCAL)
# Writes to LOCAL scope file

# Clear active profile
config.clear_active_profile(scope=Scope.LOCAL)
# Removes active profile from LOCAL scope
```

##### Project Defaults

```python
# Get project default profile
default = config.get_project_default()
# Returns: str | None
# None if no project default set

# Set project default
config.set_project_default("base")
# Writes to PROJECT scope

# Clear project default
config.clear_project_default()
# Removes from PROJECT scope
```

##### Settings Access

```python
# Get merged settings
settings = config.get_merged_settings()
# Returns: dict[str, Any]
# Deep merge of USER < PROJECT < LOCAL

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
# Adds to sources section in PROJECT scope

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

### Utility Functions

#### deep_merge

```python
from amplifier_config import deep_merge

result = deep_merge(
    base={"a": {"b": 1, "c": 2}},
    overlay={"a": {"b": 999, "d": 3}}
)
# Returns: {"a": {"b": 999, "c": 2, "d": 3}}

# Overlay values completely replace base values
result = deep_merge(
    base={"a": {"b": 1, "c": 2}},
    overlay={"a": {"b": 999}}
)
# Returns: {"a": {"b": 999, "c": 2}}  # c preserved, b overridden
```

**Parameters**:

- `base` (dict): Base dictionary
- `overlay` (dict): Overlay dictionary (values take precedence)

**Returns**: New dictionary with merged values (base and overlay unchanged)

**Note**: None values in overlay are treated as regular values, not deletion markers. To remove a key, omit it from the overlay.

---

## Usage Examples

### CLI Application

```python
from amplifier_config import ConfigManager, ConfigPaths, Scope
from pathlib import Path

# CLI defines its path conventions
paths = ConfigPaths(
    user=Path.home() / ".amplifier" / "settings.yaml",
    project=Path(".amplifier/settings.yaml"),
    local=Path(".amplifier/settings.local.yaml"),
)

config = ConfigManager(paths=paths)

# Profile management
active = config.get_active_profile()
if active is None:
    # Use project default or fallback
    active = config.get_project_default() or "base"

# Get all merged settings
settings = config.get_merged_settings()

# Module source overrides
sources = config.get_module_sources()
```

### Web Application

```python
from amplifier_config import ConfigManager, ConfigPaths
from pathlib import Path

def create_workspace_config(user_id: str, workspace_id: str) -> ConfigManager:
    """Create config manager for web workspace."""

    # Web defines its path conventions (different from CLI)
    paths = ConfigPaths(
        user=Path(f"/var/amplifier/users/{user_id}/settings.yaml"),
        project=Path(f"/var/amplifier/workspaces/{workspace_id}/settings.yaml"),
        local=Path(f"/var/amplifier/workspaces/{workspace_id}/settings.local.yaml"),
    )

    return ConfigManager(paths=paths)

# Use in API endpoint
@app.post("/workspaces/{workspace_id}/profile")
async def set_workspace_profile(workspace_id: str, profile_name: str, user: User):
    config = create_workspace_config(user.id, workspace_id)
    config.set_active_profile(profile_name, scope=Scope.PROJECT)
    return {"profile": profile_name}
```

### Desktop Application

```python
from amplifier_config import ConfigManager, ConfigPaths
from pathlib import Path
import platformdirs

def create_desktop_config(app_name: str) -> ConfigManager:
    """Create config manager for desktop app."""

    # Platform-specific paths (macOS/Windows/Linux)
    user_config_dir = platformdirs.user_config_dir(app_name)
    project_config_dir = Path.cwd() / ".config"

    paths = ConfigPaths(
        user=Path(user_config_dir) / "settings.yaml",
        project=project_config_dir / "settings.yaml",
        local=project_config_dir / "settings.local.yaml",
    )

    return ConfigManager(paths=paths)

# Platform-appropriate paths automatically
config = create_desktop_config("Amplifier")
```

### Testing

```python
from amplifier_config import ConfigManager, ConfigPaths, Scope
from pathlib import Path
import tempfile

def test_scope_precedence():
    """Test LOCAL > PROJECT > USER precedence."""

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # Test-specific paths
        paths = ConfigPaths(
            user=tmp_path / "user.yaml",
            project=tmp_path / "project.yaml",
            local=tmp_path / "local.yaml",
        )

        config = ConfigManager(paths=paths)

        # Set at different scopes
        config.set_active_profile("base", scope=Scope.USER)
        assert config.get_active_profile() == "base"

        config.set_active_profile("dev", scope=Scope.PROJECT)
        assert config.get_active_profile() == "dev"  # PROJECT overrides USER

        config.set_active_profile("full", scope=Scope.LOCAL)
        assert config.get_active_profile() == "full"  # LOCAL overrides PROJECT
```

---

## Settings File Format

### Structure

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

### Conventions

- Flat structure for common settings
- Nested structure for complex configuration
- App-specific sections allowed (library passes through unchanged)

---

## Design Philosophy

### Mechanism, Not Policy

The library provides configuration **mechanism**:

- **How** to resolve scopes (USER < PROJECT < LOCAL)
- **How** to merge configurations (deep recursive merge)
- **How** to read/write files (YAML parsing)

Applications provide configuration **policy**:

- **Where** settings files live (path conventions)
- **What** settings mean (interpretation)
- **When** to reload (caching strategy)

This separation enables the library to work across diverse application types without modification.

### Path Injection Rationale

**Why not hardcode `.amplifier/` paths?**

Different applications need different conventions:

| Application | User Path                                               | Project Path                                   |
| ----------- | ------------------------------------------------------- | ---------------------------------------------- |
| CLI         | `~/.amplifier/settings.yaml`                            | `.amplifier/settings.yaml`                     |
| Web         | `/var/amplifier/users/{id}/settings.yaml`               | `/var/amplifier/workspaces/{id}/settings.yaml` |
| Desktop     | `~/Library/Application Support/Amplifier/settings.yaml` | `.config/settings.yaml`                        |
| Testing     | `/tmp/test-{uuid}/user.yaml`                            | `/tmp/test-{uuid}/project.yaml`                |

By accepting paths via injection, the library works for all contexts without modification.

### Deep Merge Rationale

**Why recursive merge instead of replace?**

Overlays typically modify **part** of configuration, not all of it:

```yaml
# USER: Complete base configuration
providers:
  anthropic: {model: claude-sonnet-4-5, temperature: 0.5, max_tokens: 100000}
  openai: {model: gpt-5, temperature: 0.7}

# PROJECT: Override just the model
providers:
  anthropic: {model: claude-opus-4-1}
  # Want to preserve temperature and max_tokens!
```

With deep merge, overlay modifies only specified values. Without it, overlay must duplicate all base values.

---

## Error Handling

### Exceptions

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

**Usage**: Standard Python exception pattern. Access error message via `str(e)` or string formatting.

### Graceful Degradation

**Missing files**: Not an error - returns None or empty dict

```python
# No settings files exist yet
config = ConfigManager(paths=paths)
active = config.get_active_profile()
# Returns: None (not an exception)

settings = config.get_merged_settings()
# Returns: {} (empty dict)
```

**Missing PyYAML**: Clear error on first use

```python
# pyyaml not installed
config.get_active_profile()
# Raises: ConfigError("PyYAML not available - install with: uv pip install pyyaml")
```

**Philosophy**: Fail fast with actionable messages, not silent failures.

---

## Advanced Usage

### Merge Behavior

```python
from amplifier_config import deep_merge

# Deep merge preserves base values not overridden
base = {"config": {"feature_x": True, "feature_y": True, "timeout": 30}}
overlay = {"config": {"feature_x": False}}  # Override just feature_x

result = deep_merge(base, overlay)
# Returns: {"config": {"feature_x": False, "feature_y": True, "timeout": 30}}
```

### Multi-Scope Batch Operations

```python
# Set profile at multiple scopes
config.set_active_profile("base", scope=Scope.USER)      # User default
config.set_project_default("dev")                        # Project default
config.set_active_profile("full", scope=Scope.LOCAL)     # Local override

# Result: LOCAL wins
assert config.get_active_profile() == "full"

# Clear local override
config.clear_active_profile(scope=Scope.LOCAL)

# Now PROJECT default becomes active
assert config.get_active_profile() == "dev"
```

### Source Override Management

```python
# Add overrides at different scopes
config.add_source_override(
    "provider-anthropic",
    "git+https://github.com/user/custom@main",
    scope=Scope.PROJECT
)

config.add_source_override(
    "tool-filesystem",
    "file:///home/dev/local-tool",
    scope=Scope.LOCAL
)

# Get merged sources (LOCAL > PROJECT > USER)
sources = config.get_module_sources()
# Returns: {
#   "provider-anthropic": "git+https://...",  # From PROJECT
#   "tool-filesystem": "file:///home/dev/...", # From LOCAL
# }

# Remove override
config.remove_source_override("provider-anthropic", scope=Scope.PROJECT)
```

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

### Test Coverage

The library includes comprehensive tests:

- **Unit tests**: Scope resolution, deep merge algorithm, file I/O
- **Integration tests**: Multi-scope precedence, concurrent access
- **Property tests**: Merge associativity, scope transitivity
- **Edge cases**: Missing files, invalid YAML, None values

Target coverage: >90%

---

## Dependencies

### Runtime

**Required**:

- Python >=3.11 (stdlib: pathlib, dataclasses, tomllib)

**Optional**:

- pyyaml >=6.0 (YAML file support, graceful degradation without)

### Development

- pytest >=8.0
- pytest-cov

**Philosophy**: Minimal dependencies (only pyyaml optionally) enable maximum reusability.

---

## Design Decisions

### Why Frozen Dataclasses?

```python
@dataclass(frozen=True)
class ConfigPaths:
    ...
```

**Benefit**: Immutability prevents accidental modification
**Trade-off**: Slightly more verbose (create new instance to change), worth it for safety

### Why Scope Enum vs Strings?

```python
# Type-safe
config.set_active_profile("dev", scope=Scope.LOCAL)

# vs string literals (error-prone)
config.set_active_profile("dev", scope="local")  # Typo risk
```

**Benefit**: IDE autocomplete, type checking, self-documenting API

### Why Optional PyYAML?

Applications using JSON or other formats can still use the library:

```python
try:
    import yaml
except ImportError:
    yaml = None  # Library still imports, YAML methods raise clear errors
```

**Benefit**: Library remains usable even if YAML support not needed

---

## Philosophy Compliance

### Kernel Philosophy ✅

**"Mechanism, not policy"**:

- ✅ Library: How to resolve scopes (mechanism)
- ✅ App: Where settings files live (policy)

**"Small, stable, and boring"**:

- ✅ ~300 LOC
- ✅ Stable interfaces (Scope, ConfigPaths, ConfigManager)
- ✅ No complex patterns

**"Minimal dependencies"**:

- ✅ pyyaml only (and it's optional)
- ✅ No transitive sprawl

### Ruthless Simplicity ✅

**No caching**: Direct file reads

- YAGNI - Optimize if profiling shows bottleneck
- File I/O is fast enough for typical use

**No file watching**: No automatic reload on change

- YAGNI - Apps can add if needed
- Simpler without observer pattern

**No transactions**: Simple read/write

- YAGNI - Concurrent config updates are rare
- Add locking if proven needed

**Simple error model**: Single exception type

- Apps add rich formatting/display
- Library provides message + context

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
