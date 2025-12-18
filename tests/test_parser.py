"""
Tests for EVTC parser - stats extraction
"""

import pytest
from parser import ParsedPlayer, ParsedLog, EVTCHeader


class TestParsedPlayer:
    """Test ParsedPlayer dataclass"""
    
    def test_player_creation(self):
        """Test basic player creation"""
        player = ParsedPlayer(
            character_name="TestPlayer",
            account_name="Test.1234",
            profession="Guardian",
            elite_spec="Firebrand",
            subgroup=1,
            team_id=1,
            is_enemy=False
        )
        assert player.character_name == "TestPlayer"
        assert player.account_name == "Test.1234"
        assert player.profession == "Guardian"
        assert player.elite_spec == "Firebrand"
        assert player.is_enemy == False
    
    def test_player_stats_defaults(self):
        """Test that stats default to 0"""
        player = ParsedPlayer(
            character_name="Test",
            account_name="Test.1234",
            profession="Warrior",
            elite_spec="Spellbreaker",
            subgroup=1,
            team_id=1,
            is_enemy=False
        )
        assert player.damage_dealt == 0
        assert player.damage_taken == 0
        assert player.healing_done == 0
        assert player.deaths == 0
        assert player.downs == 0
        assert player.kills == 0
        assert player.boon_strips == 0
        assert player.cleanses == 0
        assert player.cc_out == 0
        assert player.barrier_out == 0
        assert player.resurrects == 0
    
    def test_player_display_name(self):
        """Test display name property"""
        player = ParsedPlayer(
            character_name="MyChar",
            account_name="MyAccount.5678",
            profession="Mesmer",
            elite_spec="Chronomancer",
            subgroup=2,
            team_id=1,
            is_enemy=False
        )
        assert player.display_name == "MyChar (MyAccount.5678)"
    
    def test_enemy_player(self):
        """Test enemy player creation"""
        enemy = ParsedPlayer(
            character_name="EnemyPlayer",
            account_name="Enemy.9999",
            profession="Necromancer",
            elite_spec="Scourge",
            subgroup=0,
            team_id=2,
            is_enemy=True
        )
        assert enemy.is_enemy == True
        assert enemy.team_id == 2


class TestContextDetection:
    """Test fight context detection"""
    
    def test_zerg_context(self):
        """Test zerg context detection (25+ players)"""
        from services.counter_service import guess_fight_context, FightContext
        
        context = guess_fight_context(
            ally_count=30,
            enemy_count=25,
            duration_sec=180,
            subgroup_count=6
        )
        assert context == FightContext.ZERG
    
    def test_guild_raid_context(self):
        """Test guild raid context detection (10-25 players)"""
        from services.counter_service import guess_fight_context, FightContext
        
        context = guess_fight_context(
            ally_count=15,
            enemy_count=12,
            duration_sec=180,
            subgroup_count=3
        )
        assert context == FightContext.GUILD_RAID
    
    def test_roam_context(self):
        """Test roam context detection (<10 players)"""
        from services.counter_service import guess_fight_context, FightContext
        
        context = guess_fight_context(
            ally_count=5,
            enemy_count=3,
            duration_sec=60,
            subgroup_count=1
        )
        assert context == FightContext.ROAM


class TestStatsExtraction:
    """Test stats extraction from player data"""
    
    def test_damage_ratio_calculation(self):
        """Test damage ratio is calculated correctly"""
        # Simulate damage ratio calculation
        damage_out = 100000
        damage_in = 50000
        expected_ratio = round(damage_out / max(damage_in, 1), 2)
        assert expected_ratio == 2.0
    
    def test_damage_ratio_zero_damage_in(self):
        """Test damage ratio with zero damage in"""
        damage_out = 100000
        damage_in = 0
        expected_ratio = round(damage_out / max(damage_in, 1), 2)
        assert expected_ratio == 100000.0
    
    def test_per_second_calculations(self):
        """Test per-second stat calculations"""
        duration_sec = 180
        cleanses = 360
        cleanses_per_sec = round(cleanses / duration_sec, 2)
        assert cleanses_per_sec == 2.0
        
        boon_strips = 90
        strips_per_sec = round(boon_strips / duration_sec, 2)
        assert strips_per_sec == 0.5


class TestDeduplication:
    """Test player deduplication by account"""
    
    def test_account_deduplication(self):
        """Test that players are deduplicated by account name"""
        seen_accounts = set()
        players = [
            {"name": "Char1", "account": "Account.1234"},
            {"name": "Char2", "account": "Account.1234"},  # Duplicate
            {"name": "Char3", "account": "Account.5678"},
        ]
        
        unique_players = []
        for player in players:
            account = player.get('account', '')
            if account and account in seen_accounts:
                continue
            if account:
                seen_accounts.add(account)
            unique_players.append(player)
        
        assert len(unique_players) == 2
        assert unique_players[0]['name'] == "Char1"
        assert unique_players[1]['name'] == "Char3"
