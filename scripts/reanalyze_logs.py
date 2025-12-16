#!/usr/bin/env python3
"""
Script to re-analyze all WvW logs and rebuild stats with kills data.
"""
import os
import sys
from pathlib import Path
from tinydb import TinyDB, Query
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from parser import RealEVTCParser

LOGS_DIR = Path("/home/roddy/Téléchargements/Logs WvW")
DATA_DIR = Path("data")

def collect_log_files():
    """Collect all .zevtc and .evtc files"""
    files = []
    for root, dirs, filenames in os.walk(LOGS_DIR):
        for f in filenames:
            if f.endswith('.zevtc') or f.endswith('.evtc'):
                files.append(Path(root) / f)
    return sorted(files, key=lambda x: x.stat().st_mtime)

def analyze_file(filepath: Path, parser: RealEVTCParser):
    """Analyze a single file and extract stats"""
    try:
        with open(filepath, 'rb') as f:
            data = f.read()
        
        parsed = parser.parse_evtc_bytes(data, filepath.name)
        
        # Extract stats from players
        stats = []
        for player in parsed.players:
            stats.append({
                'name': player.character_name,
                'account': player.account_name,
                'profession': player.elite_spec or player.profession,
                'kills': player.kills or 0,
                'deaths': player.deaths or 0,
                'damage': player.damage_dealt or 0,
                'healing': player.healing_done or 0,
                'role': player.estimated_role.lower() if player.estimated_role else 'dps',
            })
        
        return {
            'success': True,
            'duration': parsed.duration_seconds,
            'players': stats,
            'enemies': len(parsed.enemies),
            'timestamp': filepath.stat().st_mtime,
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}

def main():
    print("=== Re-analyze WvW Logs ===\n")
    
    # Collect files
    files = collect_log_files()
    print(f"Found {len(files)} log files")
    
    if not files:
        print("No files found!")
        return
    
    # Initialize parser
    parser = RealEVTCParser()
    
    # Process files
    success_count = 0
    error_count = 0
    total_kills = 0
    total_deaths = 0
    account_stats = {}
    
    for i, filepath in enumerate(files):
        if i % 100 == 0:
            print(f"Processing {i}/{len(files)}...")
        
        result = analyze_file(filepath, parser)
        
        if result['success']:
            success_count += 1
            for player in result['players']:
                kills = player['kills']
                deaths = player['deaths']
                total_kills += kills
                total_deaths += deaths
                
                account = player.get('account', '')
                if account:
                    acc_lower = account.lower()
                    if acc_lower not in account_stats:
                        account_stats[acc_lower] = {
                            'account': account,
                            'kills': 0,
                            'deaths': 0,
                            'fights': 0,
                            'damage': 0,
                        }
                    account_stats[acc_lower]['kills'] += kills
                    account_stats[acc_lower]['deaths'] += deaths
                    account_stats[acc_lower]['fights'] += 1
                    account_stats[acc_lower]['damage'] += player['damage']
        else:
            error_count += 1
    
    print(f"\n=== Results ===")
    print(f"Processed: {success_count} success, {error_count} errors")
    print(f"Total kills extracted: {total_kills}")
    print(f"Total deaths extracted: {total_deaths}")
    print(f"Unique accounts: {len(account_stats)}")
    
    # Show top accounts
    sorted_accounts = sorted(account_stats.items(), key=lambda x: x[1]['kills'], reverse=True)
    print(f"\nTop 10 accounts by kills:")
    for acc, stats in sorted_accounts[:10]:
        kd = stats['kills'] / max(stats['deaths'], 1)
        print(f"  {stats['account']}: {stats['kills']} kills, {stats['deaths']} deaths, K/D={kd:.2f}")

if __name__ == "__main__":
    main()
