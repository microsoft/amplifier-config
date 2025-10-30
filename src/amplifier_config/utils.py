"""Utility functions for amplifier-config."""

from typing import Any


def deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    """Deep merge two dictionaries with overlay precedence.

    Recursively merges nested dictionaries. Non-dict values in overlay
    completely replace corresponding values in base.

    Args:
        base: Base dictionary
        overlay: Overlay dictionary (takes precedence)

    Returns:
        New merged dictionary (base and overlay are not modified)

    Examples:
        >>> base = {"a": 1, "b": {"c": 2, "d": 3}}
        >>> overlay = {"b": {"c": 20}, "e": 5}
        >>> deep_merge(base, overlay)
        {'a': 1, 'b': {'c': 20, 'd': 3}, 'e': 5}

        >>> deep_merge({}, {"a": 1})
        {'a': 1}

        >>> deep_merge({"a": 1}, {})
        {'a': 1}
    """
    result = base.copy()

    for key, value in overlay.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # Both base and overlay have dict at this key - recurse
            result[key] = deep_merge(result[key], value)
        else:
            # Overlay wins - replace completely
            result[key] = value

    return result
