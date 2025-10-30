"""Exceptions for amplifier-config."""


class ConfigError(Exception):
    """Base exception for configuration errors."""

    pass


class ConfigFileError(ConfigError):
    """Error reading or writing configuration file."""

    pass


class ConfigValidationError(ConfigError):
    """Error validating configuration data."""

    pass
