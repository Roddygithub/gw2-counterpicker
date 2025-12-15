"""
GW2 CounterPicker - The Ultimate WvW Intelligence Tool
"Le seul outil capable de lire dans l'âme de ton adversaire. Et dans celle de tout son serveur."

v3.0 - IA VIVANTE - Apprend de chaque fight uploadé
Powered by Llama 3.2 8B via Ollama

Made with rage, love and 15 years of WvW pain.
"""

import json
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from tinydb import TinyDB

from scheduler import setup_scheduled_tasks
from logger import get_logger

# Import routers
from routers import pages, analysis

# Setup logger
logger = get_logger('main')

# Initialize FastAPI app
app = FastAPI(
    title="GW2 CounterPicker",
    description="The most powerful WvW intelligence tool ever created - IA VIVANTE powered by Llama 3.2",
    version="3.0.0"
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configure templates
templates = Jinja2Templates(directory="templates")
templates.env.globals["app_version"] = app.version
templates.env.globals["offline_mode"] = True
templates.env.globals["ai_mode"] = True  # v3.0 IA VIVANTE

# Initialize scheduled tasks (fingerprint cleanup on Fridays at 18h55)
setup_scheduled_tasks()

# Import fight data if available (for deployment)
def import_deployed_data():
    """Import fight data from export file if database is empty"""
    from counter_ai import fights_table
    
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

# Include routers
app.include_router(pages.router, tags=["pages"])
app.include_router(analysis.router, tags=["analysis"])


# API endpoint for AI status
@app.get("/api/ai/status")
async def ai_status():
    """Get AI training status"""
    from counter_ai import get_ai_status
    return get_ai_status()


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {"status": "healthy", "version": app.version}


# Legacy helper functions that are still needed by services
# These will be imported by services/analysis_service.py
from role_detector import estimate_role_from_profession, detect_role_advanced

def extract_players_from_ei_json(log_data: dict) -> dict:
    """
    Extract player and enemy data from Elite Insights JSON format
    This function is kept in main.py as it's used by multiple services
    """
    players_data = {
        'allies': [],
        'allies_afk': [],
        'enemies': [],
        'fight_name': log_data.get('fightName', 'Unknown Fight'),
        'duration_sec': int(log_data.get('duration', '0s').replace('s', '').replace('m', '').split('.')[0]),
        'fight_outcome': 'unknown',
        'fight_stats': {},
        'composition': {},
        'enemy_composition': {}
    }
    
    # Extract players
    for player in log_data.get('players', []):
        if not player.get('notInSquad', False):
            role = detect_role_advanced(player)
            players_data['allies'].append({
                'name': player.get('name', 'Unknown'),
                'account': player.get('account', ''),
                'profession': player.get('profession', 'Unknown'),
                'group': player.get('group', 0),
                'role': role,
                'damage_out': player.get('dpsTargets', [{}])[0].get('damage', 0) if player.get('dpsTargets') else 0,
                'dps': player.get('dpsTargets', [{}])[0].get('dps', 0) if player.get('dpsTargets') else 0,
                'damage_in': player.get('defenses', [{}])[0].get('damageTaken', 0) if player.get('defenses') else 0,
                'damage_ratio': round(player.get('dpsTargets', [{}])[0].get('damage', 0) / max(player.get('defenses', [{}])[0].get('damageTaken', 1), 1), 2) if player.get('dpsTargets') and player.get('defenses') else 0,
                'deaths': player.get('defenses', [{}])[0].get('deadCount', 0) if player.get('defenses') else 0,
                'downs': player.get('defenses', [{}])[0].get('downCount', 0) if player.get('defenses') else 0,
                'kills': sum(target.get('killed', 0) for target in player.get('dpsTargets', [])),
                'cleanses': player.get('support', [{}])[0].get('condiCleanse', 0) if player.get('support') else 0,
                'boon_strips': player.get('support', [{}])[0].get('boonStrips', 0) if player.get('support') else 0,
                'healing': player.get('support', [{}])[0].get('healing', 0) if player.get('support') else 0,
                'barrier': player.get('support', [{}])[0].get('barrier', 0) if player.get('support') else 0,
                'resurrects': player.get('support', [{}])[0].get('resurrects', 0) if player.get('support') else 0,
                'down_contrib': player.get('statsTargets', [{}])[0].get('downContribution', 0) if player.get('statsTargets') else 0,
                'cc_out': player.get('statsTargets', [{}])[0].get('totalDamageCount', 0) if player.get('statsTargets') else 0,
            })
    
    # Extract enemies
    for target in log_data.get('targets', []):
        if target.get('enemyPlayer', False):
            role = estimate_role_from_profession(target.get('profession', 'Unknown'))
            players_data['enemies'].append({
                'name': target.get('name', 'Unknown'),
                'profession': target.get('profession', 'Unknown'),
                'damage_taken': target.get('healthPercentBurned', 0),
                'role': role,
            })
    
    # Build compositions
    ally_specs = {}
    ally_roles = {'dps': 0, 'dps_strip': 0, 'healer': 0, 'stab': 0, 'boon': 0}
    for p in players_data['allies']:
        spec = p['profession']
        ally_specs[spec] = ally_specs.get(spec, 0) + 1
        role = p.get('role', 'dps')
        if role in ally_roles:
            ally_roles[role] += 1
    
    enemy_specs = {}
    enemy_roles = {'dps': 0, 'dps_strip': 0, 'healer': 0, 'stab': 0, 'boon': 0}
    for e in players_data['enemies']:
        spec = e['profession']
        enemy_specs[spec] = enemy_specs.get(spec, 0) + 1
        role = e.get('role', 'dps')
        if role in enemy_roles:
            enemy_roles[role] += 1
    
    players_data['composition'] = {
        'spec_counts': ally_specs,
        'role_counts': ally_roles,
        'specs_by_role': {},
        'total_players': len(players_data['allies'])
    }
    
    players_data['enemy_composition'] = {
        'spec_counts': enemy_specs,
        'role_counts': enemy_roles,
        'total': len(players_data['enemies'])
    }
    
    # Determine fight outcome
    ally_deaths = sum(p.get('deaths', 0) for p in players_data['allies'])
    death_ratio = ally_deaths / max(len(players_data['allies']), 1)
    
    if death_ratio < 0.2:
        players_data['fight_outcome'] = 'victory'
    elif death_ratio > 0.6:
        players_data['fight_outcome'] = 'defeat'
    else:
        players_data['fight_outcome'] = 'draw'
    
    players_data['fight_stats'] = {
        'ally_deaths': ally_deaths,
        'ally_downs': sum(p.get('downs', 0) for p in players_data['allies']),
        'ally_damage': sum(p.get('damage_out', 0) for p in players_data['allies']),
        'ally_kills': sum(p.get('kills', 0) for p in players_data['allies']),
    }
    
    return players_data


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
