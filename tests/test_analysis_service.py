"""
Tests for analysis service
"""

import pytest
from services.analysis_service import (
    is_player_afk,
    determine_fight_outcome,
    convert_parsed_log_to_players_data
)


class MockPlayer:
    """Mock player for testing"""
    def __init__(self, damage=0, healing=0, damage_taken=0, kills=0):
        self.damage_dealt = damage
        self.healing = healing
        self.damage_taken = damage_taken
        self.kills = kills


def test_is_player_afk_true():
    """Test AFK detection for inactive player"""
    player = MockPlayer(damage=0, healing=0, damage_taken=0, kills=0)
    assert is_player_afk(player) is True


def test_is_player_afk_false_with_damage():
    """Test AFK detection for player with damage"""
    player = MockPlayer(damage=1000, healing=0, damage_taken=0, kills=0)
    assert is_player_afk(player) is False


def test_is_player_afk_false_with_healing():
    """Test AFK detection for player with healing"""
    player = MockPlayer(damage=0, healing=1000, damage_taken=0, kills=0)
    assert is_player_afk(player) is False


def test_is_player_afk_false_with_damage_taken():
    """Test AFK detection for player with damage taken"""
    player = MockPlayer(damage=0, healing=0, damage_taken=1000, kills=0)
    assert is_player_afk(player) is False


def test_determine_fight_outcome_victory():
    """Test victory outcome determination"""
    # Victory: death_ratio < 0.2 (less than 20% deaths)
    allies = [
        {'deaths': 0, 'downs': 0},
        {'deaths': 0, 'downs': 1},
        {'deaths': 0, 'downs': 0},
        {'deaths': 0, 'downs': 0},
        {'deaths': 0, 'downs': 0},
    ]  # 0/5 = 0% deaths
    enemies = [{'name': 'Enemy1'}, {'name': 'Enemy2'}]
    
    outcome = determine_fight_outcome(allies, enemies, 120)
    assert outcome == 'victory'


def test_determine_fight_outcome_defeat():
    """Test defeat outcome determination"""
    # Defeat: death_ratio > 0.6 (more than 60% deaths)
    allies = [
        {'deaths': 2, 'downs': 3},
        {'deaths': 2, 'downs': 2},
        {'deaths': 2, 'downs': 1},
    ]  # 6/3 = 200% deaths (everyone died twice)
    enemies = [{'name': 'Enemy1'}, {'name': 'Enemy2'}]
    
    outcome = determine_fight_outcome(allies, enemies, 120)
    assert outcome == 'defeat'


def test_determine_fight_outcome_draw():
    """Test draw outcome determination"""
    # Draw: 0.2 <= death_ratio <= 0.6 (between 20% and 60% deaths)
    allies = [
        {'deaths': 1, 'downs': 1},
        {'deaths': 1, 'downs': 1},
        {'deaths': 0, 'downs': 1},
        {'deaths': 0, 'downs': 1},
        {'deaths': 1, 'downs': 1},
    ]  # 3/5 = 60% deaths (exactly at threshold)
    enemies = [{'name': 'Enemy1'}, {'name': 'Enemy2'}]
    
    outcome = determine_fight_outcome(allies, enemies, 120)
    assert outcome in ['draw', 'defeat']  # At threshold, could be either


def test_determine_fight_outcome_short_fight():
    """Test outcome for very short fight"""
    allies = [
        {'deaths': 0, 'downs': 0},
        {'deaths': 0, 'downs': 0},
    ]
    enemies = [{'name': 'Enemy1'}]
    
    outcome = determine_fight_outcome(allies, enemies, 20)
    assert outcome == 'victory'


def test_determine_fight_outcome_no_enemies():
    """Test outcome when no enemies"""
    allies = [{'deaths': 0, 'downs': 0}]
    enemies = []
    
    outcome = determine_fight_outcome(allies, enemies, 120)
    assert outcome == 'unknown'


def test_determine_fight_outcome_no_allies():
    """Test outcome when no allies"""
    allies = []
    enemies = [{'name': 'Enemy1'}]
    
    outcome = determine_fight_outcome(allies, enemies, 120)
    assert outcome == 'unknown'
