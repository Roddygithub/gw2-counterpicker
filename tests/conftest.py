"""
Pytest configuration and fixtures for GW2 CounterPicker tests
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

@pytest.fixture
def sample_evtc_data():
    """Sample EVTC data for testing"""
    return b"EVTC" + b"\x00" * 100  # Minimal valid EVTC header

@pytest.fixture
def sample_player_data():
    """Sample player data for testing"""
    return {
        'name': 'Test Player',
        'account': 'Test.1234',
        'profession': 'Firebrand',
        'group': 1,
        'role': 'healer',
        'damage': 1000000,
        'dps': 10000,
        'deaths': 0,
        'kills': 5
    }

@pytest.fixture
def sample_fight_data():
    """Sample fight data for testing"""
    return {
        'allies': [
            {'name': 'Player1', 'profession': 'Firebrand', 'role': 'healer', 'damage': 1000000},
            {'name': 'Player2', 'profession': 'Scrapper', 'role': 'healer', 'damage': 900000},
            {'name': 'Player3', 'profession': 'Spellbreaker', 'role': 'dps_strip', 'damage': 2000000},
        ],
        'enemies': [
            {'name': 'Enemy1', 'profession': 'Harbinger', 'role': 'dps'},
            {'name': 'Enemy2', 'profession': 'Willbender', 'role': 'dps'},
        ],
        'fight_name': 'Test Fight',
        'duration_sec': 120,
        'fight_outcome': 'victory',
        'composition': {
            'spec_counts': {'Firebrand': 1, 'Scrapper': 1, 'Spellbreaker': 1},
            'role_counts': {'healer': 2, 'dps_strip': 1, 'dps': 0, 'stab': 0, 'boon': 0}
        },
        'enemy_composition': {
            'spec_counts': {'Harbinger': 1, 'Willbender': 1},
            'role_counts': {'dps': 2, 'healer': 0, 'dps_strip': 0, 'stab': 0, 'boon': 0}
        }
    }
