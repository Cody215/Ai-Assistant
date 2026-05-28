"""
Tests for router.py — tool routing logic (local vs cloud).

Validates that the Router class correctly classifies tools as local, cloud, or unknown.
"""

from __future__ import annotations

import pytest
from router import Router


class TestRouterInitialization:
    """Test Router initialization and class structure."""

    def test_router_initializes(self):
        """Router should initialize without errors."""
        router = Router()
        assert router is not None

    def test_router_has_local_tools_set(self):
        """Router should have LOCAL_TOOLS set defined."""
        router = Router()
        assert hasattr(router, "LOCAL_TOOLS")
        assert isinstance(router.LOCAL_TOOLS, set)
        assert len(router.LOCAL_TOOLS) > 0

    def test_router_has_cloud_tools_set(self):
        """Router should have CLOUD_TOOLS set defined."""
        router = Router()
        assert hasattr(router, "CLOUD_TOOLS")
        assert isinstance(router.CLOUD_TOOLS, set)
        assert len(router.CLOUD_TOOLS) > 0

    def test_local_and_cloud_tools_dont_overlap(self):
        """LOCAL_TOOLS and CLOUD_TOOLS should not overlap."""
        router = Router()
        overlap = router.LOCAL_TOOLS & router.CLOUD_TOOLS
        assert len(overlap) == 0, f"Tools should not be in both sets: {overlap}"


class TestLocalToolDetection:
    """Test detection of local tools."""

    def test_get_time_is_local(self):
        """get_time should be detected as local."""
        router = Router()
        assert router.is_local("get_time") is True

    def test_get_date_is_local(self):
        """get_date should be detected as local."""
        router = Router()
        assert router.is_local("get_date") is True

    def test_get_battery_is_local(self):
        """get_battery should be detected as local."""
        router = Router()
        assert router.is_local("get_battery") is True

    def test_get_volume_is_local(self):
        """get_volume should be detected as local."""
        router = Router()
        assert router.is_local("get_volume") is True

    def test_open_app_is_local(self):
        """open_app should be detected as local."""
        router = Router()
        assert router.is_local("open_app") is True

    def test_capture_screen_is_local(self):
        """capture_screen should be detected as local."""
        router = Router()
        assert router.is_local("capture_screen") is True

    def test_create_file_is_local(self):
        """create_file should be detected as local."""
        router = Router()
        assert router.is_local("create_file") is True

    def test_all_defined_local_tools_detected(self):
        """All LOCAL_TOOLS should return True for is_local()."""
        router = Router()
        for tool in router.LOCAL_TOOLS:
            assert router.is_local(tool) is True, f"{tool} should be local"


class TestCloudToolDetection:
    """Test detection of cloud tools."""

    def test_web_search_is_cloud(self):
        """web_search should be detected as cloud."""
        router = Router()
        assert router.is_cloud("web_search") is True

    def test_get_weather_is_cloud(self):
        """get_weather should be detected as cloud."""
        router = Router()
        assert router.is_cloud("get_weather") is True

    def test_all_defined_cloud_tools_detected(self):
        """All CLOUD_TOOLS should return True for is_cloud()."""
        router = Router()
        for tool in router.CLOUD_TOOLS:
            assert router.is_cloud(tool) is True, f"{tool} should be cloud"


class TestToolClassification:
    """Test the classify() method."""

    def test_classify_local_tool(self):
        """classify() should return 'local' for local tools."""
        router = Router()
        assert router.classify("get_time") == "local"
        assert router.classify("open_app") == "local"

    def test_classify_cloud_tool(self):
        """classify() should return 'cloud' for cloud tools."""
        router = Router()
        assert router.classify("web_search") == "cloud"
        assert router.classify("get_weather") == "cloud"

    def test_classify_unknown_tool(self):
        """classify() should return 'unknown' for unknown tools."""
        router = Router()
        assert router.classify("nonexistent_tool") == "unknown"
        assert router.classify("fake_function") == "unknown"

    def test_classify_empty_string(self):
        """classify() should return 'unknown' for empty string."""
        router = Router()
        assert router.classify("") == "unknown"


class TestRoutingDeterminism:
    """Test that routing is deterministic (same tool always routes the same way)."""

    def test_repeated_local_routing(self):
        """Repeated calls for the same local tool should always return True."""
        router = Router()
        for _ in range(10):
            assert router.is_local("get_time") is True

    def test_repeated_cloud_routing(self):
        """Repeated calls for the same cloud tool should always return True."""
        router = Router()
        for _ in range(10):
            assert router.is_cloud("web_search") is True

    def test_repeated_classify(self):
        """Repeated classify() calls should return the same result."""
        router = Router()
        results = [router.classify("get_time") for _ in range(5)]
        assert all(r == "local" for r in results)

    def test_multiple_routers_same_routing(self):
        """Different Router instances should route identically."""
        router1 = Router()
        router2 = Router()
        
        test_tools = ["get_time", "web_search", "open_app", "get_weather"]
        for tool in test_tools:
            assert router1.is_local(tool) == router2.is_local(tool)
            assert router1.is_cloud(tool) == router2.is_cloud(tool)
            assert router1.classify(tool) == router2.classify(tool)


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_tool_name_case_sensitive(self):
        """Tool names should be case-sensitive (get_time ≠ GET_TIME)."""
        router = Router()
        assert router.is_local("get_time") is True
        assert router.is_local("GET_TIME") is False
        assert router.classify("GET_TIME") == "unknown"

    def test_tool_with_whitespace(self):
        """Tool names with whitespace should be treated as unknown."""
        router = Router()
        assert router.classify("get_time ") == "unknown"
        assert router.classify(" get_time") == "unknown"
        assert router.classify("get time") == "unknown"

    def test_tool_with_special_characters(self):
        """Tool names with special characters should be treated as unknown."""
        router = Router()
        assert router.classify("get_time!") == "unknown"
        assert router.classify("get-time") == "unknown"
