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
    """Analyze multiple files for evening report"""
    session_id = str(uuid.uuid4())
    
    fight_results = []
    aggregated_composition = {
        'spec_counts': {},
        'role_counts': {'dps': 0, 'dps_strip': 0, 'healer': 0, 'stab': 0, 'boon': 0},
        'specs_by_role': {'dps': {}, 'dps_strip': {}, 'healer': {}, 'stab': {}, 'boon': {}},
        'total_players': 0
    }
    enemy_composition = {
        'spec_counts': {},
        'role_counts': {'dps': 0, 'dps_strip': 0, 'healer': 0, 'stab': 0, 'boon': 0},
        'total': 0
    }
    player_stats = {}
    map_counts = {}
    total_duration = 0
    victories = 0
    defeats = 0
    draws = 0
    parse_mode = "offline"
    
    dps_report_available = True
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            test_response = await client.get("https://dps.report/", timeout=5.0)
            dps_report_available = test_response.status_code == 200
        except:
            dps_report_available = False
            logger.info("dps.report unavailable, using OFFLINE mode")
        
        for filename, file_data in validated_files:
            players_data = None
            permalink = ""
            
            if dps_report_available:
                try:
                    upload_files = {"file": (filename, file_data)}
                    response = await client.post(
                        "https://dps.report/uploadContent",
                        files=upload_files,
                        data={"json": "1"}
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        permalink = result.get('permalink', '')
                        
                        if permalink:
                            json_url = f"https://dps.report/getJson?permalink={permalink}"
                            json_response = await client.get(json_url)
                            
                            if json_response.status_code == 200:
                                log_data = json_response.json()
                                if 'error' not in log_data:
                                    from main import extract_players_from_ei_json
                                    players_data = extract_players_from_ei_json(log_data)
                                    parse_mode = "online"
                except Exception as e:
                    logger.warning(f"dps.report failed for {filename}: {e}")
                    dps_report_available = False
            
            if players_data is None:
                try:
                    parsed_log = real_parser.parse_evtc_bytes(file_data, filename)
                    players_data = convert_parsed_log_to_players_data(parsed_log)
                    parse_mode = "offline"
                    logger.info(f"Offline parsed {filename}")
                except Exception as e:
                    logger.error(f"Failed to parse {filename}: {e}")
                    continue
            
            if not players_data:
                continue
            
            try:
                get_counter_service().record_fight(players_data, filename=filename, filesize=len(file_data))
            except Exception as e:
                logger.warning(f"record_fight failed for {filename}: {e}")
            
            outcome = players_data.get('fight_outcome', 'unknown')
            if outcome == 'victory':
                victories += 1
            elif outcome == 'defeat':
                defeats += 1
            elif outcome == 'draw':
                draws += 1
            
            fight_results.append({
                'filename': filename,
                'permalink': permalink,
                'fight_name': players_data.get('fight_name', 'Unknown'),
                'duration_sec': players_data.get('duration_sec', 0),
                'fight_outcome': outcome,
                'fight_stats': players_data.get('fight_stats', {}),
                'allies_count': len(players_data.get('allies', [])),
                'enemies_count': len(players_data.get('enemies', [])),
                'parse_mode': parse_mode
            })
            
            logger.info(f"Processed {filename}: {players_data.get('fight_name')} ({parse_mode})")
            
            total_duration += players_data.get('duration_sec', 0)
            
            comp = players_data.get('composition', {})
            if comp:
                for spec, count in comp.get('spec_counts', {}).items():
                    aggregated_composition['spec_counts'][spec] = aggregated_composition['spec_counts'].get(spec, 0) + count
                for role, count in comp.get('role_counts', {}).items():
                    aggregated_composition['role_counts'][role] = aggregated_composition['role_counts'].get(role, 0) + count
                aggregated_composition['total_players'] += comp.get('total_players', comp.get('total', 0) or 0)
            
            for ally in players_data.get('allies', []):
                role = ally.get('role', 'dps')
                spec = ally.get('elite_spec', ally.get('profession', 'Unknown'))
                if role not in aggregated_composition['specs_by_role']:
                    aggregated_composition['specs_by_role'][role] = {}
                aggregated_composition['specs_by_role'][role][spec] = aggregated_composition['specs_by_role'][role].get(spec, 0) + 1
            
            enemy_comp = players_data.get('enemy_composition', {})
            if enemy_comp:
                for spec, count in enemy_comp.get('spec_counts', {}).items():
                    enemy_composition['spec_counts'][spec] = enemy_composition['spec_counts'].get(spec, 0) + count
                for role, count in enemy_comp.get('role_counts', {}).items():
                    enemy_composition['role_counts'][role] = enemy_composition['role_counts'].get(role, 0) + count
                enemy_composition['total'] += enemy_comp.get('total', 0)
            
            # Build player aggregate for Top 10 (dedupe by account)
            seen_accounts = set()
            for ally in players_data.get('allies', []):
                account = ally.get('account') or ally.get('name', 'Unknown')
                if account in seen_accounts:
                    continue
                seen_accounts.add(account)
                if account not in player_stats:
                    player_stats[account] = {
                        'account': account,
                        'name': ally.get('name', account),
                        'spec': ally.get('elite_spec', ally.get('profession', 'Unknown')),
                        'damage': 0,
                        'kills': 0,
                        'deaths': 0,
                        'appearances': 0,
                    }
                player_stats[account]['damage'] += ally.get('damage_out', ally.get('damage', ally.get('dps', 0)))
                player_stats[account]['kills'] += ally.get('kills', 0)
                player_stats[account]['deaths'] += ally.get('deaths', 0)
                player_stats[account]['appearances'] += 1
    
    num_fights = len(fight_results)
    avg_players = (aggregated_composition['total_players'] // num_fights) if num_fights > 0 else 0
    unique_players = len(player_stats)
    top_players = sorted(
        [
            {
                'name': v.get('name', k),
                'spec': v.get('spec', 'Unknown'),
                'damage': v.get('damage', 0),
                'kills': v.get('kills', 0),
                'deaths': v.get('deaths', 0),
                'appearances': v.get('appearances', 0)
            }
            for k, v in player_stats.items()
        ],
        key=lambda x: x['damage'],
        reverse=True
    )[:10]
    
    return {
        "request": None,
        "session_id": session_id,
        "file_count": len(fight_results),
        "fights": fight_results,
        "stats": {
            'total_fights': len(fight_results),
            'victories': victories,
            'defeats': defeats,
            'draws': draws,
            'total_duration_min': round(total_duration / 60, 1),
            'avg_players': avg_players,
            'unique_players': unique_players,
        },
        "composition": aggregated_composition,
        "enemy_composition": enemy_composition,
        "map_counts": [],
        "top_players": top_players,
        "builds_by_class": {},
        "counter_recommendation": None,
        "parse_mode": parse_mode,
        "lang": lang,
        "t": get_all_translations(lang)
    }
