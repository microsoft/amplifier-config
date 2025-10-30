"""Tests for utility functions."""

from amplifier_config.utils import deep_merge


class TestDeepMerge:
    """Test deep_merge function."""

    def test_empty_dicts(self):
        """Test merging empty dictionaries."""
        assert deep_merge({}, {}) == {}

    def test_empty_base(self):
        """Test merging with empty base."""
        overlay = {"a": 1, "b": 2}
        assert deep_merge({}, overlay) == {"a": 1, "b": 2}

    def test_empty_overlay(self):
        """Test merging with empty overlay."""
        base = {"a": 1, "b": 2}
        assert deep_merge(base, {}) == {"a": 1, "b": 2}

    def test_simple_merge(self):
        """Test simple non-conflicting merge."""
        base = {"a": 1, "b": 2}
        overlay = {"c": 3, "d": 4}
        assert deep_merge(base, overlay) == {"a": 1, "b": 2, "c": 3, "d": 4}

    def test_overlay_wins(self):
        """Test overlay takes precedence for simple values."""
        base = {"a": 1, "b": 2}
        overlay = {"b": 20, "c": 3}
        assert deep_merge(base, overlay) == {"a": 1, "b": 20, "c": 3}

    def test_nested_merge(self):
        """Test merging nested dictionaries."""
        base = {"a": 1, "b": {"c": 2, "d": 3}}
        overlay = {"b": {"c": 20}, "e": 5}
        result = deep_merge(base, overlay)
        assert result == {"a": 1, "b": {"c": 20, "d": 3}, "e": 5}

    def test_deep_nested_merge(self):
        """Test merging deeply nested dictionaries."""
        base = {"level1": {"level2": {"level3": {"a": 1, "b": 2}}}}
        overlay = {"level1": {"level2": {"level3": {"b": 20, "c": 3}}}}
        result = deep_merge(base, overlay)
        expected = {"level1": {"level2": {"level3": {"a": 1, "b": 20, "c": 3}}}}
        assert result == expected

    def test_overlay_replaces_non_dict(self):
        """Test overlay replaces non-dict with dict."""
        base = {"a": 1, "b": "string"}
        overlay = {"b": {"c": 2}}
        assert deep_merge(base, overlay) == {"a": 1, "b": {"c": 2}}

    def test_dict_replaces_non_dict(self):
        """Test dict in base gets replaced by non-dict in overlay."""
        base = {"a": 1, "b": {"c": 2}}
        overlay = {"b": "string"}
        assert deep_merge(base, overlay) == {"a": 1, "b": "string"}

    def test_lists_not_merged(self):
        """Test lists are replaced, not merged."""
        base = {"a": [1, 2, 3]}
        overlay = {"a": [4, 5]}
        assert deep_merge(base, overlay) == {"a": [4, 5]}

    def test_original_not_modified(self):
        """Test that original dicts are not modified."""
        base = {"a": {"b": 1}}
        overlay = {"a": {"c": 2}}
        result = deep_merge(base, overlay)

        # Result should be merged
        assert result == {"a": {"b": 1, "c": 2}}

        # Originals should be unchanged
        assert base == {"a": {"b": 1}}
        assert overlay == {"a": {"c": 2}}

    def test_realistic_settings_merge(self):
        """Test merging realistic settings structure."""
        base = {"profile": {"active": "foundation"}, "sources": {"provider-anthropic": "git+https://...@v1.0"}}
        overlay = {"profile": {"active": "dev"}, "sources": {"provider-openai": "git+https://...@v2.0"}}
        result = deep_merge(base, overlay)
        expected = {
            "profile": {"active": "dev"},  # Overlay wins
            "sources": {  # Merged
                "provider-anthropic": "git+https://...@v1.0",
                "provider-openai": "git+https://...@v2.0",
            },
        }
        assert result == expected
