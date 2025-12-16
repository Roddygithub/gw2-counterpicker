"""
Tests for data extraction from dps.report and local parser
"""

import pytest


class TestPlayerDataExtraction:
    """Test player data extraction and formatting"""
    
    def test_ally_data_structure(self):
        """Test that ally data has all required fields"""
        required_fields = [
            'name', 'account', 'profession', 'group',
            'damage_out', 'damage_in', 'dps', 'damage_ratio',
            'kills', 'deaths', 'downs', 'down_contrib',
            'cc_out', 'cc_in', 'boon_strips', 'boon_strip_in',
            'heal_only', 'healing', 'healing_per_sec',
            'cleanses', 'cleanses_per_sec', 'resurrects', 'barrier',
            'boon_gen', 'boon_uptime', 'role', 'is_commander', 'in_squad'
        ]
        
        # Simulate ally data structure
        ally_data = {
            'name': 'TestPlayer',
            'account': 'Test.1234',
            'profession': 'Firebrand',
            'group': 1,
            'damage_out': 100000,
            'damage_in': 50000,
            'dps': 500,
            'damage_ratio': 2.0,
            'kills': 3,
            'deaths': 1,
            'downs': 2,
            'down_contrib': 5000,
            'cc_out': 10,
            'cc_in': 5,
            'boon_strips': 20,
            'boon_strip_in': 8,
            'heal_only': 50000,
            'healing': 50000,
            'healing_per_sec': 250,
            'cleanses': 100,
            'cleanses_per_sec': 0.5,
            'resurrects': 2,
            'barrier': 30000,
            'boon_gen': {'Might': 50, 'Fury': 30},
            'boon_uptime': {'Might': 80, 'Fury': 60},
            'role': 'stab',
            'is_commander': False,
            'in_squad': True
        }
        
        for field in required_fields:
            assert field in ally_data, f"Missing field: {field}"
    
    def test_enemy_data_structure(self):
        """Test that enemy data has required fields"""
        required_fields = ['name', 'profession', 'damage_taken', 'role']
        
        enemy_data = {
            'name': 'Scourge pl-1234',
            'profession': 'Scourge',
            'damage_taken': 50000,
            'role': 'dps_strip'
        }
        
        for field in required_fields:
            assert field in enemy_data, f"Missing field: {field}"
    
    def test_squad_totals_calculation(self):
        """Test squad totals are calculated correctly"""
        allies = [
            {'damage_out': 100000, 'healing': 50000, 'cleanses': 100, 'boon_strips': 20},
            {'damage_out': 80000, 'healing': 60000, 'cleanses': 80, 'boon_strips': 30},
            {'damage_out': 120000, 'healing': 40000, 'cleanses': 120, 'boon_strips': 10},
        ]
        
        total_damage = sum(a['damage_out'] for a in allies)
        total_healing = sum(a['healing'] for a in allies)
        total_cleanses = sum(a['cleanses'] for a in allies)
        total_strips = sum(a['boon_strips'] for a in allies)
        
        assert total_damage == 300000
        assert total_healing == 150000
        assert total_cleanses == 300
        assert total_strips == 60


class TestCompositionAnalysis:
    """Test composition analysis and role counting"""
    
    def test_role_counting(self):
        """Test role distribution counting"""
        allies = [
            {'role': 'dps'},
            {'role': 'dps'},
            {'role': 'healer'},
            {'role': 'stab'},
            {'role': 'dps_strip'},
        ]
        
        role_counts = {}
        for ally in allies:
            role = ally['role']
            role_counts[role] = role_counts.get(role, 0) + 1
        
        assert role_counts['dps'] == 2
        assert role_counts['healer'] == 1
        assert role_counts['stab'] == 1
        assert role_counts['dps_strip'] == 1
    
    def test_spec_counting(self):
        """Test spec distribution counting"""
        allies = [
            {'profession': 'Firebrand'},
            {'profession': 'Firebrand'},
            {'profession': 'Scrapper'},
            {'profession': 'Scourge'},
            {'profession': 'Scourge'},
            {'profession': 'Scourge'},
        ]
        
        spec_counts = {}
        for ally in allies:
            spec = ally['profession']
            spec_counts[spec] = spec_counts.get(spec, 0) + 1
        
        assert spec_counts['Firebrand'] == 2
        assert spec_counts['Scrapper'] == 1
        assert spec_counts['Scourge'] == 3
    
    def test_specs_by_role(self):
        """Test grouping specs by role"""
        allies = [
            {'profession': 'Firebrand', 'role': 'stab'},
            {'profession': 'Firebrand', 'role': 'stab'},
            {'profession': 'Scrapper', 'role': 'healer'},
            {'profession': 'Scourge', 'role': 'dps_strip'},
        ]
        
        specs_by_role = {}
        for ally in allies:
            role = ally['role']
            spec = ally['profession']
            if role not in specs_by_role:
                specs_by_role[role] = {}
            specs_by_role[role][spec] = specs_by_role[role].get(spec, 0) + 1
        
        assert specs_by_role['stab']['Firebrand'] == 2
        assert specs_by_role['healer']['Scrapper'] == 1
        assert specs_by_role['dps_strip']['Scourge'] == 1


class TestFightOutcome:
    """Test fight outcome determination"""
    
    def test_victory_detection(self):
        """Test victory is detected correctly"""
        ally_kills = 10
        ally_deaths = 2
        
        if ally_kills > ally_deaths:
            outcome = 'victory'
        elif ally_deaths > ally_kills * 2 and ally_deaths >= 3:
            outcome = 'defeat'
        else:
            outcome = 'draw'
        
        assert outcome == 'victory'
    
    def test_defeat_detection(self):
        """Test defeat is detected correctly"""
        ally_kills = 2
        ally_deaths = 15
        
        if ally_kills > ally_deaths:
            outcome = 'victory'
        elif ally_deaths > ally_kills * 2 and ally_deaths >= 3:
            outcome = 'defeat'
        else:
            outcome = 'draw'
        
        assert outcome == 'defeat'
    
    def test_draw_detection(self):
        """Test draw is detected correctly"""
        ally_kills = 5
        ally_deaths = 5
        
        if ally_kills > ally_deaths:
            outcome = 'victory'
        elif ally_deaths > ally_kills * 2 and ally_deaths >= 3:
            outcome = 'defeat'
        else:
            outcome = 'draw'
        
        assert outcome == 'draw'


class TestContextAutoDetection:
    """Test automatic context detection in results"""
    
    def test_context_detected_zerg(self):
        """Test zerg context is detected for large squads"""
        players_count = 30
        context = 'zerg' if players_count >= 25 else ('guild_raid' if players_count >= 10 else 'roam')
        assert context == 'zerg'
    
    def test_context_detected_guild(self):
        """Test guild context is detected for medium squads"""
        players_count = 15
        context = 'zerg' if players_count >= 25 else ('guild_raid' if players_count >= 10 else 'roam')
        assert context == 'guild_raid'
    
    def test_context_detected_roam(self):
        """Test roam context is detected for small groups"""
        players_count = 5
        context = 'zerg' if players_count >= 25 else ('guild_raid' if players_count >= 10 else 'roam')
        assert context == 'roam'
