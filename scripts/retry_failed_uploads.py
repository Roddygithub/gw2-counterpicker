#!/usr/bin/env python3
"""
Retry failed uploads (HTTP 429 rate limit errors only).
Uses longer delays to avoid rate limiting.
"""
import json
import asyncio
import httpx
from pathlib import Path
from datetime import datetime

PROGRESS_FILE = Path("data/batch_upload_progress.json")
LOGS_DIR = Path("/home/roddy/Téléchargements/Logs WvW")
DPS_REPORT_UPLOAD_URL = "https://dps.report/uploadContent"
DPS_REPORT_JSON_URL = "https://dps.report/getJson"
RATE_LIMIT_DELAY = 5.0  # Longer delay for retries

def load_progress():
    with open(PROGRESS_FILE, 'r') as f:
        return json.load(f)

def save_progress(progress):
    progress['last_updated'] = datetime.now().isoformat()
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f, indent=2)

def find_file(filename):
    """Find file in logs directory"""
    for root, dirs, files in __import__('os').walk(LOGS_DIR):
        if filename in files:
            return Path(root) / filename
    return None

async def upload_to_dps_report(filepath: str, client: httpx.AsyncClient) -> dict:
    try:
        with open(filepath, 'rb') as f:
            files = {'file': (Path(filepath).name, f, 'application/octet-stream')}
            data = {'json': '1'}
            
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
            
            await asyncio.sleep(0.5)
            json_response = await client.get(
                f"{DPS_REPORT_JSON_URL}?permalink={permalink}",
                timeout=30.0
            )
            
            if json_response.status_code != 200:
                return {'success': False, 'error': f'JSON fetch failed: {json_response.status_code}'}
            
            json_data = json_response.json()
            
            players = []
            for player in json_data.get('players', []):
                stats = player.get('statsAll', [{}])[0] if player.get('statsAll') else {}
                defenses = player.get('defenses', [{}])[0] if player.get('defenses') else {}
                
                players.append({
                    'name': player.get('name', ''),
                    'account': player.get('account', ''),
                    'profession': player.get('profession', ''),
                    'kills': stats.get('killed', 0),
                    'deaths': defenses.get('deadCount', 0),
                    'damage': stats.get('totalDamage', 0),
                })
            
            return {
                'success': True,
                'permalink': permalink,
                'players': players,
            }
            
    except Exception as e:
        return {'success': False, 'error': str(e)}

async def main():
    print("=== Retry Failed Uploads (429 errors) ===\n")
    
    progress = load_progress()
    
    # Find 429 errors
    failed_429 = [
        filename for filename, data in progress['processed'].items()
        if 'error' in data and '429' in data.get('error', '')
    ]
    
    print(f"Found {len(failed_429)} files with 429 errors")
    
    if not failed_429:
        print("Nothing to retry!")
        return
    
    print(f"Using {RATE_LIMIT_DELAY}s delay between uploads")
    print(f"Estimated time: ~{len(failed_429) * RATE_LIMIT_DELAY / 60:.1f} minutes\n")
    
    success_count = 0
    still_failed = 0
    
    async with httpx.AsyncClient() as client:
        for i, filename in enumerate(failed_429):
            filepath = find_file(filename)
            if not filepath:
                print(f"[{i+1}/{len(failed_429)}] {filename} - FILE NOT FOUND")
                continue
            
            print(f"[{i+1}/{len(failed_429)}] {filename}...", end=' ', flush=True)
            
            result = await upload_to_dps_report(str(filepath), client)
            
            if result['success']:
                success_count += 1
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
                still_failed += 1
                print(f"FAILED - {result['error']}")
            
            if (i + 1) % 10 == 0:
                save_progress(progress)
            
            await asyncio.sleep(RATE_LIMIT_DELAY)
    
    save_progress(progress)
    
    print(f"\n=== Results ===")
    print(f"Recovered: {success_count}")
    print(f"Still failed: {still_failed}")
    print(f"Total kills now: {progress['stats']['total_kills']}")

if __name__ == "__main__":
    asyncio.run(main())
