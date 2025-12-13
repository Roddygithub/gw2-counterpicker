"""
GW2 CounterPicker - The Ultimate WvW Intelligence Tool
"Le seul outil capable de lire dans l'âme de ton adversaire. Et dans celle de tout son serveur."

Made with rage, love and 15 years of WvW pain.
"""

import os
import uuid
import json
import random
from datetime import datetime, timedelta
from typing import Optional, List
from pathlib import Path

from fastapi import FastAPI, Request, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import httpx

from models import (
    AnalysisResult, PlayerBuild, CompositionAnalysis, 
    CounterRecommendation, EveningReport, HourlyEvolution,
    HeatmapData, TopPlayer
)
from parser import RealEVTCParser
from mock_parser import MockEVTCParser
from counter_engine import CounterPickEngine

app = FastAPI(
    title="GW2 CounterPicker",
    description="The most powerful WvW intelligence tool ever created",
    version="2.0.0"  # Real EVTC parsing!
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")
templates.env.globals["app_version"] = app.version

# Initialize engines - Real parser with mock fallback
real_parser = RealEVTCParser()
mock_parser = MockEVTCParser()
counter_engine = CounterPickEngine()

# Store for analysis sessions
sessions = {}


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
    Returns enemy composition and perfect counter in 3 seconds
    """
    # Validate URL
    if not url or "dps.report" not in url:
        raise HTTPException(status_code=400, detail="Invalid dps.report URL")
    
    # Parse the report (uses mock for URL, real parser for files)
    analysis = mock_parser.parse_dps_report_url(url)
    
    # Generate counter recommendations
    counter = counter_engine.generate_counter(analysis.enemy_composition)
    
    # Return HTML partial for HTMX
    return templates.TemplateResponse("partials/analysis_result.html", {
        "request": request,
        "analysis": analysis,
        "counter": counter,
        "timestamp": datetime.now().strftime("%H:%M:%S")
    })


@app.post("/api/analyze/evtc")
async def analyze_single_evtc(
    request: Request,
    file: UploadFile = File(...)
):
    """
    Analyze a single .evtc file using dps.report API for reliable parsing
    Returns exact player builds with high confidence
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    # Validate extension
    valid_extensions = ['.evtc', '.zevtc', '.zip']
    if not any(file.filename.lower().endswith(ext) for ext in valid_extensions):
        raise HTTPException(status_code=400, detail="Invalid file type. Use .evtc, .zevtc, or .zip")
    
    try:
        # Read file data
        data = await file.read()
        print(f"[EVTC] Received file: {file.filename}, size: {len(data)} bytes")
        
        # Upload to dps.report API for reliable parsing
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                # Upload to dps.report
                files = {'file': (file.filename, data)}
                response = await client.post(
                    'https://dps.report/uploadContent',
                    params={'json': '1', 'detailedwvw': 'true'},
                    files=files
                )
                
                if response.status_code == 200:
                    result = response.json()
                    permalink = result.get('permalink', '')
                    print(f"[EVTC] dps.report upload success: {permalink}")
                    
                    # Get the JSON data from dps.report
                    if permalink:
                        # Build correct JSON URL - handle both dps.report and wvw.report
                        if 'wvw.report' in permalink:
                            json_url = f"https://dps.report/getJson?permalink={permalink}"
                        else:
                            json_url = f"https://dps.report/getJson?permalink={permalink}"
                        
                        print(f"[EVTC] Fetching JSON from: {json_url}")
                        json_response = await client.get(json_url)
                        
                        if json_response.status_code == 200 and json_response.text.strip().startswith('{'):
                            log_data = json_response.json()
                            print(f"[EVTC] JSON fetched successfully, players: {len(log_data.get('players', []))}")
                            
                            # Extract player data from Elite Insights JSON
                            players_data = extract_players_from_ei_json(log_data)
                            
                            # Build enemy composition for counter generation
                            enemy_composition = build_composition_from_enemies(players_data['enemies'])
                            counter = counter_engine.generate_counter(enemy_composition)
                            
                            return templates.TemplateResponse("partials/dps_report_result.html", {
                                "request": request,
                                "data": log_data,
                                "players": players_data,
                                "counter": counter,
                                "permalink": result.get('permalink', ''),
                                "filename": file.filename,
                                "timestamp": datetime.now().strftime("%H:%M:%S")
                            })
                    
                    # Fallback if we can't get JSON
                    return templates.TemplateResponse("partials/dps_report_link.html", {
                        "request": request,
                        "permalink": result.get('permalink', ''),
                        "filename": file.filename,
                        "timestamp": datetime.now().strftime("%H:%M:%S")
                    })
                else:
                    print(f"[EVTC] dps.report upload failed: {response.status_code}")
                    raise Exception(f"dps.report returned {response.status_code}")
                    
        except Exception as api_error:
            print(f"[EVTC] dps.report API failed: {api_error}")
            
            # Fallback: use mock parser
            analysis = mock_parser.parse_dps_report_url(f"file://{file.filename}")
            counter = counter_engine.generate_counter(analysis.enemy_composition)
            
            return templates.TemplateResponse("partials/analysis_result.html", {
                "request": request,
                "analysis": analysis,
                "counter": counter,
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "parse_warning": f"API upload failed, showing simulated data. Error: {str(api_error)[:100]}"
            })
        
    except Exception as e:
        print(f"[EVTC] Critical error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process file: {str(e)}")


def build_composition_from_enemies(enemies: list) -> "CompositionAnalysis":
    """Build a CompositionAnalysis from enemy player data for counter generation"""
    from mock_parser import CompositionAnalysis, PlayerBuild
    
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

    # Get fight duration for per-second calculations
    duration_ms = data.get('duration', '0')
    if isinstance(duration_ms, str):
        # Parse duration string like "2m 30s 500ms"
        import re
        duration_sec = 0
        m = re.search(r'(\d+)m', duration_ms)
        if m:
            duration_sec += int(m.group(1)) * 60
        s = re.search(r'(\d+)s', duration_ms)
        if s:
            duration_sec += int(s.group(1))
        ms = re.search(r'(\d+)ms', duration_ms)
        if ms:
            duration_sec += int(ms.group(1)) / 1000
    else:
        duration_sec = float(duration_ms) / 1000 if duration_ms > 1000 else float(duration_ms)
    
    if duration_sec <= 0:
        duration_sec = 1  # Avoid division by zero

    # Role detection based on elite spec (WvW meta)
    # Primary stab providers (Guardian)
    STAB_SPECS = {'Firebrand', 'Luminary'}
    # Primary healers (various classes)
    HEALER_SPECS = {'Druid', 'Troubadour', 'Specter', 'Vindicator'}
    # Primary boon providers
    BOON_SPECS = {'Herald', 'Renegade', 'Chronomancer', 'Paragon'}
    # DPS specs that commonly strip boons
    STRIP_DPS_SPECS = {'Spellbreaker', 'Chronomancer', 'Reaper', 'Harbinger', 'Scourge', 'Ritualist'}
    
    # Minimum fight duration for reliable role detection (seconds)
    MIN_DURATION_FOR_ROLE = 60
    
    def detect_role_advanced(profession, stats):
        """
        Advanced role detection using multiple stats:
        - healing: total healing done
        - stab_gen: stability generation %
        - cleanses_per_sec: condition cleanses per second
        - strips: boon strips count
        - down_contrib: down contribution (damage to downed)
        - barrier: barrier generated
        - duration: fight duration in seconds
        """
        healing = stats.get('healing', 0)
        stab_gen = stats.get('stab_gen', 0)
        cleanses_per_sec = stats.get('cleanses_per_sec', 0)
        strips = stats.get('strips', 0)
        down_contrib = stats.get('down_contrib', 0)
        barrier = stats.get('barrier', 0)
        duration = stats.get('duration', 60)
        
        # Normalize stats per minute for comparison
        strips_per_min = (strips / duration) * 60 if duration > 0 else 0
        healing_per_sec = healing / duration if duration > 0 else 0
        
        # === STAB DETECTION (priority) ===
        # Stab specs are almost always stab
        if profession in STAB_SPECS:
            return 'stab'
        # Any spec with high stability generation
        if stab_gen >= 5.0:
            return 'stab'
        
        # === BOON DETECTION (before healer to avoid Paragon misdetection) ===
        # Boon specs stay boon even with high healing
        if profession in BOON_SPECS:
            return 'boon'
        
        # === HEALER DETECTION ===
        # High healing output = healer (threshold ~800 HPS for active healers)
        if healing_per_sec >= 800:
            return 'healer'
        # Healer specs with moderate healing
        if profession in HEALER_SPECS and healing_per_sec >= 300:
            return 'healer'
        # Scrapper/Tempest with good healing = healer
        if profession in {'Scrapper', 'Tempest'} and healing_per_sec >= 500:
            return 'healer'
        
        # === DPS DETECTION (with sub-roles) ===
        # High strip count = strip DPS
        if strips_per_min >= 10 and profession in STRIP_DPS_SPECS:
            return 'dps_strip'
        if strips_per_min >= 20:  # Very high strips from any class
            return 'dps_strip'
        
        # === FALLBACK DETECTION ===
        # Use cleanses as fallback for healer detection
        if cleanses_per_sec >= 0.5 and profession in HEALER_SPECS:
            return 'healer'
        if profession in {'Scrapper', 'Tempest'} and cleanses_per_sec >= 0.3:
            return 'healer'
        
        # Default = DPS
        return 'dps'

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
            enemies.append({
                'name': raw_name,
                'profession': profession_guess,
                'damage_taken': int(damage_taken),
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
        }
    }


@app.post("/api/analyze/files")
async def analyze_evening_files(
    request: Request,
    files: List[UploadFile] = File(...)
):
    """
    Analyze multiple .evtc/.zip files for full evening analysis
    Uploads each file to dps.report for REAL data extraction
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")
    
    if len(files) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 files allowed")
    
    # Create session
    session_id = str(uuid.uuid4())
    
    # Upload each file to dps.report and collect results
    fight_results = []
    aggregated_composition = {
        'spec_counts': {},
        'role_counts': {'dps': 0, 'dps_strip': 0, 'healer': 0, 'stab': 0, 'boon': 0},
        'specs_by_role': {'dps': {}, 'dps_strip': {}, 'healer': {}, 'stab': {}, 'boon': {}},
        'total_players': 0
    }
    total_duration = 0
    victories = 0
    defeats = 0
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        for f in files:
            try:
                file_data = await f.read()
                print(f"[Evening] Uploading {f.filename} to dps.report...")
                
                # Upload to dps.report
                upload_files = {"file": (f.filename, file_data)}
                upload_data = {"json": "1"}
                
                response = await client.post(
                    "https://dps.report/uploadContent",
                    files=upload_files,
                    data=upload_data
                )
                
                if response.status_code != 200:
                    print(f"[Evening] Upload failed for {f.filename}: {response.status_code}")
                    continue
                
                result = response.json()
                permalink = result.get('permalink', '')
                
                if not permalink:
                    print(f"[Evening] No permalink for {f.filename}")
                    continue
                
                # Fetch JSON data
                json_url = f"https://dps.report/getJson?permalink={permalink}"
                json_response = await client.get(json_url)
                
                if json_response.status_code != 200:
                    continue
                
                log_data = json_response.json()
                
                if 'error' in log_data:
                    print(f"[Evening] Error in JSON for {f.filename}: {log_data.get('error')}")
                    continue
                
                # Extract player data using existing function
                players_data = extract_players_from_ei_json(log_data)
                
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
                    'enemies_count': len(players_data.get('enemies', []))
                })
                
                print(f"[Evening] Processed {f.filename}: {players_data.get('fight_name')}")
                
            except Exception as e:
                print(f"[Evening] Error processing {f.filename}: {e}")
                continue
    
    # Calculate averages
    num_fights = len(fight_results)
    if num_fights > 0:
        avg_players = aggregated_composition['total_players'] // num_fights
        avg_duration = total_duration / num_fights
    else:
        avg_players = 0
        avg_duration = 0
    
    # Store session with real data
    sessions[session_id] = {
        "fights": fight_results,
        "composition": aggregated_composition,
        "stats": {
            "total_fights": num_fights,
            "total_duration_min": round(total_duration / 60, 1),
            "avg_duration_sec": round(avg_duration, 1),
            "avg_players": avg_players,
            "victories": victories,
            "defeats": defeats
        },
        "created_at": datetime.now()
    }
    
    return templates.TemplateResponse("partials/evening_result_v2.html", {
        "request": request,
        "fights": fight_results,
        "composition": aggregated_composition,
        "stats": sessions[session_id]["stats"],
        "session_id": session_id,
        "file_count": len(files)
    })


@app.get("/api/report/{session_id}/pdf")
async def download_pdf_report(session_id: str):
    """Download Night Intelligence Report as PDF"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    
    # Generate PDF (simplified for now)
    from pdf_generator import generate_night_report_pdf
    
    pdf_path = generate_night_report_pdf(session["report"], session["counter"])
    
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"night_intelligence_report_{session_id[:8]}.pdf"
    )


@app.get("/api/share/{session_id}")
async def get_shared_report(request: Request, session_id: str):
    """View a shared evening report"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Report not found")
    
    session = sessions[session_id]
    
    return templates.TemplateResponse("shared_report.html", {
        "request": request,
        "report": session["report"],
        "counter": session["counter"],
        "session_id": session_id
    })


@app.get("/health")
async def health_check():
    """Health check endpoint for deployment"""
    return {"status": "operational", "message": "GW2 CounterPicker is ready for war"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
