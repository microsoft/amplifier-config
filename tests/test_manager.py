"""Tests for ConfigManager."""

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from amplifier_config import ConfigManager
from amplifier_config import ConfigPaths
from amplifier_config import Scope


class TestConfigManager:
    """Test ConfigManager class."""

    @pytest.fixture
    def temp_paths(self):
        """Create temporary paths for testing."""
        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            paths = ConfigPaths(
                user=tmpdir_path / "user" / "settings.yaml",
                project=tmpdir_path / "project" / "settings.yaml",
                local=tmpdir_path / "local" / "settings.local.yaml",
            )
            yield paths

    @pytest.fixture
    def manager(self, temp_paths):
        """Create ConfigManager with temp paths."""
        return ConfigManager(temp_paths)

    # ===== Active Profile Tests =====

    def test_get_active_profile_none_when_no_settings(self, manager):
        """Test get_active_profile returns None when no settings exist."""
        assert manager.get_active_profile() is None

    def test_set_and_get_active_profile(self, manager):
        """Test setting and getting active profile."""
        manager.set_active_profile("dev", scope=Scope.LOCAL)
        assert manager.get_active_profile() == "dev"

    def test_active_profile_scope_precedence(self, manager):
        """Test active profile resolution order: local > project > user."""
        # Set in all scopes
        manager.set_active_profile("user-profile", scope=Scope.USER)
        manager.set_active_profile("project-profile", scope=Scope.PROJECT)
        manager.set_active_profile("local-profile", scope=Scope.LOCAL)

        # Local should win
        assert manager.get_active_profile() == "local-profile"

        # Clear local, project should win
        manager.clear_active_profile(scope=Scope.LOCAL)
        assert manager.get_active_profile() == "project-profile"

        # Clear project, user should win
        manager.clear_active_profile(scope=Scope.PROJECT)
        assert manager.get_active_profile() == "user-profile"

        # Clear user, should be None
        manager.clear_active_profile(scope=Scope.USER)
        assert manager.get_active_profile() is None

    def test_clear_active_profile_nonexistent(self, manager):
        """Test clearing active profile when it doesn't exist."""
        # Should not raise
        manager.clear_active_profile(scope=Scope.LOCAL)
        assert manager.get_active_profile() is None

    def test_set_active_profile_creates_parent_dirs(self, manager):
        """Test setting profile creates parent directories."""
        manager.set_active_profile("test", scope=Scope.USER)
        assert manager.paths.user.parent.exists()
        assert manager.paths.user.exists()

    # ===== Project Default Tests =====

    def test_get_project_default_none_when_no_settings(self, manager):
        """Test get_project_default returns None when no settings exist."""
        assert manager.get_project_default() is None

    def test_set_and_get_project_default(self, manager):
        """Test setting and getting project default."""
        manager.set_project_default("foundation")
        assert manager.get_project_default() == "foundation"

    def test_clear_project_default(self, manager):
        """Test clearing project default."""
        manager.set_project_default("foundation")
        assert manager.get_project_default() == "foundation"

        manager.clear_project_default()
        assert manager.get_project_default() is None

    def test_clear_project_default_nonexistent(self, manager):
        """Test clearing project default when it doesn't exist."""
        # Should not raise
        manager.clear_project_default()
        assert manager.get_project_default() is None

    # ===== Module Sources Tests =====

    def test_get_module_sources_empty_when_no_settings(self, manager):
        """Test get_module_sources returns empty dict when no settings exist."""
        assert manager.get_module_sources() == {}

    def test_add_and_get_module_source(self, manager):
        """Test adding and getting module source."""
        manager.add_source_override(
            "provider-anthropic",
            "git+https://github.com/microsoft/amplifier-module-provider-anthropic@v1.0",
            scope=Scope.PROJECT,
        )
        sources = manager.get_module_sources()
        assert "provider-anthropic" in sources
        assert (
            sources["provider-anthropic"] == "git+https://github.com/microsoft/amplifier-module-provider-anthropic@v1.0"
        )

    def test_module_sources_scope_precedence(self, manager):
        """Test module sources resolution order: local > project > user."""
        # Add same module with different sources in each scope
        manager.add_source_override("test-module", "user-source", scope=Scope.USER)
        manager.add_source_override("test-module", "project-source", scope=Scope.PROJECT)
        manager.add_source_override("test-module", "local-source", scope=Scope.LOCAL)

        # Local should win
        sources = manager.get_module_sources()
        assert sources["test-module"] == "local-source"

    def test_module_sources_merge_across_scopes(self, manager):
        """Test module sources from different scopes are merged."""
        manager.add_source_override("module1", "source1", scope=Scope.USER)
        manager.add_source_override("module2", "source2", scope=Scope.PROJECT)
        manager.add_source_override("module3", "source3", scope=Scope.LOCAL)

        sources = manager.get_module_sources()
        assert sources == {
            "module1": "source1",
            "module2": "source2",
            "module3": "source3",
        }

    def test_remove_module_source(self, manager):
        """Test removing module source."""
        manager.add_source_override("test-module", "test-source", scope=Scope.PROJECT)
        assert "test-module" in manager.get_module_sources()

        removed = manager.remove_source_override("test-module", scope=Scope.PROJECT)
        assert removed is True
        assert "test-module" not in manager.get_module_sources()

    def test_remove_nonexistent_module_source(self, manager):
        """Test removing nonexistent module source."""
        removed = manager.remove_source_override("nonexistent", scope=Scope.PROJECT)
        assert removed is False

    # ===== Merged Settings Tests =====

    def test_get_merged_settings_empty_when_no_settings(self, manager):
        """Test get_merged_settings returns empty dict when no settings exist."""
        assert manager.get_merged_settings() == {}

    def test_get_merged_settings_single_scope(self, manager):
        """Test get_merged_settings with single scope."""
        manager.set_active_profile("test", scope=Scope.LOCAL)
        merged = manager.get_merged_settings()
        assert merged == {"profile": {"active": "test"}}

    def test_get_merged_settings_multiple_scopes(self, manager):
        """Test get_merged_settings merges all scopes."""
        # Add different settings in each scope
        manager.set_active_profile("user-profile", scope=Scope.USER)
        manager.set_project_default("foundation")
        manager.add_source_override("module1", "source1", scope=Scope.LOCAL)

        merged = manager.get_merged_settings()

        # Should have all settings
        assert "profile" in merged
        assert merged["profile"]["active"] == "user-profile"  # From user
        assert merged["profile"]["default"] == "foundation"  # From project
        assert "sources" in merged
        assert merged["sources"]["module1"] == "source1"  # From local

    def test_get_merged_settings_precedence(self, manager):
        """Test get_merged_settings respects precedence: local > project > user."""
        # Set same key in all scopes
        manager.add_source_override("test-module", "user-source", scope=Scope.USER)
        manager.add_source_override("test-module", "project-source", scope=Scope.PROJECT)
        manager.add_source_override("test-module", "local-source", scope=Scope.LOCAL)

        merged = manager.get_merged_settings()
        # Local should win
        assert merged["sources"]["test-module"] == "local-source"

    # ===== File System Tests =====

    def test_write_creates_parent_directories(self, manager, temp_paths):
        """Test that write operations create parent directories."""
        # Verify parent doesn't exist
        assert not temp_paths.user.parent.exists()

        # Write to user settings
        manager.set_active_profile("test", scope=Scope.USER)

        # Parent should now exist
        assert temp_paths.user.parent.exists()
        assert temp_paths.user.exists()

    def test_files_are_independent(self, manager):
        """Test that different scopes use different files."""
        manager.set_active_profile("user-profile", scope=Scope.USER)
        manager.set_active_profile("project-profile", scope=Scope.PROJECT)
        manager.set_active_profile("local-profile", scope=Scope.LOCAL)

        # All three files should exist
        assert manager.paths.user.exists()
        assert manager.paths.project.exists()
        assert manager.paths.local.exists()

        # Should contain different values
        user_profile = manager._read_yaml(manager.paths.user)["profile"]["active"]
        project_profile = manager._read_yaml(manager.paths.project)["profile"]["active"]
        local_profile = manager._read_yaml(manager.paths.local)["profile"]["active"]

        assert user_profile == "user-profile"
        assert project_profile == "project-profile"
        assert local_profile == "local-profile"

    # ===== Error Handling Tests =====

    def test_yaml_format_preserved(self, manager):
        """Test that YAML format is preserved."""
        manager.set_active_profile("test", scope=Scope.LOCAL)
        manager.add_source_override("module1", "source1", scope=Scope.LOCAL)

        # Read raw file
        content = manager.paths.local.read_text()

        # Should be valid YAML
        assert "profile:" in content
        assert "active: test" in content
        assert "sources:" in content
        assert "module1: source1" in content
