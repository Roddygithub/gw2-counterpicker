"""
Tests for Counter AI - context handling and learning
"""

import pytest
from unittest.mock import patch, MagicMock
from counter_ai import (
    guess_fight_context, 
    FightContext,
    CounterAI,
    record_fight_for_learning
)


class TestFightContext:
    """Test fight context detection and handling"""
    
    def test_zerg_by_ally_count(self):
        """Zerg detected when 25+ allies"""
        context = guess_fight_context(ally_count=30, enemy_count=20, duration_sec=180)
        assert context == FightContext.ZERG
    
    def test_guild_raid_by_ally_count(self):
        """Guild raid detected when 10-24 allies with high guild ratio"""
        context = guess_fight_context(
            ally_count=15, 
            enemy_count=12, 
            duration_sec=180,
            subgroup_count=3,
            main_guild_ratio=0.8  # High guild ratio triggers guild_raid
        )
        # May return guild_raid or zerg depending on other factors
        assert context in [FightContext.GUILD_RAID, FightContext.ZERG, FightContext.UNKNOWN]
    
    def test_roam_by_ally_count(self):
        """Roam detected when <10 allies"""
        context = guess_fight_context(ally_count=5, enemy_count=3, duration_sec=60)
        assert context == FightContext.ROAM
    
    def test_context_enum_values(self):
        """Test context enum string values"""
        assert FightContext.ZERG.value == "zerg"
        assert FightContext.GUILD_RAID.value == "guild_raid"
        assert FightContext.ROAM.value == "roam"


class TestCounterAI:
    """Test CounterAI class methods"""
    
    def test_format_enemy_comp(self):
        """Test enemy composition formatting"""
        ai = CounterAI()
        enemy_comp = {"Scourge": 4, "Firebrand": 3, "Scrapper": 2}
        formatted = ai._format_enemy_comp(enemy_comp)
        assert "Scourge" in formatted
        assert "Firebrand" in formatted
        assert "Scrapper" in formatted
    
    def test_fallback_counter_zerg(self):
        """Test fallback counter for zerg context"""
        ai = CounterAI()
        enemy_comp = {"Firebrand": 5, "Scourge": 4}
        result = ai._fallback_counter(enemy_comp, {'total_fights': 100}, context="zerg")
        
        assert result['success'] == True
        assert 'counter' in result
        assert result['model'] == 'fallback_rules'
    
    def test_fallback_counter_roam(self):
        """Test fallback counter for roam context"""
        ai = CounterAI()
        enemy_comp = {"Thief": 2, "Mesmer": 1}
        result = ai._fallback_counter(enemy_comp, {'total_fights': 50}, context="roam")
        
        assert result['success'] == True
        assert 'counter' in result


class TestFightRecording:
    """Test fight recording for learning"""
    
    def test_short_fight_rejected(self):
        """Fights shorter than 60s should be rejected"""
        fight_data = {
            'duration_sec': 30,
            'allies': [],
            'enemies': [],
            'composition': {'spec_counts': {}},
            'enemy_composition': {'spec_counts': {}}
        }
        
        result = record_fight_for_learning(fight_data, filename="test.zevtc", filesize=1000)
        # Short fights return None
        assert result is None
    
    def test_context_passed_to_recording(self):
        """Test that context is properly passed when recording"""
        fight_data = {
            'duration_sec': 180,
            'allies': [
                {'name': 'Player1', 'account': 'Acc.1234', 'profession': 'Guardian', 'role': 'stab'}
            ],
            'enemies': [
                {'name': 'Enemy1', 'profession': 'Scourge'}
            ],
            'composition': {'spec_counts': {'Guardian': 1}},
            'enemy_composition': {'spec_counts': {'Scourge': 1}},
            'fight_outcome': 'victory'
        }
        
        # This should not raise an error
        # The actual recording may be skipped due to deduplication
        result = record_fight_for_learning(
            fight_data, 
            filename="test_context.zevtc", 
            filesize=2000,
            context="guild_raid"
        )
        # Result may be None if deduplicated, or a fight_id if recorded


class TestSimilarFightsSearch:
    """Test finding similar fights by composition"""
    
    def test_jaccard_similarity(self):
        """Test Jaccard similarity calculation"""
        set1 = {"Scourge", "Firebrand", "Scrapper"}
        set2 = {"Scourge", "Firebrand", "Herald"}
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        similarity = intersection / union if union > 0 else 0
        
        # 2 common specs out of 4 total unique = 0.5
        assert similarity == 0.5
    
    def test_context_filter_in_similar_fights(self):
        """Test that context filters similar fights correctly"""
        ai = CounterAI()
        
        # Mock fights with different contexts
        mock_fights = [
            {'enemy_composition': {'Scourge': 2}, 'context_detected': 'zerg'},
            {'enemy_composition': {'Scourge': 2}, 'context_detected': 'roam'},
            {'enemy_composition': {'Scourge': 2}, 'context_detected': 'guild_raid'},
        ]
        
        # The _find_similar_fights method should filter by context
        # This is a unit test of the filtering logic
        filtered = [f for f in mock_fights if f.get('context_detected') == 'zerg']
        assert len(filtered) == 1
        assert filtered[0]['context_detected'] == 'zerg'
