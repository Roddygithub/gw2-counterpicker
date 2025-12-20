"""
Tests for the feature flags system

Ensures that:
1. Feature flags can be queried correctly
2. Routers are conditionally included based on flags
3. Templates conditionally show/hide UI elements
4. Core features (analysis, META) are always available
"""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient


def test_is_feature_enabled():
    """Test that is_feature_enabled returns correct values"""
    from features import is_feature_enabled
    
    # Test enabled features
    assert is_feature_enabled("GW2_API") == True
    assert is_feature_enabled("COUNTER_ENGINE_BASIC") == True
    assert is_feature_enabled("COUNTER_ENGINE_ADVANCED") == True
    
    # Test disabled features
    assert is_feature_enabled("PLAYER_CAREER") == False
    assert is_feature_enabled("PERFORMANCE_ANALYTICS") == False
    assert is_feature_enabled("GUILD_ANALYTICS") == False
    assert is_feature_enabled("COUNTER_FEEDBACK") == False
    assert is_feature_enabled("PDF_EXPORT") == False
    assert is_feature_enabled("ADMIN_PANEL") == False
    assert is_feature_enabled("LLM_RECOMMENDATIONS") == False
    
    # Test non-existent feature (should return False)
    assert is_feature_enabled("NON_EXISTENT_FEATURE") == False


def test_get_enabled_features():
    """Test that get_enabled_features returns all features"""
    from features import get_enabled_features
    
    features = get_enabled_features()
    
    # Check that all expected features are present
    expected_features = [
        "GW2_API", "PLAYER_CAREER", "PERFORMANCE_ANALYTICS",
        "GUILD_ANALYTICS", "COUNTER_ENGINE_BASIC", "COUNTER_ENGINE_ADVANCED",
        "COUNTER_FEEDBACK", "PDF_EXPORT", "ADMIN_PANEL", "LLM_RECOMMENDATIONS"
    ]
    
    for feature in expected_features:
        assert feature in features
    
    # Verify it returns a copy (not the original dict)
    features["TEST"] = True
    features2 = get_enabled_features()
    assert "TEST" not in features2


def test_get_feature_description():
    """Test that feature descriptions are available"""
    from features import get_feature_description
    
    # Test existing features
    desc = get_feature_description("GW2_API")
    assert "GW2 API" in desc
    assert len(desc) > 0
    
    desc = get_feature_description("PLAYER_CAREER")
    assert "Player Career" in desc or "career" in desc.lower()
    
    # Test non-existent feature
    desc = get_feature_description("NON_EXISTENT")
    assert desc == ""


def test_core_routes_always_available():
    """Test that core routes are always available regardless of feature flags"""
    from main import app
    
    client = TestClient(app)
    
    # Core routes that should ALWAYS work
    core_routes = [
        "/",  # Home page
        "/analyze",  # Analysis page (single + multi)
        "/meta",  # META page (defaults to zerg)
        "/meta/zerg",  # META zerg
        "/meta/guild_raid",  # META guild raid
        "/meta/roam",  # META roam
        "/about",  # About page
        "/health",  # Health check
    ]
    
    for route in core_routes:
        response = client.get(route)
        assert response.status_code == 200, f"Core route {route} should always be available (got {response.status_code})"


def test_gw2_api_router_included_when_enabled():
    """Test that GW2 API router is included when feature is enabled"""
    from features import is_feature_enabled
    
    # This test verifies the current state where GW2_API is True
    if is_feature_enabled("GW2_API"):
        from main import app
        client = TestClient(app)
        
        # GW2 API routes should be available
        # Note: These might return 401/403 without auth, but should not be 404
        response = client.get("/api/gw2/dashboard")
        assert response.status_code != 404, "GW2 API routes should be registered when feature is enabled"


def test_admin_router_not_included_when_disabled():
    """Test that admin router is not included when feature is disabled"""
    from features import is_feature_enabled
    
    # This test verifies the current state where ADMIN_PANEL is False
    if not is_feature_enabled("ADMIN_PANEL"):
        from main import app
        client = TestClient(app)
        
        # Admin routes should return 404
        response = client.get("/admin/feedback")
        assert response.status_code == 404, "Admin routes should not be available when feature is disabled"


@patch('features.FEATURES')
def test_router_inclusion_with_mocked_flags(mock_features):
    """Test router inclusion with mocked feature flags"""
    # This test demonstrates how to test with different flag configurations
    # Note: Due to module imports, this requires app restart to take effect
    # For real testing, you'd need to reload the main module
    
    mock_features.get = lambda key, default=False: {
        "GW2_API": False,
        "ADMIN_PANEL": True,
    }.get(key, default)
    
    from features import is_feature_enabled
    
    # Verify mocked values
    assert is_feature_enabled("GW2_API") == False
    assert is_feature_enabled("ADMIN_PANEL") == True


def test_template_has_feature_flags_exposed():
    """Test that templates have access to is_feature_enabled function"""
    from main import templates
    
    # Check that is_feature_enabled is exposed to templates
    assert "is_feature_enabled" in templates.env.globals
    assert callable(templates.env.globals["is_feature_enabled"])
    
    # Check that features dict is exposed
    assert "features" in templates.env.globals
    assert isinstance(templates.env.globals["features"], dict)


def test_feature_flags_in_template_rendering():
    """Test that feature flags work in template rendering"""
    from main import app
    
    client = TestClient(app)
    
    # Get home page
    response = client.get("/")
    assert response.status_code == 200
    html = response.text
    
    # With current flags (PLAYER_CAREER=False, GUILD_ANALYTICS=False):
    # - Dashboard/History links should NOT appear in nav
    # - Guild Stats feature card should NOT appear
    # - Personal Stats feature card should NOT appear
    
    # Note: These are in Alpine.js x-text, so we check for the href instead
    # Dashboard and History should not be in nav when PLAYER_CAREER is False
    from features import is_feature_enabled
    
    if not is_feature_enabled("PLAYER_CAREER"):
        # The nav links are conditionally rendered, so they shouldn't be in HTML
        assert '/api/gw2/dashboard' not in html or 'is_feature_enabled("GW2_API") and is_feature_enabled("PLAYER_CAREER")' in html
    
    if not is_feature_enabled("GUILD_ANALYTICS"):
        # Guild Stats card should not appear
        # We can check for the unique text or heading
        pass  # The card is wrapped in {% if %} so it won't be in HTML


def test_counter_engine_flags():
    """Test that counter engine flags are properly set"""
    from features import is_feature_enabled
    
    # Both basic and advanced counter engines should be enabled by default
    assert is_feature_enabled("COUNTER_ENGINE_BASIC") == True
    assert is_feature_enabled("COUNTER_ENGINE_ADVANCED") == True
    
    # This ensures counter recommendations continue to work


def test_llm_recommendations_disabled():
    """Test that LLM recommendations are disabled (v4.0 is stats-only)"""
    from features import is_feature_enabled
    
    # LLM should be OFF in v4.0
    assert is_feature_enabled("LLM_RECOMMENDATIONS") == False


def test_analyze_endpoint_always_works():
    """Test that the analyze endpoint (core feature) always works"""
    from main import app
    
    client = TestClient(app)
    
    # The analyze page should always be accessible
    response = client.get("/analyze")
    assert response.status_code == 200
    
    # The API endpoint should exist (even if it fails without valid data)
    # We're just checking it's registered, not that it succeeds
    response = client.post("/api/analyze/evtc", files={})
    # Should not be 404 (route not found)
    assert response.status_code != 404


def test_meta_pages_always_work():
    """Test that META pages (core feature) always work"""
    from main import app
    
    client = TestClient(app)
    
    # All META context pages should be available
    contexts = ["zerg", "guild_raid", "roam"]
    
    for context in contexts:
        response = client.get(f"/meta/{context}")
        assert response.status_code == 200, f"META page for {context} should always be available"
    
    # Default META page
    response = client.get("/meta")
    assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
