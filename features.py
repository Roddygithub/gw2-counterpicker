"""
Feature Flags System for GW2 CounterPicker

This module defines which optional features are enabled/disabled.
Core features (log analysis, META by context) are ALWAYS ON and not controlled by flags.

Feature flags control:
- GW2 API integration (account connection, dashboard, history)
- Player career tracking
- Performance analytics
- Guild analytics
- Counter engine (basic & advanced)
- Counter feedback system
- PDF export
- Admin panel
- LLM recommendations (future feature)
"""

from typing import Dict

# Feature flags dictionary
# True = enabled, False = disabled
FEATURES: Dict[str, bool] = {
    # GW2 API Integration - Account connection and API features
    "GW2_API": True,
    
    # Player Career - Personal WvW career tracking and statistics
    "PLAYER_CAREER": False,
    
    # Performance Analytics - Advanced performance comparison and metrics
    "PERFORMANCE_ANALYTICS": False,
    
    # Guild Analytics - Guild-level statistics and analysis
    "GUILD_ANALYTICS": False,
    
    # Counter Engine Basic - Basic counter recommendations
    "COUNTER_ENGINE_BASIC": True,
    
    # Counter Engine Advanced - Advanced counter recommendations with detailed analysis
    "COUNTER_ENGINE_ADVANCED": True,
    
    # Counter Feedback - User feedback on counter recommendations
    "COUNTER_FEEDBACK": False,
    
    # PDF Export - Export analysis results to PDF
    "PDF_EXPORT": False,
    
    # Admin Panel - Administrative interface for feedback and settings
    "ADMIN_PANEL": False,
    
    # LLM Recommendations - AI-powered recommendations (future feature, keep OFF)
    "LLM_RECOMMENDATIONS": False,
}


def is_feature_enabled(name: str) -> bool:
    """
    Check if a feature is enabled.
    
    Args:
        name: Feature flag name (e.g., "GW2_API", "PLAYER_CAREER")
        
    Returns:
        True if feature is enabled, False otherwise
        
    Example:
        >>> is_feature_enabled("GW2_API")
        True
        >>> is_feature_enabled("LLM_RECOMMENDATIONS")
        False
    """
    return FEATURES.get(name, False)


def get_enabled_features() -> Dict[str, bool]:
    """
    Get all feature flags and their status.
    
    Returns:
        Dictionary of all features and their enabled/disabled status
    """
    return FEATURES.copy()


def get_feature_description(name: str) -> str:
    """
    Get a human-readable description of a feature.
    
    Args:
        name: Feature flag name
        
    Returns:
        Description string or empty string if not found
    """
    descriptions = {
        "GW2_API": "GW2 API Integration - Account connection and API features",
        "PLAYER_CAREER": "Player Career - Personal WvW career tracking and statistics",
        "PERFORMANCE_ANALYTICS": "Performance Analytics - Advanced performance comparison and metrics",
        "GUILD_ANALYTICS": "Guild Analytics - Guild-level statistics and analysis",
        "COUNTER_ENGINE_BASIC": "Counter Engine Basic - Basic counter recommendations",
        "COUNTER_ENGINE_ADVANCED": "Counter Engine Advanced - Advanced counter recommendations",
        "COUNTER_FEEDBACK": "Counter Feedback - User feedback on counter recommendations",
        "PDF_EXPORT": "PDF Export - Export analysis results to PDF",
        "ADMIN_PANEL": "Admin Panel - Administrative interface",
        "LLM_RECOMMENDATIONS": "LLM Recommendations - AI-powered recommendations (future)",
    }
    return descriptions.get(name, "")
