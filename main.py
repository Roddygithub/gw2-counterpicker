"""
GW2 CounterPicker - The Ultimate WvW Intelligence Tool
"Le seul outil capable de lire dans l'âme de ton adversaire. Et dans celle de tout son serveur."

v2.1 - Mode Offline activé - 100% indépendant de dps.report

Made with rage, love and 15 years of WvW pain.
"""

import os
import re
import uuid
import json
from datetime import datetime, timedelta
from typing import Optional, List
from pathlib import Path

from fastapi import FastAPI, Request, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import httpx

# TinyDB for persistent sessions
from tinydb import TinyDB, Query

from models import (
    AnalysisResult, PlayerBuild, CompositionAnalysis, 
    CounterRecommendation, EveningReport, HourlyEvolution,
    HeatmapData, TopPlayer
)
from parser import RealEVTCParser
from counter_engine import CounterPickEngine
from role_detector import (
    estimate_role_from_profession, 
    detect_role_advanced, 
    parse_duration_string,
    get_base_class,
    SPEC_TO_CLASS
)

app = FastAPI(
    title="GW2 CounterPicker",
    description="The most powerful WvW intelligence tool ever created - Now with offline mode!",
    version="2.1.0"
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")
templates.env.globals["app_version"] = app.version
templates.env.globals["offline_mode"] = True  # v2.1 feature flag

# Initialize engines
real_parser = RealEVTCParser()
counter_engine = CounterPickEngine()

# Persistent session storage with TinyDB
DB_PATH = Path("data")
DB_PATH.mkdir(exist_ok=True)
db = TinyDB(DB_PATH / "sessions.json")
sessions_table = db.table("sessions")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Main landing page - The gateway to victory"""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "title": "GW2 CounterPicker"
    })


@app.get("/analyze", response_class=HTMLResponse)
async def analyze_page(request: Request):
    """Single report analysis page"""
    return templates.TemplateResponse("analyze.html", {
        "request": request,
        "title": "Quick Analysis"
    })


@app.get("/evening", response_class=HTMLResponse)
async def evening_page(request: Request):
    """Full evening analysis page"""
    return templates.TemplateResponse("evening.html", {
        "request": request,
        "title": "Soirée Complète"
    })


@app.get("/meta", response_class=HTMLResponse)
async def meta_page(request: Request):
    """Meta 2025 page - Current trending builds"""
    meta_data = counter_engine.get_current_meta()
    return templates.TemplateResponse("meta.html", {
        "request": request,
        "title": "Meta 2025",
        "meta_data": meta_data
    })


@app.post("/api/analyze/url")
async def analyze_dps_report(request: Request, url: str = Form(...)):
    """
    Analyze a single dps.report URL
    Fetches JSON from dps.report API
    """
    # Validate URL
    if not url or "dps.report" not in url:
        raise HTTPException(status_code=400, detail="Invalid dps.report URL")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Extract permalink from URL and fetch JSON
            json_url = f"https://dps.report/getJson?permalink={url}"
            response = await client.get(json_url)
            
            if response.status_code == 200 and response.text.strip().startswith('{'):
                log_data = response.json()
                players_data = extract_players_from_ei_json(log_data)
                
                enemy_composition = build_composition_from_enemies(players_data['enemies'])
                counter = counter_engine.generate_counter(enemy_composition)
                
                return templates.TemplateResponse("partials/dps_report_result.html", {
                    "request": request,
                    "data": log_data,
                    "players": players_data,
                    "counter": counter,
                    "permalink": url,
                    "filename": "dps.report URL",
                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                    "parse_mode": "online"
                })
    except Exception as e:
        print(f"[URL] dps.report API failed: {e}")
    
    raise HTTPException(status_code=500, detail="Failed to fetch dps.report data")


@app.post("/api/analyze/evtc")
async def analyze_single_evtc(
    request: Request,
    file: UploadFile = File(...)
):
    """
    Analyze a single .evtc file
    Strategy: Try dps.report first, fallback to local parser if unavailable
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    valid_extensions = ['.evtc', '.zevtc', '.zip']
    if not any(file.filename.lower().endswith(ext) for ext in valid_extensions):
        raise HTTPException(status_code=400, detail="Invalid file type. Use .evtc, .zevtc, or .zip")
    
    data = await file.read()
    print(f"[EVTC] Received file: {file.filename}, size: {len(data)} bytes")
    
    parse_mode = "offline"  # Default to offline
    
    # Strategy 1: Try dps.report API first
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            files = {'file': (file.filename, data)}
            response = await client.post(
                'https://dps.report/uploadContent',
                params={'json': '1', 'detailedwvw': 'true'},
                files=files
            )
            
            if response.status_code == 200:
                result = response.json()
                permalink = result.get('permalink', '')
                
                if permalink:
                    json_url = f"https://dps.report/getJson?permalink={permalink}"
                    json_response = await client.get(json_url)
                    
                    if json_response.status_code == 200 and json_response.text.strip().startswith('{'):
                        log_data = json_response.json()
                        players_data = extract_players_from_ei_json(log_data)
                        enemy_composition = build_composition_from_enemies(players_data['enemies'])
                        counter = counter_engine.generate_counter(enemy_composition)
                        
                        print(f"[EVTC] dps.report success: {len(players_data['enemies'])} enemies")
                        
                        return templates.TemplateResponse("partials/dps_report_result.html", {
                            "request": request,
                            "data": log_data,
                            "players": players_data,
                            "counter": counter,
                            "permalink": permalink,
                            "filename": file.filename,
                            "timestamp": datetime.now().strftime("%H:%M:%S"),
                            "parse_mode": "online"
                        })
    except Exception as api_error:
        print(f"[EVTC] dps.report unavailable: {api_error}")
    
    # Strategy 2: OFFLINE FALLBACK - Use local parser
    print(f"[EVTC] Using OFFLINE mode with local parser")
    try:
        parsed_log = real_parser.parse_evtc_bytes(data, file.filename)
        
        # Convert parsed log to players_data format
        players_data = convert_parsed_log_to_players_data(parsed_log)
        enemy_composition = build_composition_from_enemies(players_data['enemies'])
        counter = counter_engine.generate_counter(enemy_composition)
        
        print(f"[EVTC] Offline parse success: {len(parsed_log.players)} allies, {len(parsed_log.enemies)} enemies")
        
        return templates.TemplateResponse("partials/dps_report_result.html", {
            "request": request,
            "data": {"fightName": f"Offline: {file.filename}", "duration": f"{parsed_log.duration_seconds}s"},
            "players": players_data,
            "counter": counter,
            "permalink": "",
            "filename": file.filename,
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "parse_mode": "offline"
        })
    except Exception as parse_error:
        print(f"[EVTC] Local parser failed: {parse_error}")
        raise HTTPException(status_code=500, detail=f"Failed to parse file: {str(parse_error)}")


def convert_parsed_log_to_players_data(parsed_log) -> dict:
    """Convert ParsedLog from local parser to players_data format used by templates."""
    allies = []
    enemies = []
    
    for player in parsed_log.players:
        allies.append({
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
        })
    
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
    
    return {
        'allies': allies,
        'enemies': sorted(enemies, key=lambda x: x.get('damage_taken', 0), reverse=True)[:20],
        'fight_name': f"WvW Combat ({parsed_log.duration_seconds}s)",
        'duration_sec': parsed_log.duration_seconds,
        'fight_outcome': 'unknown',
        'fight_stats': {
            'ally_deaths': sum(p.deaths for p in parsed_log.players),
            'ally_downs': sum(p.downs for p in parsed_log.players),
            'ally_damage': sum(p.damage_dealt for p in parsed_log.players),
            'enemy_damage_taken': sum(e.damage_taken for e in parsed_log.enemies)
        },
        'composition': {
            'spec_counts': spec_counts,
            'role_counts': role_counts,
            'specs_by_role': {},
            'total': len(allies)
        },
        'enemy_composition': {
            'spec_counts': enemy_spec_counts,
            'role_counts': enemy_role_counts,
            'specs_by_role': {},
            'total': len(enemies)
        }
    }


def build_composition_from_enemies(enemies: list) -> CompositionAnalysis:
    """Build a CompositionAnalysis from enemy player data for counter generation"""
    builds = []
    spec_counts = {}
    role_distribution = {}
    
    for enemy in enemies:
        # Extract profession from name (e.g., "Tempest pl-4073" -> "Tempest")
        name = enemy.get('name', 'Unknown')
        profession = enemy.get('profession', 'Unknown')
        
        # Try to get spec from name if profession is Unknown
        if profession == 'Unknown' and ' ' in name:
            profession = name.split(' ')[0]
        
        build = PlayerBuild(
            player_name=name,
            account_name="",
            profession=profession,
            elite_spec=profession,
            role="Unknown",
            weapons=[],
            is_commander=False,
            damage_dealt=0,
            healing_done=0,
            deaths=0,
            kills=0
        )
        builds.append(build)
        
        # Count specs
        spec_counts[profession] = spec_counts.get(profession, 0) + 1
    
    return CompositionAnalysis(
        builds=builds,
        spec_counts=spec_counts,
        role_distribution=role_distribution,
        total_players=len(enemies),
        confidence=0.7,
        source="dps.report WvW"
    )


def extract_players_from_ei_json(data: dict) -> dict:
    """Extract player information from Elite Insights JSON"""

    def safe_number(value):
        """Convert nested EI values (lists/dicts) to a numeric scalar"""
        if isinstance(value, (int, float)):
            return value
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                return 0
        if isinstance(value, dict):
            for key in ('damage', 'totalDamage', 'value', 'amount', 'damageTaken'):
                if key in value:
                    return safe_number(value[key])
            return 0
        if isinstance(value, list) and value:
            return safe_number(value[0])
        return 0

    # Get fight duration using centralized parser
    duration_sec = parse_duration_string(data.get('duration', '0'))

    players = []

    for player in data.get('players', []):
        # Filter out non-squad allies (names like "Profession pl-XXXX")
        player_name = player.get('name', 'Unknown')
        if ' pl-' in player_name:
            continue  # Skip non-squad allies
        
        dps_entries = player.get('dpsAll', [])
        damage_value = safe_number(dps_entries)
        
        # Extract support stats (cleanses, resurrects, boon strips)
        support_data = player.get('support', [{}])
        support = support_data[0] if support_data else {}
        condi_cleanse = support.get('condiCleanse', 0)
        condi_cleanse_self = support.get('condiCleanseSelf', 0)
        resurrects = support.get('resurrects', 0)
        boon_strips = support.get('boonStrips', 0)
        
        # Extract healing stats (requires ArcDPS healing extension)
        healing = 0
        if 'extHealingStats' in player:
            heal_stats = player['extHealingStats']
            if 'outgoingHealing' in heal_stats:
                oh = heal_stats['outgoingHealing']
                if oh and isinstance(oh, list) and len(oh) > 0:
                    if isinstance(oh[0], dict):
                        healing = oh[0].get('healing', 0)
                    elif isinstance(oh[0], (int, float)):
                        healing = oh[0]
        
        # Extract barrier stats
        barrier = 0
        if 'extBarrierStats' in player:
            barrier_stats = player['extBarrierStats']
            if 'outgoingBarrier' in barrier_stats:
                ob = barrier_stats['outgoingBarrier']
                if ob and isinstance(ob, list) and len(ob) > 0:
                    if isinstance(ob[0], dict):
                        barrier = ob[0].get('barrier', 0)
                    elif isinstance(ob[0], (int, float)):
                        barrier = ob[0]
        
        # Extract down contribution and other stats
        down_contrib = 0
        stats_all = player.get('statsAll', [{}])
        if stats_all and len(stats_all) > 0:
            stats = stats_all[0] if isinstance(stats_all[0], dict) else {}
            down_contrib = stats.get('downContribution', 0)
        
        # Extract stability generation from groupBuffs (buff id 1122)
        stab_gen = 0
        for buff in player.get('groupBuffs', []):
            if buff.get('id') == 1122:  # Stability buff ID
                buff_data = buff.get('buffData', [{}])
                if buff_data and len(buff_data) > 0:
                    stab_gen = buff_data[0].get('generation', 0)
                break
        
        # Calculate per-second values
        cleanses_per_sec = round(condi_cleanse / duration_sec, 2) if duration_sec > 0 else 0
        
        profession = player.get('profession', 'Unknown')
        
        # Use advanced role detection with all stats
        role_stats = {
            'healing': healing,
            'stab_gen': stab_gen,
            'cleanses_per_sec': cleanses_per_sec,
            'strips': boon_strips,
            'down_contrib': down_contrib,
            'barrier': barrier,
            'duration': duration_sec
        }
        role = detect_role_advanced(profession, role_stats)
        
        players.append({
            'name': player.get('name', 'Unknown'),
            'account': player.get('account', ''),
            'profession': profession,
            'group': player.get('group', 0),
            'damage': int(damage_value),
            'is_commander': player.get('hasCommanderTag', False),
            'cleanses': condi_cleanse,
            'cleanses_self': condi_cleanse_self,
            'cleanses_per_sec': cleanses_per_sec,
            'resurrects': resurrects,
            'boon_strips': boon_strips,
            'role': role,
        })

    # Get targets (enemies in WvW)
    enemies = []
    for target in data.get('targets', []):
        if target.get('enemyPlayer', False):
            damage_taken = safe_number(target.get('totalDamageTaken', 0))
            raw_name = target.get('name', 'Unknown')
            profession_guess = raw_name.split(' ')[0] if raw_name and ' ' in raw_name else 'Unknown'
            # Estimate enemy role based on profession
            enemy_role = estimate_role_from_profession(profession_guess)
            enemies.append({
                'name': raw_name,
                'profession': profession_guess,
                'damage_taken': int(damage_taken),
                'role': enemy_role,
            })

    enemies_sorted = sorted(enemies, key=lambda e: e['damage_taken'], reverse=True)[:20]

    # Calculate composition summary
    spec_counts = {}
    role_counts = {'dps': 0, 'dps_strip': 0, 'healer': 0, 'stab': 0, 'boon': 0}
    specs_by_role = {'dps': {}, 'dps_strip': {}, 'healer': {}, 'stab': {}, 'boon': {}}
    
    for p in players:
        spec = p['profession']
        spec_counts[spec] = spec_counts.get(spec, 0) + 1
        role = p['role']
        if role in role_counts:
            role_counts[role] += 1
            specs_by_role[role][spec] = specs_by_role[role].get(spec, 0) + 1
        else:
            role_counts['dps'] += 1
            specs_by_role['dps'][spec] = specs_by_role['dps'].get(spec, 0) + 1

    # Calculate fight outcome metrics
    total_ally_deaths = 0
    total_ally_downs = 0
    total_ally_damage = 0
    for p in players:
        total_ally_damage += p.get('damage', 0)
    
    # Get ally deaths/downs from original data
    for player in data.get('players', []):
        player_name = player.get('name', '')
        if ' pl-' in player_name:
            continue
        defenses = player.get('defenses', [{}])
        d = defenses[0] if defenses else {}
        total_ally_deaths += d.get('deadCount', 0)
        total_ally_downs += d.get('downCount', 0)
    
    # Calculate enemy damage taken (approximate kills)
    total_enemy_damage_taken = sum(e.get('damage_taken', 0) for e in enemies_sorted)
    
    # Determine fight outcome based on metrics
    # Win if: more damage dealt than deaths * 100k (rough heuristic)
    # Or if enemy damage taken is significantly higher than ally deaths
    if len(players) == 0:
        fight_outcome = 'unknown'
    elif total_ally_deaths == 0 and total_enemy_damage_taken > 0:
        fight_outcome = 'victory'
    elif total_ally_deaths <= 2 and total_enemy_damage_taken > total_ally_damage * 0.3:
        fight_outcome = 'victory'
    elif total_ally_deaths >= len(players) * 0.5:
        fight_outcome = 'defeat'
    elif total_ally_deaths >= 5 and total_enemy_damage_taken < total_ally_damage * 0.2:
        fight_outcome = 'defeat'
    else:
        # Close fight - use ratio
        if total_enemy_damage_taken > 0 and total_ally_deaths < 3:
            fight_outcome = 'victory'
        elif total_ally_deaths > 3:
            fight_outcome = 'defeat'
        else:
            fight_outcome = 'draw'

    # Calculate enemy composition summary with roles
    enemy_spec_counts = {}
    enemy_role_counts = {'dps': 0, 'dps_strip': 0, 'healer': 0, 'stab': 0, 'boon': 0}
    enemy_specs_by_role = {'dps': {}, 'dps_strip': {}, 'healer': {}, 'stab': {}, 'boon': {}}
    
    for e in enemies_sorted:
        spec = e.get('profession', 'Unknown')
        role = e.get('role', 'dps')
        enemy_spec_counts[spec] = enemy_spec_counts.get(spec, 0) + 1
        if role in enemy_role_counts:
            enemy_role_counts[role] += 1
            enemy_specs_by_role[role][spec] = enemy_specs_by_role[role].get(spec, 0) + 1
        else:
            enemy_role_counts['dps'] += 1
            enemy_specs_by_role['dps'][spec] = enemy_specs_by_role['dps'].get(spec, 0) + 1
    
    # Sort enemy specs by count
    enemy_spec_counts_sorted = dict(sorted(enemy_spec_counts.items(), key=lambda x: x[1], reverse=True))

    return {
        'allies': players,
        'enemies': enemies_sorted,
        'fight_name': data.get('fightName', data.get('name', 'Unknown')),
        'duration_sec': round(duration_sec, 1),
        'fight_outcome': fight_outcome,
        'fight_stats': {
            'ally_deaths': total_ally_deaths,
            'ally_downs': total_ally_downs,
            'ally_damage': total_ally_damage,
            'enemy_damage_taken': total_enemy_damage_taken
        },
        'composition': {
            'spec_counts': spec_counts,
            'role_counts': role_counts,
            'specs_by_role': specs_by_role,
            'total': len(players)
        },
        'enemy_composition': {
            'spec_counts': enemy_spec_counts_sorted,
            'role_counts': enemy_role_counts,
            'specs_by_role': enemy_specs_by_role,
            'total': len(enemies_sorted)
        }
    }


@app.post("/api/analyze/files")
async def analyze_evening_files(
    request: Request,
    files: List[UploadFile] = File(...)
):
    """
    Analyze multiple .evtc/.zip files for full evening analysis
    Strategy: Try dps.report first, fallback to local parser if unavailable
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")
    
    if len(files) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 files allowed")
    
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
    parse_mode = "offline"  # Track which mode was used
    
    # Try dps.report first, then fallback to local parser
    dps_report_available = True
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Quick check if dps.report is available
        try:
            test_response = await client.get("https://dps.report/", timeout=5.0)
            dps_report_available = test_response.status_code == 200
        except:
            dps_report_available = False
            print("[Evening] dps.report unavailable, using OFFLINE mode")
        
        for f in files:
            file_data = await f.read()
            players_data = None
            permalink = ""
            
            # Strategy 1: Try dps.report if available
            if dps_report_available:
                try:
                    upload_files = {"file": (f.filename, file_data)}
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
                                    players_data = extract_players_from_ei_json(log_data)
                                    parse_mode = "online"
                except Exception as e:
                    print(f"[Evening] dps.report failed for {f.filename}: {e}")
                    dps_report_available = False  # Switch to offline for remaining files
            
            # Strategy 2: OFFLINE FALLBACK - Use local parser
            if players_data is None:
                try:
                    parsed_log = real_parser.parse_evtc_bytes(file_data, f.filename)
                    players_data = convert_parsed_log_to_players_data(parsed_log)
                    parse_mode = "offline"
                    print(f"[Evening] Offline parsed {f.filename}")
                except Exception as e:
                    print(f"[Evening] Failed to parse {f.filename}: {e}")
                    continue
            
            if not players_data:
                continue
            
            # Aggregate composition data
            if players_data.get('composition'):
                comp = players_data['composition']
                for spec, count in comp.get('spec_counts', {}).items():
                    aggregated_composition['spec_counts'][spec] = aggregated_composition['spec_counts'].get(spec, 0) + count
                for role, count in comp.get('role_counts', {}).items():
                    aggregated_composition['role_counts'][role] = aggregated_composition['role_counts'].get(role, 0) + count
                for role, specs in comp.get('specs_by_role', {}).items():
                    for spec, count in specs.items():
                        aggregated_composition['specs_by_role'][role][spec] = aggregated_composition['specs_by_role'][role].get(spec, 0) + count
                aggregated_composition['total_players'] += comp.get('total', 0)
            
            # Aggregate enemy composition
            if players_data.get('enemy_composition'):
                enemy_comp = players_data['enemy_composition']
                for spec, count in enemy_comp.get('spec_counts', {}).items():
                    enemy_composition['spec_counts'][spec] = enemy_composition['spec_counts'].get(spec, 0) + count
                for role, count in enemy_comp.get('role_counts', {}).items():
                    enemy_composition['role_counts'][role] = enemy_composition['role_counts'].get(role, 0) + count
                enemy_composition['total'] += enemy_comp.get('total', 0)
            
            # Track player stats for top 10
            for ally in players_data.get('allies', []):
                name = ally.get('name', 'Unknown')
                if name not in player_stats:
                    player_stats[name] = {
                        'spec': ally.get('elite_spec', ally.get('profession', 'Unknown')),
                        'damage': 0,
                        'kills': 0,
                        'deaths': 0,
                        'appearances': 0
                    }
                player_stats[name]['damage'] += ally.get('dps', 0) * players_data.get('duration_sec', 0)
                player_stats[name]['kills'] += ally.get('kills', 0)
                player_stats[name]['deaths'] += ally.get('deaths', 0)
                player_stats[name]['appearances'] += 1
            
            # Track map/zone
            fight_name = players_data.get('fight_name', 'Unknown')
            map_counts[fight_name] = map_counts.get(fight_name, 0) + 1
            
            total_duration += players_data.get('duration_sec', 0)
            
            # Track wins/losses
            outcome = players_data.get('fight_outcome', 'unknown')
            if outcome == 'victory':
                victories += 1
            elif outcome == 'defeat':
                defeats += 1
            
            fight_results.append({
                'filename': f.filename,
                'permalink': permalink,
                'fight_name': players_data.get('fight_name', 'Unknown'),
                'duration_sec': players_data.get('duration_sec', 0),
                'fight_outcome': outcome,
                'fight_stats': players_data.get('fight_stats', {}),
                'allies_count': len(players_data.get('allies', [])),
                'enemies_count': len(players_data.get('enemies', [])),
                'parse_mode': parse_mode
            })
            
            print(f"[Evening] Processed {f.filename}: {players_data.get('fight_name')} ({parse_mode})")
    
    # Calculate averages
    num_fights = len(fight_results)
    if num_fights > 0:
        avg_players = aggregated_composition['total_players'] // num_fights
        avg_duration = total_duration / num_fights
    else:
        avg_players = 0
        avg_duration = 0
    
    # Calculate top 10 players by damage
    top_players = sorted(
        [{'name': name, **stats} for name, stats in player_stats.items()],
        key=lambda x: x['damage'],
        reverse=True
    )[:10]
    
    # Calculate most played build per class (use centralized SPEC_TO_CLASS)
    class_to_specs = {}
    for spec, count in aggregated_composition['spec_counts'].items():
        base_class = get_base_class(spec)
        if base_class not in class_to_specs:
            class_to_specs[base_class] = {}
        class_to_specs[base_class][spec] = count
    
    # Get most played spec per class
    builds_by_class = {}
    for base_class, specs in class_to_specs.items():
        if specs:
            top_spec = max(specs.items(), key=lambda x: x[1])
            builds_by_class[base_class] = {'spec': top_spec[0], 'count': top_spec[1]}
    
    # Sort maps by frequency
    sorted_maps = sorted(map_counts.items(), key=lambda x: x[1], reverse=True)
    
    # Generate counter recommendation for next session
    counter_recommendation = None
    if enemy_composition['spec_counts']:
        # Find dominant enemy spec
        dominant_enemy = max(enemy_composition['spec_counts'].items(), key=lambda x: x[1])
        counter_recommendation = {
            'target': dominant_enemy[0],
            'count': dominant_enemy[1],
            'suggestion': f"Ramenez plus de Spellbreaker/Scourge pour strip leurs {dominant_enemy[0]}"
        }
    
    # Build stats dict
    stats = {
        "total_fights": num_fights,
        "total_duration_min": round(total_duration / 60, 1),
        "avg_duration_sec": round(avg_duration, 1),
        "avg_players": avg_players,
        "victories": victories,
        "defeats": defeats,
        "parse_mode": parse_mode
    }
    
    # Store session in TinyDB for persistence
    session_data = {
        "session_id": session_id,
        "fights": fight_results,
        "composition": aggregated_composition,
        "enemy_composition": enemy_composition,
        "stats": stats,
        "top_players": top_players,
        "builds_by_class": builds_by_class,
        "map_counts": sorted_maps,
        "counter_recommendation": counter_recommendation,
        "created_at": datetime.now().isoformat()
    }
    sessions_table.insert(session_data)
    
    return templates.TemplateResponse("partials/evening_result_v2.html", {
        "request": request,
        "fights": fight_results,
        "composition": aggregated_composition,
        "enemy_composition": enemy_composition,
        "stats": stats,
        "session_id": session_id,
        "file_count": len(files),
        "top_players": top_players,
        "builds_by_class": builds_by_class,
        "map_counts": sorted_maps,
        "counter_recommendation": counter_recommendation,
        "parse_mode": parse_mode
    })


@app.get("/api/report/{session_id}/pdf")
async def download_pdf_report(session_id: str):
    """Download Night Intelligence Report as PDF"""
    Session = Query()
    result = sessions_table.search(Session.session_id == session_id)
    
    if not result:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = result[0]
    
    # PDF generation would need the session data
    # For now, return a simple error as PDF gen needs refactoring
    raise HTTPException(status_code=501, detail="PDF export coming soon in v2.2")


@app.get("/api/share/{session_id}")
async def get_shared_report(request: Request, session_id: str):
    """View a shared evening report"""
    Session = Query()
    result = sessions_table.search(Session.session_id == session_id)
    
    if not result:
        raise HTTPException(status_code=404, detail="Report not found")
    
    session = result[0]
    
    return templates.TemplateResponse("shared_report.html", {
        "request": request,
        "session": session,
        "session_id": session_id
    })


@app.get("/health")
async def health_check():
    """Health check endpoint for deployment"""
    return {"status": "operational", "message": "GW2 CounterPicker is ready for war"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
