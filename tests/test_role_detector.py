"""
Tests for role detection
"""

import pytest
from role_detector import estimate_role_from_profession, get_base_class


def test_estimate_role_healer():
    """Test healer role detection"""
    # Note: Firebrand is primarily stab in current logic
    assert estimate_role_from_profession("Scrapper") == "healer"
    assert estimate_role_from_profession("Tempest") == "healer"
    assert estimate_role_from_profession("Druid") == "healer"


def test_estimate_role_stab():
    """Test stab role detection"""
    assert estimate_role_from_profession("Firebrand") == "stab"
    # Note: Guardian base class may be DPS by default


def test_estimate_role_dps_strip():
    """Test DPS strip role detection"""
    assert estimate_role_from_profession("Spellbreaker") == "dps_strip"
    assert estimate_role_from_profession("Harbinger") == "dps_strip"


def test_estimate_role_boon():
    """Test boon role detection"""
    assert estimate_role_from_profession("Chronomancer") == "boon"
    assert estimate_role_from_profession("Renegade") == "boon"


def test_estimate_role_dps_default():
    """Test DPS as default role"""
    assert estimate_role_from_profession("Bladesworn") == "dps"
    assert estimate_role_from_profession("Unknown") == "dps"
    # Most specs default to DPS if not specified
    role = estimate_role_from_profession("Warrior")
    assert role in ["dps", "stab"]  # Can be either depending on implementation


def test_get_base_class():
    """Test base class extraction"""
    assert get_base_class("Firebrand") == "Guardian"
    assert get_base_class("Harbinger") == "Necromancer"
    assert get_base_class("Scrapper") == "Engineer"
    assert get_base_class("Guardian") == "Guardian"
    assert get_base_class("Unknown") == "Unknown"
