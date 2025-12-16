"""
GW2 CounterPicker - The Ultimate WvW Intelligence Tool
"Le seul outil capable de lire dans l'âme de ton adversaire. Et dans celle de tout son serveur."

v3.0 - IA VIVANTE - Apprend de chaque fight uploadé
Powered by Llama 3.2 8B via Ollama

Made with rage, love and 15 years of WvW pain.
"""

import os
import re
import uuid
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from pathlib import Path
from dataclasses import asdict

from fastapi import FastAPI, Request, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, Response
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
from role_detector import (
    estimate_role_from_profession, 
    detect_role_advanced, 
    parse_duration_string,
    get_base_class,
    SPEC_TO_CLASS
)
from counter_ai import (
    record_fight_for_learning,
    get_ai_counter,
    get_ai_status,
    counter_ai
)
from services.performance_stats_service import record_player_performance
from translations import get_all_translations
from scheduler import setup_scheduled_tasks
from rate_limiter import check_upload_rate_limit
from logger import get_logger
from routers.gw2_api import router as gw2_api_router
from services.gw2_api_service import get_api_key_by_session, get_account_by_session, gw2_api
from services.player_stats_service import record_player_fight
import zipfile
import io

# Setup logger
logger = get_logger('main')

# Note: GitHub link removed from footer in base.html

app = FastAPI(
    title="GW2 CounterPicker",
    description="The most powerful WvW intelligence tool ever created - IA VIVANTE powered by Llama 3.2",
    version="3.0.0"
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")
templates.env.globals["app_version"] = app.version
templates.env.globals["offline_mode"] = True
templates.env.globals["ai_mode"] = True  # v3.0 IA VIVANTE

# Initialize engines
real_parser = RealEVTCParser()

# Initialize scheduled tasks (fingerprint cleanup on Fridays at 18h55)
setup_scheduled_tasks()

# Include GW2 API router
app.include_router(gw2_api_router)

# Auto-deployment system active - Changes sync to GitHub and server automatically

# Import fight data if available (for deployment)
def import_deployed_data():
    """Import fight data from export file if database is empty"""
    from pathlib import Path
    import json
    from counter_ai import fights_table  # Import manquant
    
    # Check if we need to import data
    fights = fights_table.all()
    if not fights:
        export_file = Path("data/export/fights_export.json")
        if export_file.exists():
            logger.info(f"Importing {export_file.stat().st_size} bytes of fight data...")
            with open(export_file) as f:
                fights_data = json.load(f)
            fights_table.insert_multiple(fights_data)
            logger.info(f"Imported {len(fights_data)} fights to database")

# Import data on startup
import_deployed_data()

# Persistent session storage with TinyDB
DB_PATH = Path("data")
DB_PATH.mkdir(exist_ok=True)
db = TinyDB(DB_PATH / "sessions.json")
sessions_table = db.table("sessions")


def get_lang(request: Request) -> str:
    """Get language from cookie or default to French"""
    return request.cookies.get("lang", "fr")


# Security constants
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_EXTENSIONS = {'.evtc', '.zevtc', '.zip'}
ALLOWED_MIME_TYPES = {
    'application/octet-stream',
    'application/zip',
    'application/x-zip-compressed',
    'application/x-evtc'
}


async def validate_upload_file(file: UploadFile) -> bytes:
    """
    Validate uploaded file for security
    
    Args:
        file: Uploaded file
        
    Returns:
        File content as bytes
        
    Raises:
        HTTPException: If validation fails
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    # Check file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Read file content
    content = await file.read()
    file_size = len(content)
    
    # Check file size
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB"
        )
    
    if file_size == 0:
        raise HTTPException(status_code=400, detail="Empty file")
    
    # Validate ZIP files
    if file_ext == '.zip':
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                # Check for zip bombs (too many files or nested zips)
                if len(zf.namelist()) > 100:
                    raise HTTPException(
                        status_code=400,
                        detail="ZIP contains too many files (max 100)"
                    )
                
                # Check for dangerous files
                for name in zf.namelist():
                    if name.startswith('/') or '..' in name:
                        raise HTTPException(
                            status_code=400,
                            detail="ZIP contains invalid file paths"
                        )
                    
                    # Check file extension in ZIP
                    zip_ext = Path(name).suffix.lower()
                    if zip_ext not in {'.evtc', '.zevtc'}:
                        raise HTTPException(
                            status_code=400,
                            detail=f"ZIP must only contain .evtc or .zevtc files"
                        )
                
                # Check total uncompressed size
                total_size = sum(info.file_size for info in zf.infolist())
                if total_size > MAX_FILE_SIZE * 2:
                    raise HTTPException(
                        status_code=400,
                        detail="ZIP uncompressed size too large"
                    )
        except zipfile.BadZipFile:
            raise HTTPException(status_code=400, detail="Invalid or corrupted ZIP file")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"ZIP validation error: {str(e)}")
    
    return content


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Main landing page - The gateway to victory"""
    lang = get_lang(request)
    ai_status = get_ai_status()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "title": "GW2 CounterPicker",
        "lang": lang,
        "t": get_all_translations(lang),
        "ai_status": ai_status
    })

@app.get("/set-lang/{lang}")
async def set_language(request: Request, lang: str):
    """Set user language preference"""
    from fastapi.responses import RedirectResponse
    if lang not in ["fr", "en"]:
        lang = "fr"
    response = RedirectResponse(url=request.headers.get("referer", "/"), status_code=302)
    response.set_cookie(key="lang", value=lang, max_age=365*24*60*60)
    return response


@app.get("/about", response_class=HTMLResponse)
async def about_page(request: Request):
    """About page - How it works and limitations"""
    lang = get_lang(request)
    return templates.TemplateResponse("about.html", {
        "request": request,
        "title": "About" if lang == 'en' else "À propos",
        "lang": lang,
        "t": get_all_translations(lang)
    })


@app.get("/analyze", response_class=HTMLResponse)
async def analyze_page(request: Request):
    """Unified analysis page - supports single or multiple files"""
    lang = get_lang(request)
    return templates.TemplateResponse("analyze.html", {
        "request": request,
        "title": "Analyse",
        "lang": lang,
        "t": get_all_translations(lang)
    })


@app.get("/evening", response_class=HTMLResponse)
async def evening_page_redirect(request: Request):
    """Redirect to unified analyze page"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/analyze", status_code=301)


@app.get("/meta", response_class=HTMLResponse)
@app.get("/meta/{context}", response_class=HTMLResponse)
async def meta_page(request: Request, context: str = None):
    """
    Meta 2025 page - Current trending builds with AI status
    
    Args:
        context: Optional filter - "zerg", "guild_raid", "roam", or None for all
    """
    # Validate context parameter
    valid_contexts = ['zerg', 'guild_raid', 'roam', None]
    if context and context not in valid_contexts:
        context = None
    
    # Try to get meta from database first (real data), fallback to static/default
    meta_data = get_meta_from_database(context=context)
    
    # If no data from database, try static file
    if not meta_data.get('tier_s'):
        meta_file = Path("data/meta_2025.json")
        if meta_file.exists():
            with open(meta_file) as f:
                meta_data = json.load(f)
        else:
            meta_data = get_default_meta_data()
    
    # Add AI learning status
    ai_status = get_ai_status()
    
    # Title based on context
    context_titles = {
        'zerg': 'Meta Zerg 2025',
        'guild_raid': 'Meta Raid Guilde 2025',
        'roam': 'Meta Roaming 2025',
        None: 'Meta WvW 2025'
    }
    
    lang = get_lang(request)
    return templates.TemplateResponse("meta.html", {
        "request": request,
        "title": context_titles.get(context, "Meta 2025"),
        "meta_data": meta_data,
        "ai_status": ai_status,
        "current_context": context,
        "lang": lang,
        "t": get_all_translations(lang)
    })


async def record_user_fight_stats(request: Request, players_data: Dict, log_data: Dict = None):
    """Record fight stats for connected user if they appear in the log"""
    try:
        session_id = request.cookies.get("session_id")
        if not session_id:
            return
        
        account_info = get_account_by_session(session_id)
        if not account_info:
            return
        
        account_id = account_info["account_id"]
        account_name = account_info["account_name"]
        
        # Find user in allies list
        for ally in players_data.get('allies', []):
            # Match by account name (format: "Name.1234")
            ally_name = ally.get('name', '')
            if account_name.split('.')[0].lower() in ally_name.lower():
                # Found the user in the log
                fight_data = {
                    'duration': players_data.get('duration_seconds', 0),
                    'damage_out': ally.get('damage', 0),
                    'damage_in': ally.get('damage_in', 0),
                    'kills': ally.get('kills', 0),
                    'deaths': ally.get('deaths', 0),
                    'downs': ally.get('downs', 0),
                    'cleanses': ally.get('cleanses', 0),
                    'strips': ally.get('boon_strips', 0),
                    'healing': ally.get('healing', 0),
                    'barrier': ally.get('barrier', 0),
                    'boon_uptime': ally.get('boon_uptime', {}),
                    'outcome': players_data.get('outcome', 'draw'),
                    'enemy_count': len(players_data.get('enemies', [])),
                    'ally_count': len(players_data.get('allies', [])),
                    'dps': ally.get('dps', 0)
                }
                
                record_player_fight(
                    account_id=account_id,
                    account_name=account_name,
                    character_name=ally_name,
                    profession=ally.get('profession', 'Unknown'),
                    elite_spec=ally.get('profession', 'Unknown'),
                    role=ally.get('role', 'dps'),
                    fight_data=fight_data
                )
                logger.info(f"Recorded fight stats for {account_name}")
                return
                
    except Exception as e:
        logger.error(f"Failed to record user fight stats: {e}")


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
                
                # Filter: Only accept WvW logs
                if not is_wvw_log(log_data):
                    fight_name = log_data.get('fightName', 'Unknown')
                    logger.warning(f"Rejected non-WvW log: {fight_name}")
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Ce rapport n'est pas un combat WvW. Détecté: {fight_name}. Seuls les logs WvW sont acceptés."
                    )
                
                players_data = extract_players_from_ei_json(log_data)
                
                enemy_composition = build_composition_from_enemies(players_data['enemies'])
                
                # Record fight for AI learning
                players_data['source'] = 'dps_report'
                players_data['source_name'] = url
                record_fight_for_learning(players_data)
                
                # Generate AI counter
                enemy_spec_counts = players_data.get('enemy_composition', {}).get('spec_counts', {})
                ai_counter = await get_ai_counter(enemy_spec_counts)
                
                lang = get_lang(request)
                return templates.TemplateResponse("partials/dps_report_result.html", {
                    "request": request,
                    "data": log_data,
                    "players": players_data,
                    "ai_counter": ai_counter,
                    "permalink": url,
                    "filename": "dps.report URL",
                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                    "parse_mode": "online",
                    "lang": lang,
                    "t": get_all_translations(lang)
                })
    except Exception as e:
        logger.error(f"dps.report API failed: {e}")
    
    raise HTTPException(status_code=500, detail="Failed to fetch dps.report data")


@app.post("/api/analyze/evtc")
async def analyze_evtc_files(
    request: Request,
    files: List[UploadFile] = File(...),
    context: str = Form("auto")
):
    """
    Unified endpoint: Analyze single or multiple .evtc files
    Strategy: Try dps.report first, fallback to local parser if unavailable
    
    Args:
        files: EVTC/ZEVTC files to analyze
        context: Fight context - "auto", "zerg", "guild_raid", "roam"
    
    Security: Rate limited to 10 uploads/min, max 50MB per file, ZIP validation
    """
    logger.info(f"analyze_evtc_files called with {len(files)} files")
    for i, file in enumerate(files):
        logger.info(f"  File {i+1}: {file.filename} ({file.content_type})")
    
    # Rate limiting check
    await check_upload_rate_limit(request)
    
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    # Single file mode
    if len(files) == 1:
        file = files[0]
        
        # Validate and read file securely
        data = await validate_upload_file(file)
        logger.info(f"Received file: {file.filename}, size: {len(data)} bytes")
        
        parse_mode = "offline"
        
        # Strategy 1: Try dps.report API first
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                upload_files = {'file': (file.filename, data)}
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
                            
                            # Filter: Only accept WvW logs
                            if not is_wvw_log(log_data):
                                fight_name = log_data.get('fightName', 'Unknown')
                                logger.warning(f"Rejected non-WvW log: {fight_name}")
                                raise HTTPException(
                                    status_code=400, 
                                    detail=f"Ce rapport n'est pas un combat WvW. Détecté: {fight_name}. Seuls les logs WvW sont acceptés."
                                )
                            
                            players_data = extract_players_from_ei_json(log_data)
                            
                            # Record fight for AI learning with context
                            players_data['source'] = 'dps_report'
                            players_data['source_name'] = permalink
                            record_fight_for_learning(players_data, context=context)
                            
                            # Record performance stats for global comparison
                            duration_sec = players_data.get('duration_sec', 0)
                            for ally in players_data.get('allies', []):
                                record_player_performance(ally, duration_sec)
                            
                            # Record stats for connected user
                            await record_user_fight_stats(request, players_data, log_data)
                            
                            # Generate AI counter
                            enemy_spec_counts = players_data.get('enemy_composition', {}).get('spec_counts', {})
                            ai_counter = await get_ai_counter(enemy_spec_counts)
                            
                            logger.info(f"dps.report success: {len(players_data['enemies'])} enemies")
                            
                            lang = get_lang(request)
                            return templates.TemplateResponse("partials/dps_report_result.html", {
                                "request": request,
                                "data": log_data,
                                "players": players_data,
                                "ai_counter": ai_counter,
                                "permalink": permalink,
                                "filename": file.filename,
                                "timestamp": datetime.now().strftime("%H:%M:%S"),
                                "parse_mode": "online",
                                "lang": lang,
                                "t": get_all_translations(lang)
                            })
        except Exception as api_error:
            logger.warning(f"dps.report unavailable: {api_error}")
        
        # Strategy 2: OFFLINE FALLBACK - Use local parser
        logger.info("Using OFFLINE mode with local parser")
        try:
            parsed_log = real_parser.parse_evtc_bytes(data, file.filename)
            
            # Convert parsed log to players_data format
            players_data = convert_parsed_log_to_players_data(parsed_log)
            
            # Record fight for AI learning with context (with deduplication)
            players_data['source'] = 'evtc'
            players_data['source_name'] = file.filename
            record_fight_for_learning(players_data, filename=file.filename, filesize=file.size, context=context)
            
            # Record performance stats for global comparison
            duration_sec = players_data.get('duration_sec', 0)
            for ally in players_data.get('allies', []):
                record_player_performance(ally, duration_sec)
            
            # Record stats for connected user
            await record_user_fight_stats(request, players_data)
            
            # Generate AI counter
            enemy_spec_counts = players_data.get('enemy_composition', {}).get('spec_counts', {})
            ai_counter = await get_ai_counter(enemy_spec_counts)
            
            logger.info(f"Offline parse success: {len(parsed_log.players)} allies, {len(parsed_log.enemies)} enemies")
            
            lang = get_lang(request)
            return templates.TemplateResponse("partials/dps_report_result.html", {
                "request": request,
                "data": {"fightName": f"Offline: {file.filename}", "duration": f"{parsed_log.duration_seconds}s"},
                "players": players_data,
                "ai_counter": ai_counter,
                "permalink": "",
                "filename": file.filename,
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "parse_mode": "offline",
                "lang": lang,
                "t": get_all_translations(lang)
            })
        except Exception as parse_error:
            import traceback
            logger.error(f"Local parser failed: {parse_error}\n{traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=f"Failed to parse file: {str(parse_error)}")
    
    # Multiple files mode - redirect to evening analysis
    else:
        return await analyze_evening_files(request, files)


def is_wvw_log(data: dict) -> bool:
    """
    Detect if an Elite Insights JSON log is from WvW content.
    
    WvW logs have specific characteristics:
    - targets contain enemyPlayer: true (player enemies, not NPCs)
    - No raid/fractal/strike boss IDs
    - fightName typically contains player names or generic WvW identifiers
    - isCM is false or absent (no Challenge Mode in WvW)
    
    PvE logs have:
    - Boss targets with specific triggerID/encounterID
    - targets with enemyPlayer: false (NPCs)
    - fightName contains boss names like "Vale Guardian", "Dhuum", etc.
    
    Returns True if WvW, False otherwise.
    """
    # Known PvE boss encounter IDs (partial list of common raids/fractals/strikes)
    PVE_BOSS_IDS = {
        # Raids
        15438, 15429, 15375, 15251,  # Wing 1: VG, Gorseval, Sabetha
        16123, 16115, 16235, 16246,  # Wing 2: Slothasor, Trio, Matthias
        16286, 16253, 16247,         # Wing 3: Escort, KC, Xera
        17194, 17172, 17188, 17154,  # Wing 4: Cairn, MO, Samarog, Deimos
        19767, 19828, 19691, 19536,  # Wing 5: SH, Dhuum
        21105, 21089, 20934, 21041,  # Wing 6: CA, Largos, Qadim
        22006, 21964, 22000,         # Wing 7: Adina, Sabir, QTP
        # Fractals CM
        17021, 17028,                # MAMA, Siax, Ensolyss
        17949, 17759,                # Skorvald, Artsariiv, Arkk
        23254, 23223,                # Ai, Kanaxai
        # Strikes
        22154, 22492, 22711, 22521,  # IBS Strikes
        24033, 24266, 24660, 25413,  # EoD Strikes
        25577, 25989, 26087,         # SotO Strikes
    }
    
    # Check for PvE boss by triggerID or encounterID
    trigger_id = data.get('triggerID', 0)
    if trigger_id in PVE_BOSS_IDS:
        return False
    
    # Check targets for enemy players
    targets = data.get('targets', [])
    has_enemy_players = any(t.get('enemyPlayer', False) for t in targets)
    
    # If there are enemy players, it's likely WvW
    if has_enemy_players:
        return True
    
    # Check fightName for known PvE indicators
    fight_name = data.get('fightName', '').lower()
    pve_indicators = [
        'vale guardian', 'gorseval', 'sabetha', 'slothasor', 'matthias',
        'keep construct', 'xera', 'cairn', 'mursaat', 'samarog', 'deimos',
        'soulless horror', 'dhuum', 'conjured amalgamate', 'largos', 'qadim',
        'adina', 'sabir', 'mama', 'siax', 'ensolyss', 'skorvald', 'artsariiv',
        'arkk', 'kanaxai', 'boneskinner', 'whisper', 'fraenir', 'icebrood',
        'mai trin', 'ankka', 'minister li', 'harvest temple', 'old lion',
        'cerus', 'dagda', 'golem', 'standard kitty', 'medium kitty', 'large kitty'
    ]
    
    for indicator in pve_indicators:
        if indicator in fight_name:
            return False
    
    # Check if it's a golem (training area)
    if 'golem' in fight_name or data.get('isTrainingGolem', False):
        return False
    
    # Check for Challenge Mode (only in PvE)
    if data.get('isCM', False):
        return False
    
    # Default: if no enemy players and no clear WvW indicators, reject
    # WvW logs should always have enemy players
    if not has_enemy_players and len(targets) > 0:
        return False
    
    # Empty targets could be a parsing issue, allow it
    return True


def is_player_afk(player) -> bool:
    """
    Determine if a player was AFK/inactive during the fight.
    AFK criteria: no damage dealt, no healing done, no kills
    More lenient to include players who took damage but didn't contribute.
    """
    damage = getattr(player, 'damage_dealt', 0) or 0
    healing = getattr(player, 'healing_done', 0) or 0
    kills = getattr(player, 'kills', 0) or 0
    
    # Player is AFK if they contributed nothing offensively or supportively
    # Being more lenient - only exclude if truly zero contribution
    return damage == 0 and healing == 0 and kills == 0


def convert_parsed_log_to_players_data(parsed_log) -> dict:
    """Convert ParsedLog from local parser to players_data format used by templates."""
    allies = []
    allies_afk = []  # Track AFK players separately
    enemies = []
    
    duration_sec = max(parsed_log.duration_seconds, 1)
    
    # First pass: collect all ally data
    all_ally_data = []
    for player in parsed_log.players:
        damage = player.damage_dealt or 0
        healing = player.healing_done or 0
        downs = player.downs if hasattr(player, 'downs') else 0
        
        player_data = {
            'name': player.character_name,
            'account': player.account_name,
            'profession': player.elite_spec or player.profession,
            'elite_spec': player.elite_spec,
            'group': player.subgroup,
            # Damage stats
            'damage': damage,
            'damage_out': damage,
            'damage_in': 0,
            'dps': damage // duration_sec,
            'down_contrib': downs,
            'down_contrib_per_sec': round(downs / duration_sec, 2) if downs else 0,
            'damage_ratio': 0,
            # Combat stats
            'kills': player.kills or 0,
            'deaths': player.deaths or 0,
            'downs': downs,
            'cc_out': 0,
            'boon_strips': 0,
            'strips_per_sec': 0,
            # Support stats
            'healing': healing,
            'healing_per_sec': round(healing / duration_sec, 2) if healing else 0,
            'cleanses': 0,
            'cleanses_per_sec': 0,
            'resurrects': 0,
            'barrier': 0,
            # Boon generation
            'boon_gen': {},
            'boon_uptime': {},
            # Meta
            'is_commander': False,
            'role': player.estimated_role.lower() if player.estimated_role else 'dps',
            'is_afk': is_player_afk(player),
            'in_squad': player.subgroup > 0,  # Group 0 = not in squad
        }
        all_ally_data.append(player_data)
    
    # Separate AFK from active - but if all would be AFK, include them anyway
    active_allies = [p for p in all_ally_data if not p['is_afk']]
    afk_allies = [p for p in all_ally_data if p['is_afk']]
    
    if active_allies:
        allies = active_allies
        allies_afk = afk_allies
    else:
        # No active allies found - include all players to avoid empty results
        allies = all_ally_data
        allies_afk = []
    
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
    specs_by_role = {'dps': {}, 'dps_strip': {}, 'healer': {}, 'stab': {}, 'boon': {}}
    
    for p in allies:
        spec = p['profession']
        spec_counts[spec] = spec_counts.get(spec, 0) + 1
        role = p.get('role', 'dps')
        # Always count the role, even if not in the predefined list
        if role not in role_counts:
            role_counts[role] = 0
        role_counts[role] += 1
        if role not in specs_by_role:
            specs_by_role[role] = {}
        specs_by_role[role][spec] = specs_by_role[role].get(spec, 0) + 1
    
    enemy_spec_counts = {}
    enemy_role_counts = {'dps': 0, 'dps_strip': 0, 'healer': 0, 'stab': 0, 'boon': 0}
    enemy_specs_by_role = {'dps': {}, 'dps_strip': {}, 'healer': {}, 'stab': {}, 'boon': {}}
    
    for e in enemies:
        spec = e['profession']
        enemy_spec_counts[spec] = enemy_spec_counts.get(spec, 0) + 1
        role = e.get('role', 'dps')
        if role in enemy_role_counts:
            enemy_role_counts[role] += 1
            enemy_specs_by_role[role][spec] = enemy_specs_by_role[role].get(spec, 0) + 1
    
    # Calculate stats from ACTIVE players only (exclude AFK)
    active_deaths = sum(p.get('deaths', 0) for p in allies)
    active_kills = sum(p.get('kills', 0) for p in allies)
    active_damage = sum(p.get('damage', 0) for p in allies)
    
    # Calculate fight outcome based on combat stats
    def determine_fight_outcome(allies, enemies, duration_sec):
        """Determine fight outcome based on combat statistics"""
        if not allies or not enemies:
            return 'unknown'
        
        # Calculate total deaths and downs for allies
        total_ally_deaths = sum(p.get('deaths', 0) for p in allies)
        total_ally_downs = sum(p.get('downs', 0) for p in allies)
        
        # For very short fights (< 30s), consider draws unless clear winner
        if duration_sec < 30:
            if total_ally_deaths == 0:
                return 'victory'
            elif total_ally_deaths > 3:
                return 'defeat'
            else:
                return 'draw'
        
        # For longer fights, use death ratio
        if total_ally_deaths == 0:
            return 'victory'
        elif total_ally_downs > len(allies) * 0.8:  # Most allies were downed
            return 'defeat'
        else:
            # Check if it was a close fight
            if total_ally_deaths <= 2 and total_ally_downs <= len(allies) * 0.3:
                return 'victory'
            elif total_ally_deaths >= len(allies) * 0.5:
                return 'defeat'
            else:
                return 'draw'
    
    fight_outcome = determine_fight_outcome(allies, parsed_log.players, parsed_log.duration_seconds)
    
    # Calculate ally_downs from the allies dict (already converted)
    total_ally_downs = sum(p.get('downs', 0) for p in allies)
    
    return {
        'allies': allies,
        'allies_afk': allies_afk,  # AFK players tracked separately
        'enemies': sorted(enemies, key=lambda x: x.get('damage_taken', 0), reverse=True)[:20],
        'fight_name': f"WvW Combat ({parsed_log.duration_seconds}s)",
        'duration_sec': parsed_log.duration_seconds,
        'fight_outcome': fight_outcome,
        'fight_stats': {
            'ally_deaths': active_deaths,
            'ally_downs': total_ally_downs,
            'ally_kills': active_kills,
            'ally_damage': active_damage,
            'enemy_damage_taken': sum(e.damage_taken for e in parsed_log.enemies),
            'afk_count': len(allies_afk),
            'active_count': len(allies)
        },
        'composition': {
            'spec_counts': spec_counts,
            'role_counts': role_counts,
            'specs_by_role': specs_by_role,
            'total': len(allies)  # Only active allies
        },
        'enemy_composition': {
            'spec_counts': enemy_spec_counts,
            'role_counts': enemy_role_counts,
            'specs_by_role': enemy_specs_by_role,
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
    """Extract player information from Elite Insights JSON with comprehensive stats"""

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

    # Boon IDs for tracking (from GW2 API)
    BOON_IDS = {
        'quickness': 1187,
        'protection': 717,
        'vigor': 726,
        'aegis': 743,
        'stability': 1122,
        'resistance': 26980,
        'superspeed': 5974,
        # Secondary boons
        'might': 740,
        'fury': 725,
        'regeneration': 718,
        'resolution': 873,
        'swiftness': 719,
        'alacrity': 30328
    }

    # Get fight duration using centralized parser
    duration_sec = parse_duration_string(data.get('duration', '0'))

    players = []
    group_boon_uptimes = {}  # {group_num: {boon_name: uptime %}}

    for player in data.get('players', []):
        player_name = player.get('name', 'Unknown')
        
        # === DAMAGE OUT ===
        dps_entries = player.get('dpsAll', [])
        damage_out = safe_number(dps_entries)
        
        # Skip players who didn't participate (less than 1k damage)
        if damage_out < 1000:
            continue
        
        # === DAMAGE IN ===
        damage_in = 0
        defenses = player.get('defenses', [{}])
        if defenses and len(defenses) > 0:
            d = defenses[0] if isinstance(defenses[0], dict) else {}
            damage_in = d.get('damageTaken', 0)
        
        # === SUPPORT STATS ===
        support_data = player.get('support', [{}])
        support = support_data[0] if support_data else {}
        condi_cleanse = support.get('condiCleanse', 0)
        condi_cleanse_self = support.get('condiCleanseSelf', 0)
        resurrects = support.get('resurrects', 0)
        boon_strips = support.get('boonStrips', 0)
        
        # === HEALING OUT (includes barrier) ===
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
        
        # === BARRIER OUT ===
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
        
        healing_total = healing + barrier
        
        # === DOWN CONTRIBUTION & CC OUT ===
        down_contrib = 0
        cc_out = 0
        deaths = 0
        downs = 0
        kills = 0
        stats_all = player.get('statsAll', [{}])
        if stats_all and len(stats_all) > 0:
            stats = stats_all[0] if isinstance(stats_all[0], dict) else {}
            down_contrib = stats.get('downContribution', 0)
            cc_out = stats.get('interrupts', 0) + stats.get('knockdowns', 0)
            # Extract kills - EI uses 'killed' for final blows
            kills = stats.get('killed', 0) + stats.get('killedDowned', 0)
        
        if defenses and len(defenses) > 0:
            d = defenses[0] if isinstance(defenses[0], dict) else {}
            deaths = d.get('deadCount', 0)
            downs = d.get('downCount', 0)
            # CC received (stuns, knockdowns, etc.)
        
        # === BOON STRIP IN (received from enemies) ===
        boon_strip_in = 0
        if defenses and len(defenses) > 0:
            d = defenses[0] if isinstance(defenses[0], dict) else {}
            boon_strip_in = d.get('boonStrips', 0)
        
        # === BOON GENERATION ===
        boon_gen = {}
        for boon_name, boon_id in BOON_IDS.items():
            for buff in player.get('groupBuffs', []):
                if buff.get('id') == boon_id:
                    buff_data = buff.get('buffData', [{}])
                    if buff_data and len(buff_data) > 0:
                        boon_gen[boon_name] = buff_data[0].get('generation', 0)
                    break
            if boon_name not in boon_gen:
                boon_gen[boon_name] = 0
        
        # === BOON UPTIME (received) ===
        boon_uptime = {}
        for boon_name, boon_id in BOON_IDS.items():
            for buff in player.get('buffUptimes', []):
                if buff.get('id') == boon_id:
                    boon_uptime[boon_name] = buff.get('buffData', [{}])[0].get('uptime', 0) if buff.get('buffData') else 0
                    break
            if boon_name not in boon_uptime:
                boon_uptime[boon_name] = 0
        
        # === SKILL USAGE ===
        skill_usage = []
        for rotation in player.get('rotation', []):
            skill_id = rotation.get('id', 0)
            skill_name = rotation.get('skill', f'Skill_{skill_id}')
            casts = len(rotation.get('skills', []))
            if duration_sec > 0:
                casts_per_min = round(casts / (duration_sec / 60), 2)
            else:
                casts_per_min = 0
            skill_usage.append({
                'id': skill_id,
                'name': skill_name,
                'casts': casts,
                'casts_per_min': casts_per_min
            })
        
        # === PER-SECOND VALUES ===
        if duration_sec > 0:
            dps = round(damage_out / duration_sec, 1)
            cleanses_per_sec = round(condi_cleanse / duration_sec, 2)
            down_contrib_per_sec = round(down_contrib / duration_sec, 2)
            cc_per_sec = round(cc_out / duration_sec, 2)
            healing_per_sec = round(healing_total / duration_sec, 1)
            strips_per_sec = round(boon_strips / duration_sec, 2)
            strip_in_per_sec = round(boon_strip_in / duration_sec, 2)
        else:
            dps = cleanses_per_sec = down_contrib_per_sec = cc_per_sec = 0
            healing_per_sec = strips_per_sec = strip_in_per_sec = 0
        
        profession = player.get('profession', 'Unknown')
        group = player.get('group', 0)
        
        # Track group boon uptimes
        if group not in group_boon_uptimes:
            group_boon_uptimes[group] = {b: [] for b in BOON_IDS.keys()}
        for boon_name, uptime in boon_uptime.items():
            group_boon_uptimes[group][boon_name].append(uptime)
        
        # Use advanced role detection with all stats
        role_stats = {
            'healing': healing,
            'stab_gen': boon_gen.get('stability', 0),
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
            'group': group,
            'is_commander': player.get('hasCommanderTag', False),
            'role': role,
            # Damage
            'damage_out': int(damage_out),
            'damage_in': int(damage_in),
            'dps': dps,
            'damage_ratio': round(damage_out / damage_in, 2) if damage_in > 0 else 999,
            # Combat stats
            'down_contrib': down_contrib,
            'down_contrib_per_sec': down_contrib_per_sec,
            'cc_out': cc_out,
            'cc_per_sec': cc_per_sec,
            'deaths': deaths,
            'downs': downs,
            'kills': kills,
            # Support stats
            'cleanses': condi_cleanse,
            'cleanses_self': condi_cleanse_self,
            'cleanses_per_sec': cleanses_per_sec,
            'heal_only': healing,
            'barrier': barrier,
            'healing': healing_total,
            'healing_per_sec': healing_per_sec,
            'boon_strips': boon_strips,
            'strips_per_sec': strips_per_sec,
            'resurrects': resurrects,
            # Defensive
            'boon_strip_in': boon_strip_in,
            'strip_in_per_sec': strip_in_per_sec,
            # Boons
            'boon_gen': boon_gen,
            'boon_uptime': boon_uptime,
            # Skills
            'skill_usage': sorted(skill_usage, key=lambda x: x['casts'], reverse=True)[:20],
            # Legacy compatibility
            'damage': int(damage_out),
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

    # Calculate average boon uptimes per group
    group_boon_avg = {}
    for group, boons in group_boon_uptimes.items():
        group_boon_avg[group] = {}
        for boon_name, uptimes in boons.items():
            group_boon_avg[group][boon_name] = round(sum(uptimes) / len(uptimes), 1) if uptimes else 0
    
    # Calculate squad totals
    squad_totals = {
        'damage_out': sum(p.get('damage_out', 0) for p in players),
        'damage_in': sum(p.get('damage_in', 0) for p in players),
        'healing': sum(p.get('healing', 0) for p in players),
        'cleanses': sum(p.get('cleanses', 0) for p in players),
        'boon_strips': sum(p.get('boon_strips', 0) for p in players),
        'down_contrib': sum(p.get('down_contrib', 0) for p in players),
        'cc_out': sum(p.get('cc_out', 0) for p in players),
        'resurrects': sum(p.get('resurrects', 0) for p in players),
    }
    squad_totals['damage_ratio'] = round(squad_totals['damage_out'] / squad_totals['damage_in'], 2) if squad_totals['damage_in'] > 0 else 999

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
        'squad_totals': squad_totals,
        'group_boon_uptimes': group_boon_avg,
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
    
    Security: Rate limited to 10 uploads/min, max 50MB per file, ZIP validation
    """
    # Rate limiting check
    await check_upload_rate_limit(request)
    
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")
    
    if len(files) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 files allowed")
    
    # Validate all files before processing
    validated_files = []
    for file in files:
        try:
            content = await validate_upload_file(file)
            validated_files.append((file.filename, content))
        except HTTPException as e:
            raise HTTPException(
                status_code=e.status_code,
                detail=f"File '{file.filename}': {e.detail}"
            )
    
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
    skipped_non_wvw = 0  # Count of non-WvW logs skipped
    parse_mode = "offline"  # Track which mode was used
    
    # Use local parser for evening analysis (faster and more reliable for batch processing)
    dps_report_available = False
    logger.info("Using OFFLINE mode for batch analysis (faster)")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Skip dps.report check - use local parser directly for batch processing
        pass
        
        logger.info(f"Processing {len(validated_files)} files...")
        
        for filename, file_data in validated_files:
            logger.info(f"Processing file: {filename} ({len(file_data)} bytes)")
            players_data = None
            permalink = ""
            
            # Strategy 1: Try dps.report if available
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
                                logger.info(f"Got JSON for {filename}, error={log_data.get('error', 'none')}")
                                if 'error' not in log_data:
                                    # Filter: Only accept WvW logs
                                    is_wvw = is_wvw_log(log_data)
                                    logger.info(f"is_wvw_log({filename}): {is_wvw}, fightName={log_data.get('fightName', 'Unknown')}")
                                    if not is_wvw:
                                        fight_name = log_data.get('fightName', 'Unknown')
                                        logger.warning(f"Skipped non-WvW log in batch: {fight_name}")
                                        skipped_non_wvw += 1
                                        continue
                                    players_data = extract_players_from_ei_json(log_data)
                                    logger.info(f"Extracted {len(players_data.get('allies', []))} allies, {len(players_data.get('enemies', []))} enemies")
                                    parse_mode = "online"
                            else:
                                logger.warning(f"JSON fetch failed for {filename}: status={json_response.status_code}")
                except Exception as e:
                    logger.warning(f"dps.report failed for {filename}: {e}")
                    dps_report_available = False  # Switch to offline for remaining files
            
            # Strategy 2: OFFLINE FALLBACK - Use local parser
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
            
            # Aggregate composition data
            if players_data.get('composition'):
                comp = players_data['composition']
                for spec, count in comp.get('spec_counts', {}).items():
                    aggregated_composition['spec_counts'][spec] = aggregated_composition['spec_counts'].get(spec, 0) + count
                for role, count in comp.get('role_counts', {}).items():
                    aggregated_composition['role_counts'][role] = aggregated_composition['role_counts'].get(role, 0) + count
                for role, specs in comp.get('specs_by_role', {}).items():
                    if role not in aggregated_composition['specs_by_role']:
                        aggregated_composition['specs_by_role'][role] = {}
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
            
            # Track player stats for top 10 - USE ACCOUNT NAME for deduplication
            for ally in players_data.get('allies', []):
                # Use account name for deduplication, fallback to character name
                account = ally.get('account', ally.get('name', 'Unknown'))
                char_name = ally.get('name', 'Unknown')
                
                if account not in player_stats:
                    player_stats[account] = {
                        'account': account,
                        'name': char_name,  # Keep one character name for display
                        'spec': ally.get('elite_spec', ally.get('profession', 'Unknown')),
                        'specs_played': {},
                        'damage': 0,
                        'kills': 0,
                        'deaths': 0,
                        'appearances': 0
                    }
                
                # Track specs played by this account
                spec = ally.get('elite_spec', ally.get('profession', 'Unknown'))
                player_stats[account]['specs_played'][spec] = player_stats[account]['specs_played'].get(spec, 0) + 1
                
                # Update most played spec
                most_played = max(player_stats[account]['specs_played'].items(), key=lambda x: x[1])
                player_stats[account]['spec'] = most_played[0]
                
                # Use damage_out directly (already total damage), not dps * duration
                player_stats[account]['damage'] += ally.get('damage_out', ally.get('dps', 0))
                player_stats[account]['kills'] += ally.get('kills', 0)
                player_stats[account]['deaths'] += ally.get('deaths', 0)
                player_stats[account]['appearances'] += 1
            
            # Track map/zone
            fight_name = players_data.get('fight_name', 'Unknown')
            map_counts[fight_name] = map_counts.get(fight_name, 0) + 1
            
            total_duration += players_data.get('duration_sec', 0)
            
            # Track wins/losses/draws
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
    
    # Calculate averages
    num_fights = len(fight_results)
    if num_fights > 0:
        avg_players = aggregated_composition['total_players'] // num_fights
        avg_duration = total_duration / num_fights
    else:
        avg_players = 0
        avg_duration = 0
    
    # Calculate top 10 players by damage (using account name for deduplication)
    top_players = sorted(
        [{'name': stats.get('account', name), 'display_name': stats.get('name', name), **stats} for name, stats in player_stats.items()],
        key=lambda x: x['damage'],
        reverse=True
    )[:10]
    
    # Count unique players (by account)
    unique_players_count = len(player_stats)
    
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
    
    # Build stats dict - Simplified summary
    stats = {
        "total_fights": num_fights,
        "total_duration_min": round(total_duration / 60, 1),
        "avg_duration_sec": round(avg_duration, 1),
        "avg_players": avg_players,
        "unique_players": unique_players_count,
        "victories": victories,
        "defeats": defeats,
        "draws": draws,
        "skipped_non_wvw": skipped_non_wvw,
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
    ai_status = get_ai_status()
    return {
        "status": "operational", 
        "message": "GW2 CounterPicker v3.0 - IA VIVANTE",
        "ai_status": ai_status
    }


@app.get("/api/ai/status")
async def ai_status_endpoint():
    """Get AI learning status"""
    return get_ai_status()


@app.get("/favicon.ico")
async def favicon():
    """Return empty response for favicon to avoid 404 errors"""
    return Response(status_code=204)


def get_default_meta_data() -> dict:
    """Default meta data when no file exists"""
    return {
        "last_updated": "Décembre 2025",
        "tier_s": [
            {"spec": "Firebrand", "role": "Stab/Support", "usage": 95},
            {"spec": "Scrapper", "role": "Heal/Superspeed", "usage": 90},
            {"spec": "Spellbreaker", "role": "Strip/DPS", "usage": 85}
        ],
        "tier_a": [
            {"spec": "Scourge", "role": "Condi/Corrupt", "usage": 75},
            {"spec": "Herald", "role": "Boon/Frontline", "usage": 70},
            {"spec": "Tempest", "role": "Heal/Aura", "usage": 65}
        ],
        "tier_b": [
            {"spec": "Reaper", "role": "DPS/Power", "usage": 50},
            {"spec": "Chronomancer", "role": "Strip/CC", "usage": 45},
            {"spec": "Vindicator", "role": "Boon/Leap", "usage": 40}
        ],
        "tier_c": [
            {"spec": "Harbinger", "role": "DPS/Condi", "usage": 30},
            {"spec": "Willbender", "role": "Roamer/Burst", "usage": 25},
            {"spec": "Druid", "role": "Heal/Spirits", "usage": 20}
        ]
    }


def get_meta_from_database(context: str = None) -> dict:
    """
    Generate meta data from actual fight database
    
    Args:
        context: Filter by fight context - "zerg", "guild_raid", "roam", or None for all
    """
    from counter_ai import fights_table
    
    # Count spec usage across fights (optionally filtered by context)
    spec_counts = {}
    total_builds = 0
    fights_count = 0
    
    for fight in fights_table.all():
        # Filter by context if specified
        if context:
            fight_context = fight.get('context_confirmed') or fight.get('context_detected') or fight.get('context', 'unknown')
            if fight_context != context:
                continue
        
        fights_count += 1
        for build in fight.get('ally_builds', []):
            spec = build.get('elite_spec', build.get('profession', 'Unknown'))
            role = build.get('role', 'dps')
            if spec and spec != 'Unknown':
                if spec not in spec_counts:
                    spec_counts[spec] = {'count': 0, 'roles': {}, 'wins': 0}
                spec_counts[spec]['count'] += 1
                spec_counts[spec]['roles'][role] = spec_counts[spec]['roles'].get(role, 0) + 1
                # Track wins for win rate calculation
                if fight.get('outcome') == 'victory':
                    spec_counts[spec]['wins'] += 1
                total_builds += 1
    
    if total_builds == 0:
        return get_default_meta_data()
    
    # Sort by usage and create tiers
    sorted_specs = sorted(spec_counts.items(), key=lambda x: x[1]['count'], reverse=True)
    
    def get_main_role(roles_dict):
        if not roles_dict:
            return "DPS"
        main_role = max(roles_dict.items(), key=lambda x: x[1])[0]
        role_map = {'healer': 'Heal', 'stab': 'Stab', 'boon': 'Boon', 'dps_strip': 'Strip', 'dps': 'DPS'}
        return role_map.get(main_role, main_role.capitalize())
    
    def make_tier(specs_slice):
        result = []
        for spec, data in specs_slice:
            usage = round((data['count'] / total_builds) * 100)
            main_role = get_main_role(data['roles'])
            win_rate = round((data['wins'] / data['count']) * 100) if data['count'] > 0 else 0
            result.append({
                'spec': spec,
                'role': main_role,
                'usage': min(usage, 99),  # Cap at 99%
                'win_rate': win_rate
            })
        return result
    
    # Distribute into tiers
    tier_s = make_tier(sorted_specs[:3]) if len(sorted_specs) >= 3 else make_tier(sorted_specs)
    tier_a = make_tier(sorted_specs[3:6]) if len(sorted_specs) >= 6 else []
    tier_b = make_tier(sorted_specs[6:9]) if len(sorted_specs) >= 9 else []
    tier_c = make_tier(sorted_specs[9:12]) if len(sorted_specs) >= 12 else []
    
    # Context labels for display
    context_labels = {
        'zerg': 'Zerg (25+ joueurs)',
        'guild_raid': 'Raid Guilde (10-25 joueurs)',
        'roam': 'Roaming (1-10 joueurs)',
        None: 'Tous les contextes'
    }
    
    return {
        "last_updated": "Décembre 2025 (Live Data)",
        "context": context,
        "context_label": context_labels.get(context, 'Tous les contextes'),
        "fights_count": fights_count,
        "tier_s": tier_s,
        "tier_a": tier_a,
        "tier_b": tier_b,
        "tier_c": tier_c
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
