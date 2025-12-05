"""Integration tests for ConfigManager."""

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from amplifier_config import ConfigManager
from amplifier_config import ConfigPaths
from amplifier_config import Scope


class TestConfigIntegration:
    """Integration tests for realistic configuration scenarios."""

    @pytest.fixture
    def temp_paths(self):
        """Create temporary paths for testing."""
        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            paths = ConfigPaths(
                user=tmpdir_path / "user" / ".amplifier" / "settings.yaml",
                project=tmpdir_path / "project" / ".amplifier" / "settings.yaml",
                local=tmpdir_path / "project" / ".amplifier" / "settings.local.yaml",
            )
            yield paths

    @pytest.fixture
    def manager(self, temp_paths):
        """Create ConfigManager with temp paths."""
        return ConfigManager(temp_paths)

    def test_realistic_workflow_profile_switching(self, manager):
        """Test realistic workflow of switching profiles."""
        # 1. User sets global default profile
        manager.set_active_profile("foundation", scope=Scope.USER)
        assert manager.get_active_profile() == "foundation"

        # 2. Project sets its default
        manager.set_project_default("dev")
        assert manager.get_project_default() == "dev"

        # 3. Developer overrides locally for testing
        manager.set_active_profile("test", scope=Scope.LOCAL)
        assert manager.get_active_profile() == "test"  # Local wins

        # 4. Developer clears local override, project default applies
        manager.clear_active_profile(scope=Scope.LOCAL)
        assert manager.get_active_profile() == "foundation"  # User still set

    def test_realistic_workflow_module_sources(self, manager):
        """Test realistic workflow of managing module sources."""
        # 1. User sets global source overrides for faster local development
        manager.add_source_override(
            "provider-anthropic", "file:///home/user/dev/amplifier-module-provider-anthropic", scope=Scope.USER
        )

        # 2. Project pins a specific version
        manager.add_source_override(
            "provider-anthropic",
            "git+https://github.com/microsoft/amplifier-module-provider-anthropic@v1.5.0",
            scope=Scope.PROJECT,
        )

        # 3. Developer overrides locally to test unreleased version
        manager.add_source_override(
            "provider-anthropic",
            "git+https://github.com/microsoft/amplifier-module-provider-anthropic@main",
            scope=Scope.LOCAL,
        )

        sources = manager.get_module_sources()
        # Local override wins
        assert sources["provider-anthropic"].endswith("@main")

        # 4. Developer removes local override
        manager.remove_source_override("provider-anthropic", scope=Scope.LOCAL)
        sources = manager.get_module_sources()
        # Project version now applies
        assert sources["provider-anthropic"].endswith("@v1.5.0")

    def test_realistic_workflow_team_collaboration(self, manager):
        """Test realistic workflow of team collaboration."""
        # 1. Team lead sets project defaults (committed to git)
        manager.set_project_default("dev")
        manager.add_source_override(
            "provider-anthropic",
            "git+https://github.com/microsoft/amplifier-module-provider-anthropic@v1.0",
            scope=Scope.PROJECT,
        )

        # 2. Developer A clones repo and sets local preferences (not committed)
        manager.set_active_profile("dev-with-extended-thinking", scope=Scope.LOCAL)
        manager.add_source_override("tool-custom", "file:///home/developerA/custom-tools", scope=Scope.LOCAL)

        # Verify settings
        assert manager.get_active_profile() == "dev-with-extended-thinking"
        sources = manager.get_module_sources()
        assert "tool-custom" in sources
        assert "provider-anthropic" in sources

        # 3. Developer B clones same repo (different machine)
        # Simulate by clearing local settings
        manager.clear_active_profile(scope=Scope.LOCAL)
        manager.remove_source_override("tool-custom", scope=Scope.LOCAL)

        # Developer B gets project defaults
        # Note: Active profile falls back to user or None if not set in project
        project_default = manager.get_project_default()
        assert project_default == "dev"

        # Project sources still apply
        sources = manager.get_module_sources()
        assert "provider-anthropic" in sources
        assert "tool-custom" not in sources  # Developer A's local override gone

    def test_three_scope_resolution_comprehensive(self, manager):
        """Test comprehensive three-scope resolution scenarios."""
        # Set up complex settings across all scopes
        manager.add_source_override("module-a", "user-source-a", scope=Scope.USER)
        manager.add_source_override("module-b", "user-source-b", scope=Scope.USER)

        manager.add_source_override("module-b", "project-source-b", scope=Scope.PROJECT)
        manager.add_source_override("module-c", "project-source-c", scope=Scope.PROJECT)

        manager.add_source_override("module-c", "local-source-c", scope=Scope.LOCAL)
        manager.add_source_override("module-d", "local-source-d", scope=Scope.LOCAL)

        # Get merged sources
        sources = manager.get_module_sources()

        # Verify correct precedence
        assert sources["module-a"] == "user-source-a"  # Only in user
        assert sources["module-b"] == "project-source-b"  # Project overrides user
        assert sources["module-c"] == "local-source-c"  # Local overrides project
        assert sources["module-d"] == "local-source-d"  # Only in local

    def test_get_merged_settings_realistic_structure(self, manager):
        """Test get_merged_settings with realistic nested structure."""
        # User sets global preferences
        manager.set_active_profile("foundation", scope=Scope.USER)
        manager.add_source_override("provider-anthropic", "user-anthropic", scope=Scope.USER)

        # Project sets team defaults
        manager.set_project_default("dev")
        manager.add_source_override("provider-openai", "project-openai", scope=Scope.PROJECT)

        # Local overrides for development
        manager.set_active_profile("test", scope=Scope.LOCAL)
        manager.add_source_override("tool-custom", "local-custom", scope=Scope.LOCAL)

        # Get complete merged settings
        merged = manager.get_merged_settings()

        # Verify structure
        assert "profile" in merged
        assert merged["profile"]["active"] == "test"  # Local wins
        assert merged["profile"]["default"] == "dev"  # From project

        assert "sources" in merged
        assert merged["sources"]["provider-anthropic"] == "user-anthropic"
        assert merged["sources"]["provider-openai"] == "project-openai"
        assert merged["sources"]["tool-custom"] == "local-custom"

    def test_clean_state_after_clearing_all(self, manager):
        """Test that clearing all settings returns to clean state."""
        # Set up settings in all scopes
        manager.set_active_profile("user-profile", scope=Scope.USER)
        manager.set_project_default("project-default")
        manager.set_active_profile("local-profile", scope=Scope.LOCAL)
        manager.add_source_override("module", "source", scope=Scope.USER)

        # Clear everything
        manager.clear_active_profile(scope=Scope.USER)
        manager.clear_project_default()
        manager.clear_active_profile(scope=Scope.LOCAL)
        manager.remove_source_override("module", scope=Scope.USER)

        # Verify clean state
        assert manager.get_active_profile() is None
        assert manager.get_project_default() is None
        assert manager.get_module_sources() == {}
        assert manager.get_merged_settings() == {}

    def test_paths_injection_different_locations(self):
        """Test that different path configurations work correctly."""
        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Simulate different application with different path policy
            custom_paths = ConfigPaths(
                user=tmpdir_path / "custom" / "user-config.yaml",
                project=tmpdir_path / "custom" / "project.yaml",
                local=tmpdir_path / "custom" / "local-overrides.yaml",
            )

            manager = ConfigManager(custom_paths)

            # Operations should work with custom paths
            manager.set_active_profile("test")
            assert manager.get_active_profile() == "test"

            # Verify files created at custom locations
            assert custom_paths.local is not None  # We explicitly set it above
            assert custom_paths.local.exists()
            assert custom_paths.local.name == "local-overrides.yaml"
