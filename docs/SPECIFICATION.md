# amplifier-config Technical Specification

**Configuration management mechanism for Amplifier applications**

This document is the authoritative source for all technical contracts in amplifier-config. When implementation details conflict with this specification, this document is correct.

---

## Three-Scope Resolution Algorithm

### Overview

Configuration resolves in strict precedence order (highest wins):

```
┌─────────────────────────────────────────────────────────┐
│ LOCAL SCOPE (highest precedence)                        │
│ .amplifier/settings.local.yaml                          │
│ Developer-specific overrides (gitignored)               │
├─────────────────────────────────────────────────────────┤
│ PROJECT SCOPE (middle precedence)                       │
│ .amplifier/settings.yaml                                │
│ Team-shared settings (committed to git)                 │
├─────────────────────────────────────────────────────────┤
│ USER SCOPE (lowest precedence)                          │
│ ~/.amplifier/settings.yaml                              │
│ User-global defaults (applies to all projects)          │
└─────────────────────────────────────────────────────────┘

Resolution: Check LOCAL → PROJECT → USER → None
Merging: USER < PROJECT < LOCAL (deep recursive merge)
```

### Resolution Rules

**Rule 1: Scope Precedence**
```
LOCAL > PROJECT > USER
```
When the same setting exists in multiple scopes, higher scope always wins.

**Rule 2: Missing Files Are Not Errors**
- Absent scope files treated as empty dictionaries
- Resolution continues through remaining scopes
- Returns None/empty dict if no scopes define value

**Rule 3: Null Values Are Values**
- `profile: null` in LOCAL overrides PROJECT/USER
- To "unset", omit the key entirely from the scope

### Active Profile Resolution

Active profile resolves by checking scopes in precedence order:

```python
def get_active_profile() -> str | None:
    # Check LOCAL first
    if local_yaml exists and has profile.active:
        return local_yaml.profile.active

    # Check PROJECT next
    if project_yaml exists and has profile.active:
        return project_yaml.profile.active

    # Check USER last
    if user_yaml exists and has profile.active:
        return user_yaml.profile.active

    # No active profile at any scope
    return None
```

### Project Default Profile (Special Case)

Project defaults stored in PROJECT scope only:

```yaml
# PROJECT scope only (.amplifier/settings.yaml)
profile:
  default: base  # Project default
```

Not valid in USER or LOCAL scopes (silently ignored if present).

---

## Deep Merge Algorithm Specification

### Algorithm

```python
def deep_merge(base: dict, overlay: dict) -> dict:
    """Recursively merge overlay into base.

    Rules:
    1. Overlay values completely replace base values
    2. Dictionaries merge recursively
    3. Non-dict values replace (no merging)
    4. None is a value, not a deletion marker
    5. Original dicts unmodified (returns new dict)
    """
    result = base.copy()

    for key, overlay_value in overlay.items():
        if key in result:
            base_value = result[key]

            # Both dicts? Recurse
            if isinstance(base_value, dict) and isinstance(overlay_value, dict):
                result[key] = deep_merge(base_value, overlay_value)
            else:
                # Any other combination: overlay replaces base
                result[key] = overlay_value
        else:
            # Key only in overlay: add it
            result[key] = overlay_value

    return result
```

### Merge Examples

**Example 1: Partial Override**
```python
base = {
    "config": {
        "feature_x": True,
        "feature_y": True,
        "timeout": 30
    }
}

overlay = {
    "config": {
        "feature_x": False  # Override just this
    }
}

result = deep_merge(base, overlay)
# Returns: {
#     "config": {
#         "feature_x": False,   # From overlay
#         "feature_y": True,    # Preserved from base
#         "timeout": 30         # Preserved from base
#     }
# }
```

**Example 2: Adding New Keys**
```python
base = {"a": {"b": 1}}
overlay = {"a": {"c": 2}}

result = deep_merge(base, overlay)
# Returns: {"a": {"b": 1, "c": 2}}  # Both preserved
```

**Example 3: Replacing Non-Dict Values**
```python
base = {"x": [1, 2, 3]}
overlay = {"x": [4, 5]}

result = deep_merge(base, overlay)
# Returns: {"x": [4, 5]}  # Overlay replaces, does NOT merge lists
```

**Example 4: None Is a Value**
```python
base = {"x": 10}
overlay = {"x": None}

result = deep_merge(base, overlay)
# Returns: {"x": None}  # None replaces 10 (not deleted)
```

### Rationale

**Why deep merge instead of complete replacement?**

Overlays typically modify part of configuration, not all:

```yaml
# USER: Complete base configuration (100+ lines)
providers:
  anthropic:
    model: claude-sonnet-4-5
    temperature: 0.5
    max_tokens: 100000
  openai:
    model: gpt-5
    temperature: 0.7

# PROJECT: Override just the model (2 lines)
providers:
  anthropic:
    model: claude-opus-4-1
    # Want to preserve temperature and max_tokens!
```

Without deep merge, PROJECT must duplicate all base values.

---

## Path Injection Contract

### Contract

```python
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

### Application Responsibilities

Apps must provide **absolute paths** to existing or creatable directories.

**CLI example**:
```python
paths = ConfigPaths(
    user=Path.home() / ".amplifier" / "settings.yaml",
    project=Path(".amplifier/settings.yaml"),
    local=Path(".amplifier/settings.local.yaml"),
)
```

**Web example**:
```python
paths = ConfigPaths(
    user=Path(f"/var/amplifier/users/{user_id}/settings.yaml"),
    project=Path(f"/var/amplifier/workspaces/{workspace_id}/settings.yaml"),
    local=Path(f"/var/amplifier/workspaces/{workspace_id}/settings.local.yaml"),
)
```

### Path Conventions By Application

| Application | User Path | Project Path |
|-------------|-----------|-------------|
| CLI | `~/.amplifier/settings.yaml` | `.amplifier/settings.yaml` |
| Web | `/var/amplifier/users/{id}/settings.yaml` | `/var/amplifier/workspaces/{id}/settings.yaml` |
| Desktop | `~/Library/Application Support/Amplifier/settings.yaml` | `.config/settings.yaml` |
| Testing | `/tmp/test-{uuid}/user.yaml` | `/tmp/test-{uuid}/project.yaml` |

### Rationale

Different applications need different conventions. By accepting paths via injection, the library works for all contexts without modification.

---

## Error Handling Specification

### Exception Hierarchy

```python
class ConfigError(Exception):
    """Base exception for all configuration errors."""
    pass

class ConfigFileError(ConfigError):
    """Raised when file I/O fails."""
    pass

class ConfigValidationError(ConfigError):
    """Raised when configuration data is invalid."""
    pass
```

### When Exceptions Are Raised

**ConfigFileError**:
- File write fails (permission denied, disk full)
- File read fails (corrupted YAML, encoding errors)

**ConfigValidationError**:
- Invalid data types (e.g., profile: 123 instead of string)
- Invalid structure (missing required sections)

**ConfigError** (base):
- PyYAML not available when YAML operation attempted

### Graceful Degradation

**Missing Files**: NOT an error

```python
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

### Error Messages

All errors must be actionable:

```python
# GOOD: Tells user exactly what to do
ConfigError("PyYAML not available - install with: uv pip install pyyaml")

# BAD: Generic, not actionable
ConfigError("Missing dependency")
```

---

## Settings File Schema

### Complete Schema

```yaml
# Profile management
profile:
  active: str | null     # Active profile name (any scope)
  default: str | null    # Project default (PROJECT scope only)

# Module source overrides
sources:
  <module-id>: str  # Module ID -> source URI
  # Example:
  # provider-anthropic: git+https://github.com/user/custom@main

# Custom sections (library passes through unchanged)
custom:
  anything: ...  # Apps can store arbitrary configuration
  library: ...   # Library does not interpret custom sections
```

### Field Specifications

**profile.active** (any scope):
- Type: `str | null`
- Format: Simple profile name OR collection syntax (`collection:name`)
- Examples: `"dev"`, `"design-intelligence:designer"`, `null`
- Scope: USER, PROJECT, or LOCAL

**profile.default** (PROJECT scope only):
- Type: `str | null`
- Format: Same as profile.active
- Scope: PROJECT only (ignored if present in USER or LOCAL)
- Purpose: Project-level default when no active profile set

**sources** (any scope):
- Type: `dict[str, str]`
- Keys: Module IDs (e.g., `"provider-anthropic"`)
- Values: Source URIs (git URLs, file paths, package names)

### Scope-Specific Validation

```python
def validate_settings(data: dict, scope: Scope) -> None:
    """Validate settings for a scope.

    Validation rules:
    1. profile.default only valid in PROJECT scope
    2. profile.active valid in any scope
    3. All other sections pass through without validation
    """
    if "profile" in data and "default" in data["profile"]:
        if scope != Scope.PROJECT:
            raise ConfigValidationError(
                f"profile.default only valid in PROJECT scope, found in {scope.value}"
            )
```

---

## Design Philosophy and Rationale

### Mechanism, Not Policy

**Library provides**:
- How to resolve scopes (USER < PROJECT < LOCAL)
- How to merge configurations (deep recursive merge)
- How to read/write files (YAML parsing)

**Applications provide**:
- Where settings files live (path conventions)
- What settings mean (interpretation)
- When to reload (caching strategy)

This separation enables the library to work across diverse application types without modification.

### Design Decisions

#### Why Frozen Dataclasses?

```python
@dataclass(frozen=True)
class ConfigPaths:
    ...
```

**Benefit**: Immutability prevents accidental modification
**Trade-off**: Slightly more verbose (create new instance to change)
**Verdict**: Worth it for safety - configuration should be explicit

#### Why Scope Enum vs Strings?

```python
# Type-safe
config.set_active_profile("dev", scope=Scope.LOCAL)

# vs string literals (error-prone)
config.set_active_profile("dev", scope="local")  # Typo risk
```

**Benefits**:
- IDE autocomplete
- Type checking catches errors
- Self-documenting API

#### Why Optional PyYAML?

Applications using JSON or other formats can still use the library:

```python
try:
    import yaml
except ImportError:
    yaml = None  # Library still imports, YAML methods raise clear errors
```

**Benefit**: Library remains usable even if YAML support not needed

### Philosophy Compliance

**Kernel Philosophy ✅**:
- **"Mechanism, not policy"**: Library provides how, apps provide where/what
- **"Small, stable, and boring"**: ~300 LOC, stable interfaces
- **"Minimal dependencies"**: pyyaml only (and it's optional)

**Ruthless Simplicity ✅**:
- No caching (optimize if profiling shows bottleneck)
- No file watching (apps can add if needed)
- No transactions (concurrent config updates are rare)
- Simple error model (single exception hierarchy)

---

## Testing Strategy

### Test Categories

**Unit Tests**:
- Scope resolution order
- Deep merge algorithm (all edge cases)
- Path validation
- Exception handling

**Integration Tests**:
- Multi-scope precedence (LOCAL > PROJECT > USER)
- Concurrent file access
- Missing file handling

**Property Tests**:
- Merge associativity: `deep_merge(deep_merge(a, b), c) == deep_merge(a, deep_merge(b, c))`
- Scope transitivity: If LOCAL > PROJECT and PROJECT > USER, then LOCAL > USER

**Edge Cases**:
- Missing files (all scopes)
- Invalid YAML
- None values in overlays
- Empty dictionaries
- Concurrent writes to same file

### Target Coverage

- Line coverage: >90%
- Branch coverage: >85%
- All public APIs covered

---

## Dependencies

### Runtime

**Required**:
- Python >=3.11 (stdlib: pathlib, dataclasses, typing)

**Optional**:
- pyyaml >=6.0 (YAML file support, graceful degradation without)

### Development

- pytest >=8.0
- pytest-cov

### Dependency Philosophy

Minimal dependencies (only pyyaml optionally) enable maximum reusability across applications.

---

## When to Use This Library

**Use amplifier-config when**:
- You need hierarchical configuration (user/project/local scopes)
- You want deep merge semantics (preserve unmodified values)
- You need path injection (different apps, different conventions)
- You want mechanism-only library (no policy baked in)

**Don't use amplifier-config when**:
- You only need single-file configuration
- You want complete replacement (not merge) on override
- You need complex validation (build on top, don't fork)
- You need database-backed config (different mechanism entirely)

---

## Summary

amplifier-config provides **pure configuration mechanism**:
- Three-scope resolution (LOCAL > PROJECT > USER)
- Deep recursive merge
- Path injection for diverse application types
- Minimal dependencies (pyyaml optional)
- Simple error handling

Applications inject path policy; library handles resolution. This separation enables reuse across CLI, web, desktop, and testing contexts without modification.

**Key principle**: Library provides "how", applications provide "where" and "what".
