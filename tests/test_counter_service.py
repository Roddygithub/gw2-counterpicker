"""
Tests for the stats-based counter service
"""

import pytest
from pathlib import Path
from datetime import datetime
from services.counter_service import (
    CounterService,
    FightContext,
    guess_fight_context,
    AllyBuildRecord,
    FightRecord
)


@pytest.fixture
def counter_service(tmp_path):
    """Create a counter service with temporary database"""
    db_path = tmp_path / "test_fights.db"
    return CounterService(db_path)


@pytest.fixture
def sample_fight_data():
    """Sample fight data for testing"""
    return {
        'duration_sec': 120,
        'allies': [
            {
                'name': 'Player1',
                'account': 'Account1.1234',
                'profession': 'Firebrand',
                'role': 'stab',
                'group': 1,
                'damage': 50000,
                'damage_out': 50000,
                'damage_in': 30000,
                'dps': 416,
                'healing': 10000,
                'cleanses': 5,
                'boon_strips': 2,
                'down_contrib': 1,
                'deaths': 0,
                'kills': 2,
                'boon_gen': {'stability': 0.8}
            },
            {
                'name': 'Player2',
                'account': 'Account2.5678',
                'profession': 'Scourge',
                'role': 'dps',
                'group': 1,
                'damage': 80000,
                'damage_out': 80000,
                'damage_in': 20000,
                'dps': 666,
                'healing': 5000,
                'cleanses': 1,
                'boon_strips': 10,
                'down_contrib': 3,
                'deaths': 0,
                'kills': 3,
                'boon_gen': {}
            }
        ],
        'enemies': [
            {'profession': 'Herald', 'name': 'Enemy1'},
            {'profession': 'Scrapper', 'name': 'Enemy2'},
            {'profession': 'Spellbreaker', 'name': 'Enemy3'}
        ],
        'composition': {
            'spec_counts': {'Firebrand': 1, 'Scourge': 1},
            'role_counts': {'stab': 1, 'dps': 1},
            'total_players': 2
        },
        'enemy_composition': {
            'spec_counts': {'Herald': 1, 'Scrapper': 1, 'Spellbreaker': 1},
            'role_counts': {'boon': 1, 'support': 1, 'frontline': 1},
            'total': 3
        },
        'fight_stats': {
            'ally_deaths': 0,
            'ally_kills': 5,
            'ally_damage': 130000,
            'enemy_damage_taken': 130000
        },
        'fight_outcome': 'victory',
        'source': 'evtc',
        'source_name': 'test_fight.evtc'
    }


class TestFightContext:
    """Test fight context detection"""
    
    def test_roam_context(self):
        """Small scale fights should be detected as roaming"""
        context = guess_fight_context(
            ally_count=5,
            enemy_count=8,
            duration_sec=180,
            subgroup_count=1,
            main_guild_ratio=0.0
        )
        assert context == FightContext.ROAM
    
    def test_zerg_context_large_allies(self):
        """Large ally count should be detected as zerg"""
        context = guess_fight_context(
            ally_count=30,
            enemy_count=15,
            duration_sec=300,
            subgroup_count=2,
            main_guild_ratio=0.3
        )
        assert context == FightContext.ZERG
    
    def test_zerg_context_large_enemies(self):
        """Large enemy count should be detected as zerg"""
        context = guess_fight_context(
            ally_count=20,
            enemy_count=35,
            duration_sec=300,
            subgroup_count=2,
            main_guild_ratio=0.3
        )
        assert context == FightContext.ZERG
    
    def test_guild_raid_context_high_cohesion(self):
        """Medium size with high guild cohesion should be guild raid"""
        context = guess_fight_context(
            ally_count=15,
            enemy_count=18,
            duration_sec=240,
            subgroup_count=2,
            main_guild_ratio=0.6
        )
        assert context == FightContext.GUILD_RAID
    
    def test_guild_raid_context_multiple_subgroups(self):
        """Medium size with multiple subgroups should be guild raid"""
        context = guess_fight_context(
            ally_count=20,
            enemy_count=22,
            duration_sec=240,
            subgroup_count=3,
            main_guild_ratio=0.3
        )
        assert context == FightContext.GUILD_RAID
    
    def test_unknown_context(self):
        """Ambiguous fights should be unknown"""
        context = guess_fight_context(
            ally_count=15,
            enemy_count=12,
            duration_sec=120,
            subgroup_count=1,
            main_guild_ratio=0.2
        )
        assert context == FightContext.UNKNOWN


class TestCounterService:
    """Test counter service functionality"""
    
    def test_initialization(self, counter_service):
        """Service should initialize with empty database"""
        stats = counter_service.get_stats()
        assert stats['total_fights'] == 0
        assert stats['victories'] == 0
        assert stats['win_rate'] == 0
    
    def test_record_fight(self, counter_service, sample_fight_data):
        """Should record a fight successfully"""
        fight_id = counter_service.record_fight(sample_fight_data)
        
        assert fight_id is not None
        assert fight_id.startswith('fight_')
        
        stats = counter_service.get_stats()
        assert stats['total_fights'] == 1
        assert stats['victories'] == 1
        assert stats['win_rate'] == 100.0
    
    def test_duplicate_file_detection(self, counter_service, sample_fight_data):
        """Should detect and skip duplicate files"""
        fight_id1 = counter_service.record_fight(
            sample_fight_data,
            filename='test.evtc',
            filesize=1000
        )
        
        fight_id2 = counter_service.record_fight(
            sample_fight_data,
            filename='test.evtc',
            filesize=1000
        )
        
        assert fight_id1 is not None
        assert fight_id2 is None
        
        stats = counter_service.get_stats()
        assert stats['total_fights'] == 1
    
    def test_duplicate_fight_detection(self, counter_service, sample_fight_data):
        """Should detect and skip duplicate fights from different uploaders"""
        fight_id1 = counter_service.record_fight(
            sample_fight_data,
            filename='uploader1.evtc',
            filesize=1000
        )
        
        fight_id2 = counter_service.record_fight(
            sample_fight_data,
            filename='uploader2.evtc',
            filesize=2000
        )
        
        assert fight_id1 is not None
        assert fight_id2 is None
    
    def test_short_fight_rejection(self, counter_service, sample_fight_data):
        """Should reject fights shorter than 60 seconds"""
        sample_fight_data['duration_sec'] = 30
        
        fight_id = counter_service.record_fight(
            sample_fight_data,
            filename='short.evtc',
            filesize=500
        )
        
        assert fight_id is None
        
        stats = counter_service.get_stats()
        assert stats['total_fights'] == 0
    
    def test_generate_counter(self, counter_service, sample_fight_data):
        """Should generate counter recommendations"""
        counter_service.record_fight(sample_fight_data)
        
        enemy_comp = {'Herald': 1, 'Scrapper': 1, 'Spellbreaker': 1}
        
        import asyncio
        result = asyncio.run(counter_service.generate_counter(enemy_comp, context='zerg'))
        
        assert result['success'] is True
        assert 'counter' in result
        assert 'precision' in result
        assert result['model'] == 'stats_engine'
        assert 'CONTER:' in result['counter']
        assert 'FOCUS:' in result['counter']
        assert 'TACTIQUE:' in result['counter']
    
    def test_best_builds_against(self, counter_service, sample_fight_data):
        """Should find best performing builds"""
        counter_service.record_fight(sample_fight_data)
        
        enemy_comp = {'Herald': 1, 'Scrapper': 1, 'Spellbreaker': 1}
        best_builds = counter_service.get_best_builds_against(enemy_comp)
        
        assert isinstance(best_builds, dict)
    
    def test_feedback_recording(self, counter_service):
        """Should record user feedback"""
        enemy_comp = {'Firebrand': 2, 'Scourge': 3}
        
        counter_service.record_feedback(enemy_comp, worked=True, context='zerg')
        counter_service.record_feedback(enemy_comp, worked=False, context='zerg')
        
        summary = counter_service.get_feedback_summary()
        
        assert summary['count'] == 2
        assert len(summary['by_comp']) > 0
    
    def test_settings_management(self, counter_service):
        """Should manage settings"""
        settings = counter_service.get_settings()
        assert 'feedback_weight' in settings
        assert settings['feedback_weight'] == 0.0
        
        updated = counter_service.update_settings({'feedback_weight': 0.5})
        assert updated['feedback_weight'] == 0.5
        
        retrieved = counter_service.get_settings()
        assert retrieved['feedback_weight'] == 0.5
    
    def test_get_status(self, counter_service, sample_fight_data):
        """Should return service status"""
        counter_service.record_fight(sample_fight_data)
        
        status = counter_service.get_status()
        
        assert status['total_fights'] == 1
        assert status['win_rate'] == 100.0
        assert status['status'] == 'active'
        assert status['engine'] == 'stats_based'
        assert 'unique_players' in status
        assert 'last_updated' in status


class TestAllyBuildRecord:
    """Test ally build record dataclass"""
    
    def test_creation(self):
        """Should create build record"""
        build = AllyBuildRecord(
            player_name='TestPlayer',
            account='Test.1234',
            profession='Firebrand',
            elite_spec='Firebrand',
            role='stab',
            group=1,
            damage_out=50000,
            damage_in=30000,
            dps=416.0,
            healing=10000,
            cleanses=5,
            boon_strips=2,
            down_contrib=1,
            deaths=0,
            boon_gen={'stability': 0.8},
            kills=2
        )
        
        assert build.player_name == 'TestPlayer'
        assert build.role == 'stab'
        assert build.kills == 2
    
    def test_to_dict(self):
        """Should convert to dictionary"""
        build = AllyBuildRecord(
            player_name='TestPlayer',
            account='Test.1234',
            profession='Firebrand',
            elite_spec='Firebrand',
            role='stab',
            group=1,
            damage_out=50000,
            damage_in=30000,
            dps=416.0,
            healing=10000,
            cleanses=5,
            boon_strips=2,
            down_contrib=1,
            deaths=0,
            boon_gen={'stability': 0.8},
            kills=2
        )
        
        data = build.to_dict()
        assert isinstance(data, dict)
        assert data['player_name'] == 'TestPlayer'
        assert data['kills'] == 2


class TestFightRecord:
    """Test fight record dataclass"""
    
    def test_context_property(self):
        """Should return confirmed context if set, otherwise detected"""
        record = FightRecord(
            fight_id='test_123',
            timestamp=datetime.now().isoformat(),
            source='evtc',
            source_name='test.evtc',
            enemy_composition={'Herald': 1},
            ally_composition={'Firebrand': 1},
            ally_builds=[],
            outcome='victory',
            duration_sec=120.0,
            ally_deaths=0,
            ally_kills=5,
            enemy_deaths=5,
            total_ally_damage=100000,
            total_enemy_damage=50000,
            context_detected='zerg',
            context_confirmed=None
        )
        
        assert record.context == 'zerg'
        
        record.context_confirmed = 'guild_raid'
        assert record.context == 'guild_raid'
    
    def test_to_dict_from_dict(self):
        """Should convert to/from dictionary"""
        original = FightRecord(
            fight_id='test_123',
            timestamp=datetime.now().isoformat(),
            source='evtc',
            source_name='test.evtc',
            enemy_composition={'Herald': 1},
            ally_composition={'Firebrand': 1},
            ally_builds=[],
            outcome='victory',
            duration_sec=120.0,
            ally_deaths=0,
            ally_kills=5,
            enemy_deaths=5,
            total_ally_damage=100000,
            total_enemy_damage=50000,
            context_detected='zerg',
            context_confirmed='guild_raid'
        )
        
        data = original.to_dict()
        assert isinstance(data, dict)
        assert data['context'] == 'guild_raid'
        
        restored = FightRecord.from_dict(data)
        assert restored.fight_id == original.fight_id
        assert restored.context == 'guild_raid'
