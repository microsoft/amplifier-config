# amplifier-config User Guide

**Practical patterns for using configuration management in your applications**

This guide shows you how to use amplifier-config in real applications. For technical specifications, see [SPECIFICATION.md](./SPECIFICATION.md).

---

## When to Use Which Scope

### LOCAL Scope

**Purpose**: Developer-specific overrides, temporary experiments

**Use cases**:
- Testing local module changes
- Developer-specific tool preferences
- Temporary overrides (not committed to version control)

**Example**:
```yaml
# .amplifier/settings.local.yaml (gitignored)
profile:
  active: experimental  # Testing new profile

sources:
  provider-anthropic: file:///home/dev/local-provider  # Local development
```

**Best practices**:
- Add `.amplifier/settings.local.yaml` to `.gitignore`
- Use for temporary overrides only
- Document expected LOCAL settings in project README if shared

---

### PROJECT Scope

**Purpose**: Team-shared settings, project consistency

**Use cases**:
- Project default profile
- Pinned module versions for consistency
- Team-shared module source overrides

**Example**:
```yaml
# .amplifier/settings.yaml (committed to git)
profile:
  default: dev  # Team uses 'dev' profile by default

sources:
  provider-anthropic: git+https://github.com/org/custom-provider@v1.2.0
  # Team uses specific version for consistency
```

**Best practices**:
- Commit to version control
- Document why settings exist (comments in YAML)
- Pin versions for reproducibility

---

### USER Scope

**Purpose**: User-global defaults across all projects

**Use cases**:
- Personal default profile
- User-wide module source overrides
- Global preferences

**Example**:
```yaml
# ~/.amplifier/settings.yaml
profile:
  active: base  # My preferred default

sources:
  # My global overrides (apply to all projects unless overridden)
  tool-custom: git+https://github.com/me/my-tool@main
```

**Best practices**:
- Keep minimal (most settings should be project-specific)
- Document in personal notes
- Don't assume others have same USER settings

---

## Application Examples

### CLI Application

```python
from amplifier_config import ConfigManager, ConfigPaths, Scope
from pathlib import Path

# Define CLI path conventions
paths = ConfigPaths(
    user=Path.home() / ".amplifier" / "settings.yaml",
    project=Path(".amplifier/settings.yaml"),
    local=Path(".amplifier/settings.local.yaml"),
)

config = ConfigManager(paths=paths)

# Get active profile (LOCAL > PROJECT > USER)
active = config.get_active_profile()
if active is None:
    # Use project default or hardcoded fallback
    active = config.get_project_default() or "base"

print(f"Active profile: {active}")

# Get all merged settings
settings = config.get_merged_settings()

# Module source overrides (merged across all scopes)
sources = config.get_module_sources()
print(f"Module sources: {sources}")
```

---

### Web Application

```python
from amplifier_config import ConfigManager, ConfigPaths, Scope
from pathlib import Path

def create_workspace_config(user_id: str, workspace_id: str) -> ConfigManager:
    """Create config manager for web workspace.

    Web apps use different path conventions than CLI.
    """
    # Web-specific paths (different from CLI!)
    paths = ConfigPaths(
        user=Path(f"/var/amplifier/users/{user_id}/settings.yaml"),
        project=Path(f"/var/amplifier/workspaces/{workspace_id}/settings.yaml"),
        local=Path(f"/var/amplifier/workspaces/{workspace_id}/settings.local.yaml"),
    )

    return ConfigManager(paths=paths)

# Use in API endpoint
async def set_workspace_profile(workspace_id: str, profile_name: str, user: User):
    """Set active profile for workspace."""
    config = create_workspace_config(user.id, workspace_id)

    # Set at PROJECT scope (workspace-level setting)
    config.set_active_profile(profile_name, scope=Scope.PROJECT)

    return {"profile": profile_name, "workspace": workspace_id}

# Get workspace settings
async def get_workspace_settings(workspace_id: str, user: User):
    """Get merged workspace settings."""
    config = create_workspace_config(user.id, workspace_id)

    return {
        "active_profile": config.get_active_profile(),
        "settings": config.get_merged_settings(),
        "sources": config.get_module_sources(),
    }
```

---

### Desktop Application

```python
from amplifier_config import ConfigManager, ConfigPaths
from pathlib import Path
import platformdirs

def create_desktop_config(app_name: str) -> ConfigManager:
    """Create config manager for desktop app.

    Uses platform-appropriate paths (macOS/Windows/Linux).
    """
    # Platform-specific paths via platformdirs
    user_config_dir = platformdirs.user_config_dir(app_name)
    project_config_dir = Path.cwd() / ".config"

    paths = ConfigPaths(
        user=Path(user_config_dir) / "settings.yaml",
        project=project_config_dir / "settings.yaml",
        local=project_config_dir / "settings.local.yaml",
    )

    return ConfigManager(paths=paths)

# Platform-appropriate paths automatically
# macOS: ~/Library/Application Support/Amplifier/settings.yaml
# Linux: ~/.config/Amplifier/settings.yaml
# Windows: %APPDATA%\Amplifier\settings.yaml
config = create_desktop_config("Amplifier")
```

---

### Testing

```python
from amplifier_config import ConfigManager, ConfigPaths, Scope
from pathlib import Path
import tempfile

def test_scope_precedence():
    """Test LOCAL > PROJECT > USER precedence."""

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # Test-specific paths (isolated from real config)
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

        # Clear local override
        config.clear_active_profile(scope=Scope.LOCAL)
        assert config.get_active_profile() == "dev"  # Falls back to PROJECT
```

---

## Advanced Patterns

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

# Clear project default
config.clear_project_default()

# Now USER default becomes active
assert config.get_active_profile() == "base"
```

---

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
removed = config.remove_source_override("provider-anthropic", scope=Scope.PROJECT)
# Returns: True (was removed)

# Try removing non-existent override
removed = config.remove_source_override("nonexistent", scope=Scope.USER)
# Returns: False (not found)
```

---

### Arbitrary Settings Updates

```python
# Update custom settings at a scope
config.update_settings(
    updates={
        "custom": {
            "feature_flags": {
                "new_ui": True,
                "beta_features": False
            }
        }
    },
    scope=Scope.PROJECT
)

# Get merged settings (includes custom sections)
settings = config.get_merged_settings()
# Returns: {
#   "profile": {...},
#   "sources": {...},
#   "custom": {
#     "feature_flags": {
#       "new_ui": True,
#       "beta_features": False
#     }
#   }
# }
```

---

## Troubleshooting

### Issue: Profile Not Loading

**Symptom**: `get_active_profile()` returns `None`

**Causes**:
1. No profile set at any scope
2. Profile files don't exist
3. YAML syntax error

**Solution**:
```python
# Check each scope individually
config = ConfigManager(paths=paths)

# Check if files exist
print(f"User file exists: {paths.user.exists()}")
print(f"Project file exists: {paths.project.exists()}")
print(f"Local file exists: {paths.local.exists()}")

# If no profile set, use default
active = config.get_active_profile() or config.get_project_default() or "base"
```

---

### Issue: Settings Not Merging

**Symptom**: PROJECT settings not visible when LOCAL is set

**Cause**: Misunderstanding merge behavior

**Explanation**:
```yaml
# PROJECT
config:
  timeout: 30
  retries: 3

# LOCAL
profile:
  active: dev

# Result: Both preserved!
# Merge is RECURSIVE - LOCAL doesn't erase PROJECT
```

Deep merge preserves unmodified values. If LOCAL doesn't mention `config`, PROJECT values remain.

---

### Issue: Module Source Not Found

**Symptom**: Module source override not working

**Causes**:
1. Wrong scope (e.g., set in USER but PROJECT overrides)
2. Typo in module ID
3. Source added but config not reloaded

**Solution**:
```python
# Verify what config sees
sources = config.get_module_sources()
print(f"All sources: {sources}")

# Check specific module
module_id = "provider-anthropic"
if module_id in sources:
    print(f"{module_id} source: {sources[module_id]}")
else:
    print(f"{module_id} not found in any scope")
```

---

### Issue: PyYAML Not Available

**Symptom**: `ConfigError("PyYAML not available...")`

**Cause**: pyyaml not installed

**Solution**:
```bash
# Install PyYAML
uv pip install pyyaml

# Or add to your project
uv add pyyaml
```

---

## Best Practices

### For Users

1. **Start with USER scope** - Set your personal defaults
2. **Use PROJECT scope for teams** - Commit team-shared settings
3. **Use LOCAL for experiments** - Temporary, not committed
4. **Keep settings minimal** - Only set what you need to override
5. **Document why** - Add comments explaining non-obvious settings

### For Applications

1. **Inject paths explicitly** - Don't hardcode `.amplifier/`
2. **Provide clear defaults** - Fallback to sensible values if no settings
3. **Don't cache unless profiling shows need** - ConfigManager is already fast
4. **Handle missing files gracefully** - Not an error condition
5. **Use correct scope** - USER for personal, PROJECT for team, LOCAL for temporary

### For Library Consumers

1. **Trust deep merge** - It preserves unmodified values correctly
2. **Scope precedence is absolute** - LOCAL always wins
3. **None is a value** - Use absence to unset, not `null`
4. **Test with temp paths** - Isolate tests from real configuration

---

## Related Documentation

- **[SPECIFICATION.md](./SPECIFICATION.md)** - Complete technical specification
- **[amplifier-config README](../README.md)** - API reference and installation
- **[amplifier-profiles](https://github.com/microsoft/amplifier-profiles)** - Profile system that uses this config library
- **[amplifier-module-resolution](https://github.com/microsoft/amplifier-module-resolution)** - Module resolution that uses this config library
