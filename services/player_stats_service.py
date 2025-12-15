"""
Player Stats Service
Tracks personal WvW statistics linked to GW2 accounts
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from pathlib import Path
from tinydb import TinyDB, Query
from logger import get_logger

logger = get_logger('player_stats')

# Database for player stats
db_path = Path(__file__).parent.parent / "data" / "player_stats.json"
db_path.parent.mkdir(parents=True, exist_ok=True)
player_stats_db = TinyDB(str(db_path))

# Tables
fights_table = player_stats_db.table('fights')
sessions_table = player_stats_db.table('sessions')
guild_stats_table = player_stats_db.table('guild_stats')


@dataclass
class PlayerFightRecord:
    """Record of a player's participation in a fight"""
    account_id: str
    account_name: str
    character_name: str
    profession: str
    elite_spec: str
    role: str
    fight_date: str
    fight_duration: int  # seconds
    damage_out: int
    damage_in: int
    kills: int
    deaths: int
    downs: int
    cleanses: int
    strips: int
    healing: int
    barrier: int
    boon_uptime: Dict[str, float]  # {boon_name: uptime %}
    outcome: str  # "victory", "defeat", "draw"
    enemy_count: int
    ally_count: int
    map_name: str = ""
    dps: int = 0
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class PlayerCareerStats:
    """Aggregated career statistics for a player"""
    account_id: str
    account_name: str
    total_fights: int
    total_victories: int
    total_defeats: int
    total_time_played: int  # seconds
    total_kills: int
    total_deaths: int
    total_damage_out: int
    total_damage_in: int
    avg_dps: float
    avg_kills_per_fight: float
    avg_deaths_per_fight: float
    favorite_profession: str
    favorite_elite_spec: str
    favorite_role: str
    specs_played: Dict[str, int]  # {spec: count}
    roles_played: Dict[str, int]  # {role: count}
    monthly_stats: Dict[str, Dict]  # {month: {stats}}
    last_fight_date: str
    first_fight_date: str
    
    def to_dict(self) -> Dict:
        return asdict(self)


def record_player_fight(
    account_id: str,
    account_name: str,
    character_name: str,
    profession: str,
    elite_spec: str,
    role: str,
    fight_data: Dict
) -> bool:
    """Record a fight for a player's history"""
    try:
        record = PlayerFightRecord(
            account_id=account_id,
            account_name=account_name,
            character_name=character_name,
            profession=profession,
            elite_spec=elite_spec or profession,
            role=role,
            fight_date=datetime.now().isoformat(),
            fight_duration=fight_data.get('duration', 0),
            damage_out=fight_data.get('damage_out', 0),
            damage_in=fight_data.get('damage_in', 0),
            kills=fight_data.get('kills', 0),
            deaths=fight_data.get('deaths', 0),
            downs=fight_data.get('downs', 0),
            cleanses=fight_data.get('cleanses', 0),
            strips=fight_data.get('strips', 0),
            healing=fight_data.get('healing', 0),
            barrier=fight_data.get('barrier', 0),
            boon_uptime=fight_data.get('boon_uptime', {}),
            outcome=fight_data.get('outcome', 'draw'),
            enemy_count=fight_data.get('enemy_count', 0),
            ally_count=fight_data.get('ally_count', 0),
            map_name=fight_data.get('map_name', ''),
            dps=fight_data.get('dps', 0)
        )
        
        fights_table.insert(record.to_dict())
        logger.info(f"Recorded fight for {account_name} as {elite_spec}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to record fight: {e}")
        return False


def get_player_fights(account_id: str, limit: int = 50) -> List[Dict]:
    """Get recent fights for a player"""
    try:
        Fight = Query()
        fights = fights_table.search(Fight.account_id == account_id)
        
        # Sort by date descending
        fights.sort(key=lambda x: x.get('fight_date', ''), reverse=True)
        
        return fights[:limit]
        
    except Exception as e:
        logger.error(f"Failed to get player fights: {e}")
        return []


def get_player_career_stats(account_id: str) -> Optional[PlayerCareerStats]:
    """Calculate career stats for a player"""
    try:
        fights = get_player_fights(account_id, limit=1000)
        
        if not fights:
            return None
        
        # Aggregate stats
        total_fights = len(fights)
        total_victories = sum(1 for f in fights if f.get('outcome') == 'victory')
        total_defeats = sum(1 for f in fights if f.get('outcome') == 'defeat')
        total_time = sum(f.get('fight_duration', 0) for f in fights)
        total_kills = sum(f.get('kills', 0) for f in fights)
        total_deaths = sum(f.get('deaths', 0) for f in fights)
        total_damage_out = sum(f.get('damage_out', 0) for f in fights)
        total_damage_in = sum(f.get('damage_in', 0) for f in fights)
        
        # Calculate averages
        avg_dps = sum(f.get('dps', 0) for f in fights) / total_fights if total_fights > 0 else 0
        avg_kills = total_kills / total_fights if total_fights > 0 else 0
        avg_deaths = total_deaths / total_fights if total_fights > 0 else 0
        
        # Count specs and roles
        specs_played = {}
        roles_played = {}
        for fight in fights:
            spec = fight.get('elite_spec', 'Unknown')
            role = fight.get('role', 'dps')
            specs_played[spec] = specs_played.get(spec, 0) + 1
            roles_played[role] = roles_played.get(role, 0) + 1
        
        # Find favorites
        favorite_spec = max(specs_played.items(), key=lambda x: x[1])[0] if specs_played else "Unknown"
        favorite_role = max(roles_played.items(), key=lambda x: x[1])[0] if roles_played else "dps"
        favorite_profession = fights[0].get('profession', 'Unknown') if fights else "Unknown"
        
        # Monthly breakdown
        monthly_stats = {}
        for fight in fights:
            date_str = fight.get('fight_date', '')
            if date_str:
                month = date_str[:7]  # YYYY-MM
                if month not in monthly_stats:
                    monthly_stats[month] = {
                        'fights': 0, 'victories': 0, 'kills': 0, 'deaths': 0,
                        'damage_out': 0, 'time_played': 0
                    }
                monthly_stats[month]['fights'] += 1
                if fight.get('outcome') == 'victory':
                    monthly_stats[month]['victories'] += 1
                monthly_stats[month]['kills'] += fight.get('kills', 0)
                monthly_stats[month]['deaths'] += fight.get('deaths', 0)
                monthly_stats[month]['damage_out'] += fight.get('damage_out', 0)
                monthly_stats[month]['time_played'] += fight.get('fight_duration', 0)
        
        # Get date range
        dates = [f.get('fight_date', '') for f in fights if f.get('fight_date')]
        first_date = min(dates) if dates else ''
        last_date = max(dates) if dates else ''
        
        return PlayerCareerStats(
            account_id=account_id,
            account_name=fights[0].get('account_name', 'Unknown'),
            total_fights=total_fights,
            total_victories=total_victories,
            total_defeats=total_defeats,
            total_time_played=total_time,
            total_kills=total_kills,
            total_deaths=total_deaths,
            total_damage_out=total_damage_out,
            total_damage_in=total_damage_in,
            avg_dps=round(avg_dps, 1),
            avg_kills_per_fight=round(avg_kills, 2),
            avg_deaths_per_fight=round(avg_deaths, 2),
            favorite_profession=favorite_profession,
            favorite_elite_spec=favorite_spec,
            favorite_role=favorite_role,
            specs_played=specs_played,
            roles_played=roles_played,
            monthly_stats=monthly_stats,
            last_fight_date=last_date,
            first_fight_date=first_date
        )
        
    except Exception as e:
        logger.error(f"Failed to calculate career stats: {e}")
        return None


def get_player_spec_stats(account_id: str) -> Dict[str, Dict]:
    """Get detailed stats per specialization for a player"""
    try:
        fights = get_player_fights(account_id, limit=1000)
        
        spec_stats = {}
        for fight in fights:
            spec = fight.get('elite_spec', 'Unknown')
            if spec not in spec_stats:
                spec_stats[spec] = {
                    'fights': 0, 'victories': 0, 'kills': 0, 'deaths': 0,
                    'total_dps': 0, 'total_damage': 0, 'time_played': 0,
                    'boon_uptimes': {}
                }
            
            stats = spec_stats[spec]
            stats['fights'] += 1
            if fight.get('outcome') == 'victory':
                stats['victories'] += 1
            stats['kills'] += fight.get('kills', 0)
            stats['deaths'] += fight.get('deaths', 0)
            stats['total_dps'] += fight.get('dps', 0)
            stats['total_damage'] += fight.get('damage_out', 0)
            stats['time_played'] += fight.get('fight_duration', 0)
            
            # Aggregate boon uptimes
            for boon, uptime in fight.get('boon_uptime', {}).items():
                if boon not in stats['boon_uptimes']:
                    stats['boon_uptimes'][boon] = []
                stats['boon_uptimes'][boon].append(uptime)
        
        # Calculate averages
        for spec, stats in spec_stats.items():
            if stats['fights'] > 0:
                stats['avg_dps'] = round(stats['total_dps'] / stats['fights'], 1)
                stats['avg_kills'] = round(stats['kills'] / stats['fights'], 2)
                stats['avg_deaths'] = round(stats['deaths'] / stats['fights'], 2)
                stats['win_rate'] = round(stats['victories'] / stats['fights'] * 100, 1)
                stats['hours_played'] = round(stats['time_played'] / 3600, 1)
                
                # Average boon uptimes
                for boon, uptimes in stats['boon_uptimes'].items():
                    stats['boon_uptimes'][boon] = round(sum(uptimes) / len(uptimes), 1)
        
        return spec_stats
        
    except Exception as e:
        logger.error(f"Failed to get spec stats: {e}")
        return {}


# ==================== GUILD STATS ====================

@dataclass
class GuildStats:
    """Aggregated statistics for a guild"""
    guild_id: str
    guild_name: str
    guild_tag: str
    total_fights: int
    total_victories: int
    member_count: int
    active_members: int  # Members with recent fights
    avg_squad_size: float
    role_distribution: Dict[str, int]
    spec_distribution: Dict[str, int]
    top_performers: List[Dict]
    recent_fights: List[Dict]
    monthly_activity: Dict[str, int]
    
    @property
    def win_rate(self) -> float:
        """Calculate win rate percentage"""
        if self.total_fights == 0:
            return 0.0
        return (self.total_victories / self.total_fights) * 100
    
    def to_dict(self) -> Dict:
        # Manual conversion to avoid TinyDB Document serialization issues
        return {
            'guild_id': self.guild_id,
            'guild_name': self.guild_name,
            'guild_tag': self.guild_tag,
            'total_fights': self.total_fights,
            'total_victories': self.total_victories,
            'member_count': self.member_count,
            'active_members': self.active_members,
            'avg_squad_size': self.avg_squad_size,
            'role_distribution': dict(self.role_distribution),
            'spec_distribution': dict(self.spec_distribution),
            'top_performers': list(self.top_performers),
            'recent_fights': [dict(f) for f in self.recent_fights],
            'monthly_activity': dict(self.monthly_activity),
            'win_rate': self.win_rate
        }


def record_guild_fight(
    guild_id: str,
    guild_name: str,
    guild_tag: str,
    fight_data: Dict,
    participants: List[Dict]
) -> bool:
    """Record a fight for guild statistics"""
    try:
        record = {
            'guild_id': guild_id,
            'guild_name': guild_name,
            'guild_tag': guild_tag,
            'fight_date': datetime.now().isoformat(),
            'duration': fight_data.get('duration', 0),
            'outcome': fight_data.get('outcome', 'draw'),
            'ally_count': len(participants),
            'enemy_count': fight_data.get('enemy_count', 0),
            'total_damage': sum(p.get('damage_out', 0) for p in participants),
            'total_kills': sum(p.get('kills', 0) for p in participants),
            'total_deaths': sum(p.get('deaths', 0) for p in participants),
            'participants': [
                {
                    'account_id': p.get('account_id', ''),
                    'account_name': p.get('account_name', ''),
                    'elite_spec': p.get('elite_spec', ''),
                    'role': p.get('role', 'dps')
                }
                for p in participants
            ]
        }
        
        guild_stats_table.insert(record)
        logger.info(f"Recorded guild fight for [{guild_tag}] {guild_name}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to record guild fight: {e}")
        return False


def get_guild_stats(guild_id: str) -> Optional[GuildStats]:
    """Calculate statistics for a guild"""
    try:
        Guild = Query()
        fights = guild_stats_table.search(Guild.guild_id == guild_id)
        
        if not fights:
            return None
        
        # Sort by date
        fights.sort(key=lambda x: x.get('fight_date', ''), reverse=True)
        
        total_fights = len(fights)
        total_victories = sum(1 for f in fights if f.get('outcome') == 'victory')
        
        # Collect all unique members
        all_members = {}
        role_dist = {}
        spec_dist = {}
        
        for fight in fights:
            for p in fight.get('participants', []):
                acc_id = p.get('account_id', '')
                if acc_id:
                    if acc_id not in all_members:
                        all_members[acc_id] = {
                            'account_name': p.get('account_name', ''),
                            'fights': 0, 'recent': False
                        }
                    all_members[acc_id]['fights'] += 1
                    
                    # Check if recent (last 30 days)
                    fight_date = fight.get('fight_date', '')
                    if fight_date:
                        try:
                            fd = datetime.fromisoformat(fight_date)
                            if datetime.now() - fd < timedelta(days=30):
                                all_members[acc_id]['recent'] = True
                        except:
                            pass
                
                # Role and spec distribution
                role = p.get('role', 'dps')
                spec = p.get('elite_spec', 'Unknown')
                role_dist[role] = role_dist.get(role, 0) + 1
                spec_dist[spec] = spec_dist.get(spec, 0) + 1
        
        # Calculate averages
        avg_squad = sum(f.get('ally_count', 0) for f in fights) / total_fights if total_fights > 0 else 0
        
        # Top performers by participation
        top_performers = sorted(
            [{'account_name': m['account_name'], 'fights': m['fights']} 
             for m in all_members.values()],
            key=lambda x: x['fights'],
            reverse=True
        )[:10]
        
        # Monthly activity
        monthly = {}
        for fight in fights:
            date_str = fight.get('fight_date', '')
            if date_str:
                month = date_str[:7]
                monthly[month] = monthly.get(month, 0) + 1
        
        # Get guild info from first fight
        guild_name = fights[0].get('guild_name', 'Unknown')
        guild_tag = fights[0].get('guild_tag', '')
        
        return GuildStats(
            guild_id=guild_id,
            guild_name=guild_name,
            guild_tag=guild_tag,
            total_fights=total_fights,
            total_victories=total_victories,
            member_count=len(all_members),
            active_members=sum(1 for m in all_members.values() if m['recent']),
            avg_squad_size=round(avg_squad, 1),
            role_distribution=role_dist,
            spec_distribution=spec_dist,
            top_performers=top_performers,
            recent_fights=fights[:10],
            monthly_activity=monthly
        )
        
    except Exception as e:
        logger.error(f"Failed to get guild stats: {e}")
        return None


def get_guilds_for_account(account_id: str) -> List[str]:
    """Get all guild IDs that an account has participated in"""
    try:
        fights = get_player_fights(account_id, limit=1000)
        guild_ids = set()
        
        # This would need to be enhanced with actual guild data
        # For now, return empty - guilds would be linked via API
        return list(guild_ids)
        
    except Exception as e:
        logger.error(f"Failed to get guilds for account: {e}")
        return []


def import_fights_from_ai_database(account_id: str, account_name: str) -> Dict[str, Any]:
    """
    Import existing fights from the AI learning database into player stats.
    Matches fights where the account name appears in ally_builds.
    """
    try:
        from counter_ai import fights_table as ai_fights_table
        
        # Get all fights from AI database
        all_fights = ai_fights_table.all()
        
        imported_count = 0
        skipped_count = 0
        matched_fights = []
        
        # Extract account name prefix for matching (e.g., "Roddy" from "Roddy.1234")
        account_prefix = account_name.split('.')[0].lower()
        
        for fight in all_fights:
            ally_builds = fight.get('ally_builds', [])
            
            # Search for account in ally builds
            player_data = None
            for ally in ally_builds:
                ally_name = ally.get('player_name', '').lower()
                ally_account = ally.get('account', '').lower()
                
                # Match by account name or player name containing account prefix
                if account_prefix in ally_name or account_prefix in ally_account:
                    player_data = ally
                    break
            
            if not player_data:
                continue
            
            # Check if already imported (by fight timestamp + account)
            fight_date = fight.get('timestamp', '')
            Fight = Query()
            existing = fights_table.search(
                (Fight.account_id == account_id) & 
                (Fight.fight_date == fight_date)
            )
            
            if existing:
                skipped_count += 1
                continue
            
            # Create fight record
            record = PlayerFightRecord(
                account_id=account_id,
                account_name=account_name,
                character_name=player_data.get('player_name', 'Unknown'),
                profession=player_data.get('profession', 'Unknown'),
                elite_spec=player_data.get('elite_spec', player_data.get('profession', 'Unknown')),
                role=player_data.get('role', 'dps'),
                fight_date=fight_date,
                fight_duration=int(fight.get('duration_sec', 0)),
                damage_out=player_data.get('damage_out', 0),
                damage_in=player_data.get('damage_in', 0),
                kills=fight.get('enemy_deaths', 0) // max(len(ally_builds), 1),  # Estimate kills per player
                deaths=player_data.get('deaths', 0),
                downs=0,  # Not tracked individually
                cleanses=player_data.get('cleanses', 0),
                strips=player_data.get('boon_strips', 0),
                healing=player_data.get('healing', 0),
                barrier=0,
                boon_uptime=player_data.get('boon_gen', {}),
                outcome=fight.get('outcome', 'draw'),
                enemy_count=sum(fight.get('enemy_composition', {}).values()),
                ally_count=len(ally_builds),
                map_name='',
                dps=int(player_data.get('dps', 0))
            )
            
            fights_table.insert(record.to_dict())
            imported_count += 1
            matched_fights.append({
                'date': fight_date,
                'spec': record.elite_spec,
                'outcome': record.outcome
            })
        
        logger.info(f"Imported {imported_count} fights for {account_name}, skipped {skipped_count} duplicates")
        
        return {
            'success': True,
            'imported': imported_count,
            'skipped': skipped_count,
            'total_in_db': len(all_fights),
            'sample_fights': matched_fights[:5]
        }
        
    except Exception as e:
        logger.error(f"Failed to import fights: {e}")
        return {
            'success': False,
            'error': str(e),
            'imported': 0
        }


def import_guild_fights_from_ai_database(guild_id: str, guild_name: str, guild_tag: str) -> Dict[str, Any]:
    """
    Import existing fights from the AI learning database into guild stats.
    Matches fights where guild members participated.
    """
    try:
        from counter_ai import fights_table as ai_fights_table
        
        all_fights = ai_fights_table.all()
        
        imported_count = 0
        skipped_count = 0
        
        for fight in all_fights:
            ally_builds = fight.get('ally_builds', [])
            
            if not ally_builds:
                continue
            
            # Check if already imported
            fight_date = fight.get('timestamp', '')
            Fight = Query()
            existing = guild_stats_table.search(
                (Fight.guild_id == guild_id) & 
                (Fight.fight_date == fight_date)
            )
            
            if existing:
                skipped_count += 1
                continue
            
            # Create guild fight record
            participants = []
            for ally in ally_builds:
                participants.append({
                    'account_id': ally.get('account', ''),
                    'account_name': ally.get('account', ally.get('player_name', '')),
                    'elite_spec': ally.get('elite_spec', ally.get('profession', '')),
                    'role': ally.get('role', 'dps'),
                    'damage_out': ally.get('damage_out', 0),
                    'deaths': ally.get('deaths', 0)
                })
            
            record = {
                'guild_id': guild_id,
                'guild_name': guild_name,
                'guild_tag': guild_tag,
                'fight_date': fight_date,
                'duration': int(fight.get('duration_sec', 0)),
                'outcome': fight.get('outcome', 'draw'),
                'ally_count': len(ally_builds),
                'enemy_count': sum(fight.get('enemy_composition', {}).values()),
                'total_damage': sum(p.get('damage_out', 0) for p in participants),
                'total_kills': fight.get('enemy_deaths', 0),
                'total_deaths': sum(p.get('deaths', 0) for p in participants),
                'participants': participants
            }
            
            guild_stats_table.insert(record)
            imported_count += 1
        
        logger.info(f"Imported {imported_count} fights for guild [{guild_tag}], skipped {skipped_count} duplicates")
        
        return {
            'success': True,
            'imported': imported_count,
            'skipped': skipped_count,
            'total_in_db': len(all_fights)
        }
        
    except Exception as e:
        logger.error(f"Failed to import guild fights: {e}")
        return {
            'success': False,
            'error': str(e),
            'imported': 0
        }
