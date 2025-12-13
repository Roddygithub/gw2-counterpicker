#!/usr/bin/env python3
"""
Batch Import Script for GW2 CounterPicker
Imports all .zevtc/.evtc files from a folder to train the AI

Usage:
    python batch_import.py /path/to/logs/folder
    
This will:
1. Find all .zevtc and .evtc files in the folder
2. Upload each to dps.report for parsing
3. Record each fight in the AI database
4. Track processed files to allow resuming if interrupted
"""

import sys
import os
import asyncio
import httpx
import json
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from counter_ai import record_fight_for_learning, get_ai_status

DPS_REPORT_URL = "https://dps.report/uploadContent"
PROGRESS_FILE = "batch_import_progress.json"

def load_progress() -> dict:
    """Load progress from file to allow resuming"""
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {'processed_files': [], 'success_count': 0, 'fail_count': 0}

def save_progress(progress: dict):
    """Save progress to file"""
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f, indent=2)

async def upload_to_dps_report(file_path: Path) -> dict:
    """Upload a file to dps.report and get the JSON response"""
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            with open(file_path, 'rb') as f:
                files = {'file': (file_path.name, f, 'application/octet-stream')}
                data = {'json': '1'}
                
                response = await client.post(DPS_REPORT_URL, files=files, data=data)
                
                if response.status_code == 200:
                    result = response.json()
                    if 'permalink' in result:
                        return {'success': True, 'permalink': result['permalink'], 'id': result.get('id')}
                    else:
                        return {'success': False, 'error': result.get('error', 'Unknown error')}
                else:
                    return {'success': False, 'error': f'HTTP {response.status_code}'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

async def fetch_ei_json(permalink: str) -> dict:
    """Fetch the Elite Insights JSON from dps.report or wvw.report"""
    try:
        # Handle both dps.report and wvw.report URLs
        if 'wvw.report' in permalink:
            # wvw.report uses different API format
            # Extract the ID from permalink like https://wvw.report/tVBG-20251205-233553_wvw
            # Remove the _wvw suffix for the JSON API
            report_id = permalink.split('/')[-1].replace('_wvw', '')
            json_url = f"https://dps.report/getJson?id={report_id}"
        else:
            json_url = permalink.replace('https://dps.report/', 'https://dps.report/getJson?permalink=')
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(json_url)
            if response.status_code == 200:
                data = response.json()
                if 'error' in data:
                    return {'success': False, 'error': data['error']}
                return {'success': True, 'data': data}
            else:
                return {'success': False, 'error': f'HTTP {response.status_code}'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def extract_fight_data(ei_json: dict, source_name: str) -> dict:
    """Extract fight data from Elite Insights JSON for AI learning"""
    from main import extract_players_from_ei_json
    
    try:
        players_data = extract_players_from_ei_json(ei_json)
        players_data['source'] = 'dps_report'
        players_data['source_name'] = source_name
        return players_data
    except Exception as e:
        print(f"  Error extracting data: {e}")
        return None

async def process_file(file_path: Path, index: int, total: int) -> bool:
    """Process a single log file"""
    print(f"[{index}/{total}] Processing: {file_path.name}")
    
    # Upload to dps.report
    print(f"  Uploading to dps.report...")
    upload_result = await upload_to_dps_report(file_path)
    
    if not upload_result['success']:
        print(f"  ❌ Upload failed: {upload_result['error']}")
        return False
    
    permalink = upload_result['permalink']
    print(f"  ✓ Uploaded: {permalink}")
    
    # Wait a bit to avoid rate limiting
    await asyncio.sleep(2)
    
    # Fetch JSON
    print(f"  Fetching JSON...")
    json_result = await fetch_ei_json(permalink)
    
    if not json_result['success']:
        print(f"  ❌ JSON fetch failed: {json_result['error']}")
        return False
    
    # Extract fight data
    fight_data = extract_fight_data(json_result['data'], permalink)
    
    if not fight_data:
        print(f"  ❌ Data extraction failed")
        return False
    
    # Record for AI learning
    fight_id = record_fight_for_learning(fight_data)
    print(f"  ✓ Recorded: {fight_id} ({fight_data.get('fight_outcome', 'unknown')})")
    
    return True

async def main():
    if len(sys.argv) < 2:
        print("Usage: python batch_import.py /path/to/logs/folder")
        print("\nThis script imports all .zevtc and .evtc files to train the AI.")
        print("Progress is saved automatically - you can interrupt and resume later.")
        sys.exit(1)
    
    folder_path = Path(sys.argv[1])
    
    if not folder_path.exists():
        print(f"Error: Folder not found: {folder_path}")
        sys.exit(1)
    
    # Find all log files (recursively in subfolders)
    log_files = list(folder_path.rglob("*.zevtc")) + list(folder_path.rglob("*.evtc"))
    
    if not log_files:
        print(f"No .zevtc or .evtc files found in {folder_path}")
        sys.exit(1)
    
    # Load progress
    progress = load_progress()
    processed_set = set(progress['processed_files'])
    
    # Filter out already processed files
    remaining_files = [f for f in log_files if str(f) not in processed_set]
    
    print(f"=" * 60)
    print(f"GW2 CounterPicker - Batch Import")
    print(f"=" * 60)
    print(f"Folder: {folder_path}")
    print(f"Total files found: {len(log_files)}")
    print(f"Already processed: {len(processed_set)}")
    print(f"Remaining to process: {len(remaining_files)}")
    print(f"=" * 60)
    
    if not remaining_files:
        print("All files have already been processed!")
        print(f"Delete {PROGRESS_FILE} to start fresh.")
        sys.exit(0)
    
    # Show current AI status
    status = get_ai_status()
    print(f"Current AI status:")
    print(f"  - Total fights: {status['total_fights']}")
    print(f"  - Win rate: {status['win_rate']}%")
    print(f"=" * 60)
    
    # Process files
    success_count = progress['success_count']
    fail_count = progress['fail_count']
    
    for i, file_path in enumerate(remaining_files, 1):
        total_done = len(processed_set) + i
        try:
            if await process_file(file_path, total_done, len(log_files)):
                success_count += 1
            else:
                fail_count += 1
        except Exception as e:
            print(f"  ❌ Error: {e}")
            fail_count += 1
        
        # Save progress after each file
        progress['processed_files'].append(str(file_path))
        progress['success_count'] = success_count
        progress['fail_count'] = fail_count
        save_progress(progress)
        
        # Rate limiting
        if i < len(remaining_files):
            await asyncio.sleep(3)
    
    # Final summary
    print(f"\n" + "=" * 60)
    print(f"IMPORT COMPLETE")
    print(f"=" * 60)
    print(f"Successful: {success_count}")
    print(f"Failed: {fail_count}")
    
    # Show updated AI status
    status = get_ai_status()
    print(f"\nUpdated AI status:")
    print(f"  - Total fights: {status['total_fights']}")
    print(f"  - Win rate: {status['win_rate']}%")
    
    # Clean up progress file on completion
    if os.path.exists(PROGRESS_FILE):
        os.remove(PROGRESS_FILE)
        print(f"\nProgress file cleaned up.")

if __name__ == "__main__":
    asyncio.run(main())
