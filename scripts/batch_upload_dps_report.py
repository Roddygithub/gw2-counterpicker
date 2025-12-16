#!/usr/bin/env python3
"""
Batch upload WvW logs to dps.report and extract stats with kills.
Rate limited to avoid overloading the API.
Progress is saved so you can resume if interrupted.
"""
import os
import sys
import json
import time
import httpx
import asyncio
from pathlib import Path
from datetime import datetime
from tinydb import TinyDB, Query

# Configuration
LOGS_DIR = Path("/home/roddy/Téléchargements/Logs WvW")
PROGRESS_FILE = Path("data/batch_upload_progress.json")
DPS_REPORT_UPLOAD_URL = "https://dps.report/uploadContent"
DPS_REPORT_JSON_URL = "https://dps.report/getJson"
RATE_LIMIT_DELAY = 2.0  # Seconds between uploads (be nice to dps.report)
MAX_RETRIES = 3

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def collect_log_files():
    """Collect all .zevtc files sorted by date"""
    files = []
    for root, dirs, filenames in os.walk(LOGS_DIR):
        for f in filenames:
            if f.endswith('.zevtc') or f.endswith('.evtc'):
                filepath = Path(root) / f
                files.append({
                    'path': str(filepath),
                    'name': f,
                    'size': filepath.stat().st_size,
                    'mtime': filepath.stat().st_mtime,
                })
    return sorted(files, key=lambda x: x['mtime'])

def load_progress():
    """Load progress from file"""
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    return {
        'processed': {},  # filename -> result
        'stats': {
            'total_kills': 0,
            'total_deaths': 0,
            'total_damage': 0,
            'accounts': {},
        },
        'last_updated': None,
    }

def save_progress(progress):
    """Save progress to file"""
    progress['last_updated'] = datetime.now().isoformat()
    PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f, indent=2)

async def upload_to_dps_report(filepath: str, client: httpx.AsyncClient) -> dict:
    """Upload a file to dps.report and get JSON result"""
    try:
        with open(filepath, 'rb') as f:
            files = {'file': (Path(filepath).name, f, 'application/octet-stream')}
            data = {'json': '1'}  # Request JSON response
            
            response = await client.post(
                DPS_REPORT_UPLOAD_URL,
                files=files,
                data=data,
                timeout=60.0
            )
            
            if response.status_code != 200:
                return {'success': False, 'error': f'HTTP {response.status_code}'}
            
            result = response.json()
            permalink = result.get('permalink', '')
            
            if not permalink:
                return {'success': False, 'error': 'No permalink returned'}
            
            # Get JSON data
            await asyncio.sleep(0.5)  # Small delay before fetching JSON
            json_response = await client.get(
                f"{DPS_REPORT_JSON_URL}?permalink={permalink}",
                timeout=30.0
            )
            
            if json_response.status_code != 200:
                return {'success': False, 'error': f'JSON fetch failed: {json_response.status_code}'}
            
            json_data = json_response.json()
            
            # Extract player stats
            players = []
            for player in json_data.get('players', []):
                stats = player.get('statsAll', [{}])[0] if player.get('statsAll') else {}
                defenses = player.get('defenses', [{}])[0] if player.get('defenses') else {}
                support = player.get('support', [{}])[0] if player.get('support') else {}
                
                players.append({
                    'name': player.get('name', ''),
                    'account': player.get('account', ''),
                    'profession': player.get('profession', ''),
                    'kills': stats.get('killed', 0),
                    'deaths': defenses.get('deadCount', 0),
                    'downs': defenses.get('downCount', 0),
                    'damage': stats.get('totalDamage', 0),
                    'dps': stats.get('dps', 0),
                })
            
            return {
                'success': True,
                'permalink': permalink,
                'duration': json_data.get('duration', ''),
                'players': players,
                'enemies': len(json_data.get('targets', [])),
            }
            
    except httpx.TimeoutException:
        return {'success': False, 'error': 'Timeout'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

async def process_files(files: list, progress: dict, max_files: int = None):
    """Process files with rate limiting"""
    processed_count = 0
    error_count = 0
    skipped_count = 0
    
    files_to_process = files[:max_files] if max_files else files
    total = len(files_to_process)
    
    async with httpx.AsyncClient() as client:
        for i, file_info in enumerate(files_to_process):
            filename = file_info['name']
            filepath = file_info['path']
            
            # Skip if already processed
            if filename in progress['processed']:
                skipped_count += 1
                continue
            
            print(f"[{i+1}/{total}] Uploading {filename}...", end=' ', flush=True)
            
            # Upload with retries
            result = None
            for attempt in range(MAX_RETRIES):
                result = await upload_to_dps_report(filepath, client)
                if result['success']:
                    break
                if attempt < MAX_RETRIES - 1:
                    print(f"retry {attempt+2}...", end=' ', flush=True)
                    await asyncio.sleep(RATE_LIMIT_DELAY)
            
            if result['success']:
                processed_count += 1
                print(f"OK - {len(result['players'])} players")
                
                # Update stats
                for player in result['players']:
                    kills = player['kills']
                    deaths = player['deaths']
                    damage = player['damage']
                    account = player['account']
                    
                    progress['stats']['total_kills'] += kills
                    progress['stats']['total_deaths'] += deaths
                    progress['stats']['total_damage'] += damage
                    
                    if account:
                        if account not in progress['stats']['accounts']:
                            progress['stats']['accounts'][account] = {
                                'kills': 0, 'deaths': 0, 'damage': 0, 'fights': 0
                            }
                        progress['stats']['accounts'][account]['kills'] += kills
                        progress['stats']['accounts'][account]['deaths'] += deaths
                        progress['stats']['accounts'][account]['damage'] += damage
                        progress['stats']['accounts'][account]['fights'] += 1
                
                progress['processed'][filename] = {
                    'permalink': result['permalink'],
                    'players': len(result['players']),
                    'timestamp': datetime.now().isoformat(),
                }
            else:
                error_count += 1
                print(f"FAILED - {result['error']}")
                progress['processed'][filename] = {
                    'error': result['error'],
                    'timestamp': datetime.now().isoformat(),
                }
            
            # Save progress periodically
            if (i + 1) % 10 == 0:
                save_progress(progress)
            
            # Rate limiting
            await asyncio.sleep(RATE_LIMIT_DELAY)
    
    return processed_count, error_count, skipped_count

def print_stats(progress):
    """Print current stats"""
    stats = progress['stats']
    print(f"\n{'='*50}")
    print(f"Total kills: {stats['total_kills']}")
    print(f"Total deaths: {stats['total_deaths']}")
    print(f"Total damage: {stats['total_damage']:,}")
    print(f"Unique accounts: {len(stats['accounts'])}")
    
    if stats['accounts']:
        print(f"\nTop 10 accounts by kills:")
        sorted_accounts = sorted(
            stats['accounts'].items(),
            key=lambda x: x[1]['kills'],
            reverse=True
        )[:10]
        for acc, data in sorted_accounts:
            kd = data['kills'] / max(data['deaths'], 1)
            print(f"  {acc}: {data['kills']} kills, {data['deaths']} deaths, K/D={kd:.2f}")

async def main():
    print("=== Batch Upload to dps.report ===\n")
    
    # Collect files
    files = collect_log_files()
    print(f"Found {len(files)} log files")
    
    # Load progress
    progress = load_progress()
    already_processed = len(progress['processed'])
    print(f"Already processed: {already_processed}")
    print(f"Remaining: {len(files) - already_processed}")
    
    if already_processed > 0:
        print_stats(progress)
    
    # Check command line args
    max_files = None
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == '0':
            print("Cancelled.")
            return
        elif arg == 'all':
            max_files = None
        else:
            try:
                max_files = int(arg)
            except ValueError:
                max_files = None
    else:
        # Interactive mode
        print(f"\nRate limit: {RATE_LIMIT_DELAY}s between uploads")
        print("Estimated time for all remaining: ~{:.1f} hours".format(
            (len(files) - already_processed) * RATE_LIMIT_DELAY / 3600
        ))
        
        try:
            max_input = input("\nHow many files to process? (Enter for all, 0 to quit): ").strip()
            if max_input == '0':
                print("Cancelled.")
                return
            max_files = int(max_input) if max_input else None
        except (ValueError, EOFError):
            max_files = None
    
    # Process
    print(f"\nStarting upload... (max_files={max_files or 'all'})")
    processed, errors, skipped = await process_files(files, progress, max_files)
    
    # Save final progress
    save_progress(progress)
    
    print(f"\n{'='*50}")
    print(f"Processed: {processed}")
    print(f"Errors: {errors}")
    print(f"Skipped (already done): {skipped}")
    
    print_stats(progress)
    print(f"\nProgress saved to {PROGRESS_FILE}")

if __name__ == "__main__":
    asyncio.run(main())
