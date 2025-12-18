"""
Analysis service - Core business logic for fight analysis
Extracted from main.py for better organization
"""

from datetime import datetime
from typing import Dict, List, Tuple
import httpx
import uuid

from parser import RealEVTCParser
from services.counter_service import get_counter_service
from role_detector import estimate_role_from_profession
from translations import get_all_translations
from logger import get_logger

logger = get_logger('analysis_service')

# Initialize parser
real_parser = RealEVTCParser()


def is_player_afk(player) -> bool:
    damage = getattr(player, 'damage_dealt', 0) or 0
    healing = getattr(player, 'healing', 0) or 0
    damage_taken = getattr(player, 'damage_taken', 0) or 0
    kills = getattr(player, 'kills', 0) or 0
    subgroup = getattr(player, 'subgroup', 0) or 0
    if subgroup > 0:
        return False
    return damage == 0 and healing == 0 and damage_taken == 0 and kills == 0


def determine_fight_outcome(allies, enemies, duration_sec):
    """Determine fight outcome based on combat statistics"""
    if not allies or not enemies:
        return 'unknown'
    
    total_ally_deaths = sum(p.get('deaths', 0) for p in allies)
    total_ally_downs = sum(p.get('downs', 0) for p in allies)
    
    if duration_sec < 30:
        if total_ally_deaths == 0 and len(enemies) > 0:
            return 'victory'
        elif total_ally_deaths > len(allies) * 0.5:
            return 'defeat'
        return 'draw'
    
    death_ratio = total_ally_deaths / max(len(allies), 1)
    
    if death_ratio < 0.2:
        return 'victory'
    elif death_ratio > 0.6:
        return 'defeat'
    else:
        return 'draw'


def convert_parsed_log_to_players_data(parsed_log) -> dict:
    """Convert ParsedLog from local parser to players_data format used by templates."""
    allies = []
    allies_afk = []
    enemies = []
    
    for player in parsed_log.players:
        player_data = {
            'name': player.character_name,
            'account': player.account_name,
            'profession': player.elite_spec or player.profession,
            'elite_spec': player.elite_spec,
            'group': player.subgroup,
            'damage': player.damage_dealt,
            'dps': player.damage_dealt // max(parsed_log.duration_seconds, 1),
            'is_commander': False,
            'cleanses': 0,
            'cleanses_per_sec': 0,
            'resurrects': 0,
            'boon_strips': 0,
            'role': player.estimated_role.lower() if player.estimated_role else 'dps',
            'kills': player.kills,
            'deaths': player.deaths,
            'is_afk': is_player_afk(player),
            'in_squad': player.subgroup > 0,
        }
        
        if player_data['is_afk']:
            allies_afk.append(player_data)
        else:
            allies.append(player_data)
    
    for enemy in parsed_log.enemies:
        role = estimate_role_from_profession(enemy.elite_spec or enemy.profession)
        enemies.append({
            'name': enemy.character_name,
            'profession': enemy.elite_spec or enemy.profession,
            'damage_taken': enemy.damage_taken,
            'role': role,
        })
    
    # Build composition summaries
    spec_counts = {}
    role_counts = {'dps': 0, 'dps_strip': 0, 'healer': 0, 'stab': 0, 'boon': 0}
    
    for p in allies:
        spec = p['profession']
        spec_counts[spec] = spec_counts.get(spec, 0) + 1
        role = p.get('role', 'dps')
        if role in role_counts:
            role_counts[role] += 1
    
    enemy_spec_counts = {}
    enemy_role_counts = {'dps': 0, 'dps_strip': 0, 'healer': 0, 'stab': 0, 'boon': 0}
    
    for e in enemies:
        spec = e['profession']
        enemy_spec_counts[spec] = enemy_spec_counts.get(spec, 0) + 1
        role = e.get('role', 'dps')
        if role in enemy_role_counts:
            enemy_role_counts[role] += 1
    
    active_deaths = sum(p.get('deaths', 0) for p in allies)
    active_kills = sum(p.get('kills', 0) for p in allies)
    active_damage = sum(p.get('damage', 0) for p in allies)
    
    fight_outcome = determine_fight_outcome(allies, enemies, parsed_log.duration_seconds)
    
    return {
        'allies': allies,
        'allies_afk': allies_afk,
        'enemies': enemies,
        'fight_name': f"Fight - {parsed_log.duration_seconds}s",
        'duration_sec': parsed_log.duration_seconds,
        'fight_outcome': fight_outcome,
        'fight_stats': {
            'ally_deaths': active_deaths,
            'ally_kills': active_kills,
            'ally_damage': active_damage,
            'ally_downs': sum(p.get('downs', 0) for p in allies),
        },
        'composition': {
            'spec_counts': spec_counts,
            'role_counts': role_counts,
            'specs_by_role': {},
            'total_players': len(allies)
        },
        'enemy_composition': {
            'spec_counts': enemy_spec_counts,
            'role_counts': enemy_role_counts,
            'total': len(enemies)
        }
    }


async def analyze_dps_report_url(url: str, lang: str) -> dict:
    """Analyze a dps.report URL and return template data"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        json_url = f"https://dps.report/getJson?permalink={url}"
        response = await client.get(json_url)
        
        if response.status_code == 200 and response.text.strip().startswith('{'):
            log_data = response.json()
            from main import extract_players_from_ei_json
            players_data = extract_players_from_ei_json(log_data)
            
            players_data['source'] = 'dps_report'
            players_data['source_name'] = url
            get_counter_service().record_fight(players_data)
            
            enemy_spec_counts = players_data.get('enemy_composition', {}).get('spec_counts', {})
            ai_counter = await get_counter_service().generate_counter(enemy_spec_counts)
            
            return {
                "request": None,
                "data": log_data,
                "players": players_data,
                "ai_counter": ai_counter,
                "permalink": url,
                "filename": "dps.report URL",
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "parse_mode": "online",
                "lang": lang,
                "t": get_all_translations(lang)
            }
    
    raise Exception("Failed to fetch dps.report data")


async def analyze_single_file(filename: str, data: bytes, filesize: int, lang: str) -> dict:
    """Analyze a single EVTC file"""
    parse_mode = "offline"
    
    # Strategy 1: Try dps.report API first
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            upload_files = {'file': (filename, data)}
            response = await client.post(
                'https://dps.report/uploadContent',
                params={'json': '1', 'detailedwvw': 'true'},
                files=upload_files
            )
            
            if response.status_code == 200:
                result = response.json()
                permalink = result.get('permalink', '')
                
                if permalink:
                    json_url = f"https://dps.report/getJson?permalink={permalink}"
                    json_response = await client.get(json_url)
                    
                    if json_response.status_code == 200 and json_response.text.strip().startswith('{'):
                        log_data = json_response.json()
                        from main import extract_players_from_ei_json
                        players_data = extract_players_from_ei_json(log_data)
                        
                        players_data['source'] = 'dps_report'
                        players_data['source_name'] = permalink
                        get_counter_service().record_fight(players_data)
                        
                        enemy_spec_counts = players_data.get('enemy_composition', {}).get('spec_counts', {})
                        ai_counter = await get_counter_service().generate_counter(enemy_spec_counts)
                        
                        logger.info(f"dps.report success: {len(players_data['enemies'])} enemies")
                        
                        return {
                            "request": None,
                            "data": log_data,
                            "players": players_data,
                            "ai_counter": ai_counter,
                            "permalink": permalink,
                            "filename": filename,
                            "timestamp": datetime.now().strftime("%H:%M:%S"),
                            "parse_mode": "online",
                            "lang": lang,
                            "t": get_all_translations(lang)
                        }
    except Exception as api_error:
        logger.warning(f"dps.report unavailable: {api_error}")
    
    # Strategy 2: OFFLINE FALLBACK - Use local parser
    logger.info("Using OFFLINE mode with local parser")
    parsed_log = real_parser.parse_evtc_bytes(data, filename)
    
    players_data = convert_parsed_log_to_players_data(parsed_log)
    
    players_data['source'] = 'evtc'
    players_data['source_name'] = filename
    get_counter_service().record_fight(players_data, filename=filename, filesize=filesize)
    
    enemy_spec_counts = players_data.get('enemy_composition', {}).get('spec_counts', {})
    ai_counter = await get_counter_service().generate_counter(enemy_spec_counts)
    
    logger.info(f"Offline parse success: {len(parsed_log.players)} allies, {len(parsed_log.enemies)} enemies")
    
    return {
        "request": None,
        "data": {"fightName": f"Offline: {filename}", "duration": f"{parsed_log.duration_seconds}s"},
        "players": players_data,
        "ai_counter": ai_counter,
        "permalink": "",
        "filename": filename,
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "parse_mode": "offline",
        "lang": lang,
        "t": get_all_translations(lang)
    }


async def analyze_multiple_files(validated_files: List[Tuple[str, bytes]], lang: str) -> dict:
    """
    Analyze multiple EVTC/ZEVTC files and return aggregated statistics.
    
    Returns a single aggregated analysis with averaged metrics across all fights.
    """
    results = []
    errors = []
    
    for filename, data in validated_files:
        try:
            single_result = await analyze_single_file(filename, data, len(data), lang)
            results.append({
                "filename": filename,
                "data": single_result
            })
        except HTTPException as e:
            errors.append({"filename": filename, "detail": e.detail})
        except Exception as e:
            errors.append({"filename": filename, "detail": str(e)})
    
    if not results:
        return {
            "errors": errors,
            "summary": {},
            "aggregated_players": None,
            "lang": lang,
            "t": get_all_translations(lang)
        }
    
    # Aggregate statistics across all fights
    total_fights = len(results)
    victories = 0
    defeats = 0
    draws = 0
    total_duration_sec = 0
    unique_players = set()
    
    # Aggregated player data
    all_allies = {}  # account -> player data with aggregated stats
    all_enemies = {}  # name -> enemy data with aggregated stats
    all_allies_afk = {}
    
    # Composition aggregation
    ally_spec_counts = {}
    ally_role_counts = {'dps': 0, 'dps_strip': 0, 'healer': 0, 'stab': 0, 'boon': 0}
    enemy_spec_counts = {}
    enemy_role_counts = {'dps': 0, 'dps_strip': 0, 'healer': 0, 'stab': 0, 'boon': 0}
    
    # Fight stats aggregation
    total_ally_deaths = 0
    total_ally_kills = 0
    total_ally_damage = 0
    total_ally_downs = 0
    
    for item in results:
        players_data = item["data"]["players"]
        outcome = players_data.get("fight_outcome", "unknown")
        
        if outcome == "victory":
            victories += 1
        elif outcome == "defeat":
            defeats += 1
        elif outcome == "draw":
            draws += 1
        
        total_duration_sec += players_data.get("duration_sec", 0)
        
        # Aggregate allies (only squad members)
        for ally in players_data.get("allies", []):
            account = ally.get("account", "")
            in_squad = ally.get('in_squad', True)
            if account and in_squad:  # Only include squad members
                unique_players.add(account)
                if account not in all_allies:
                    all_allies[account] = {
                        'name': ally.get('name'),
                        'account': account,
                        'profession': ally.get('profession'),
                        'role': ally.get('role'),
                        'group': ally.get('group'),
                        'damage': 0,
                        'kills': 0,
                        'deaths': 0,
                        'downs': 0,
                        'is_commander': ally.get('is_commander', False),
                        'in_squad': True,
                        'fight_count': 0
                    }
                all_allies[account]['damage'] += ally.get('damage', 0)
                all_allies[account]['kills'] += ally.get('kills', 0)
                all_allies[account]['deaths'] += ally.get('deaths', 0)
                all_allies[account]['downs'] += ally.get('downs', 0)
                all_allies[account]['fight_count'] += 1
        
        # Aggregate AFK allies
        for ally_afk in players_data.get("allies_afk", []):
            account = ally_afk.get("account", ally_afk.get("name"))
            if account not in all_allies_afk:
                all_allies_afk[account] = ally_afk
        
        # Aggregate enemies
        for enemy in players_data.get("enemies", []):
            name = enemy.get('name')
            if name not in all_enemies:
                all_enemies[name] = {
                    'name': name,
                    'profession': enemy.get('profession'),
                    'role': enemy.get('role'),
                    'damage_taken': 0,
                    'fight_count': 0
                }
            all_enemies[name]['damage_taken'] += enemy.get('damage_taken', 0)
            all_enemies[name]['fight_count'] += 1
        
        # Aggregate compositions
        comp = players_data.get('composition', {})
        for spec, count in comp.get('spec_counts', {}).items():
            ally_spec_counts[spec] = ally_spec_counts.get(spec, 0) + count
        for role, count in comp.get('role_counts', {}).items():
            if role in ally_role_counts:
                ally_role_counts[role] += count
        
        enemy_comp = players_data.get('enemy_composition', {})
        for spec, count in enemy_comp.get('spec_counts', {}).items():
            enemy_spec_counts[spec] = enemy_spec_counts.get(spec, 0) + count
        for role, count in enemy_comp.get('role_counts', {}).items():
            if role in enemy_role_counts:
                enemy_role_counts[role] += count
        
        # Aggregate fight stats
        fight_stats = players_data.get('fight_stats', {})
        total_ally_deaths += fight_stats.get('ally_deaths', 0)
        total_ally_kills += fight_stats.get('ally_kills', 0)
        total_ally_damage += fight_stats.get('ally_damage', 0)
        total_ally_downs += fight_stats.get('ally_downs', 0)
    
    # Use TOTALS instead of averages for role counts
    total_ally_spec_counts = ally_spec_counts
    total_ally_role_counts = ally_role_counts
    total_enemy_spec_counts = enemy_spec_counts
    total_enemy_role_counts = enemy_role_counts
    
    # Build specs_by_role for allies
    ally_specs_by_role = {'dps': {}, 'dps_strip': {}, 'healer': {}, 'stab': {}, 'boon': {}}
    for account, ally_data in all_allies.items():
        role = ally_data.get('role', 'dps')
        spec = ally_data.get('profession')
        if role in ally_specs_by_role and spec:
            ally_specs_by_role[role][spec] = ally_specs_by_role[role].get(spec, 0) + 1
    
    # Build specs_by_role for enemies
    enemy_specs_by_role = {'dps': {}, 'dps_strip': {}, 'healer': {}, 'stab': {}, 'boon': {}}
    for name, enemy_data in all_enemies.items():
        role = enemy_data.get('role', 'dps')
        spec = enemy_data.get('profession')
        if role in enemy_specs_by_role and spec:
            enemy_specs_by_role[role][spec] = enemy_specs_by_role[role].get(spec, 0) + 1
    
    # Build per-fight enemy composition breakdown for detail view
    per_fight_enemy_breakdown = []
    for idx, item in enumerate(results):
        players_data = item["data"]["players"]
        enemy_comp = players_data.get('enemy_composition', {})
        per_fight_enemy_breakdown.append({
            'fight_number': idx + 1,
            'filename': item['filename'],
            'role_counts': enemy_comp.get('role_counts', {}),
            'total_enemies': enemy_comp.get('total', 0)
        })
    
    # Determine overall fight outcome
    if victories > defeats:
        overall_outcome = "victory"
    elif defeats > victories:
        overall_outcome = "defeat"
    else:
        overall_outcome = "draw"
    
    # Build aggregated players_data structure
    aggregated_players = {
        'allies': list(all_allies.values()),
        'allies_afk': list(all_allies_afk.values()),
        'enemies': list(all_enemies.values()),
        'fight_name': f"Aggregated Analysis ({total_fights} fights)",
        'duration_sec': total_duration_sec,
        'fight_outcome': overall_outcome,
        'fight_stats': {
            'ally_deaths': total_ally_deaths,
            'ally_kills': total_ally_kills,
            'ally_damage': total_ally_damage,
            'ally_downs': total_ally_downs,
        },
        'composition': {
            'spec_counts': total_ally_spec_counts,
            'role_counts': total_ally_role_counts,
            'specs_by_role': ally_specs_by_role,
            'total_players': len(all_allies)
        },
        'enemy_composition': {
            'spec_counts': total_enemy_spec_counts,
            'role_counts': total_enemy_role_counts,
            'specs_by_role': enemy_specs_by_role,
            'total': len(all_enemies),
            'per_fight_breakdown': per_fight_enemy_breakdown
        }
    }
    
    # Generate counter recommendation based on total enemy composition
    ai_counter = await get_counter_service().generate_counter(total_enemy_spec_counts)
    
    summary = {
        "total_fights": total_fights,
        "victories": victories,
        "defeats": defeats,
        "draws": draws,
        "total_duration_sec": total_duration_sec,
        "unique_players_count": len(unique_players)
    }
    
    return {
        "errors": errors,
        "summary": summary,
        "aggregated_players": aggregated_players,
        "ai_counter": ai_counter,
        "lang": lang,
        "t": get_all_translations(lang)
    }
