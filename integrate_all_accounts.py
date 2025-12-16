#!/usr/bin/env python3
"""
Integrate ALL accounts from dps.report batch upload into aggregated stats
"""
import json
from pathlib import Path
from tinydb import TinyDB, Query
import sys

def main():
    print("=== Intégration de TOUS les comptes dps.report ===\n")
    
    # Load dps.report stats
    progress_file = Path("data/batch_upload_progress.json")
    with open(progress_file, 'r') as f:
        progress = json.load(f)
    
    dps_stats = progress['stats']['accounts']
    total_accounts = len(dps_stats)
    print(f"Comptes à intégrer: {total_accounts}")
    
    # Open DB
    db = TinyDB("data/player_stats.json")
    aggregated_table = db.table('aggregated_career_stats')
    
    # Process with progress
    for i, (acc, stats) in enumerate(dps_stats.items(), 1):
        if i % 100 == 0 or i == total_accounts:
            print(f"\rProgression: {i}/{total_accounts} ({i*100/total_accounts:.1f}%)", end='', flush=True)
        
        record = {
            'account_name': acc,
            'total_fights': stats['fights'],
            'total_kills': stats['kills'],
            'total_deaths': stats['deaths'],
            'total_damage': stats['damage'],
            'kd_ratio': round(stats['kills'] / max(stats['deaths'], 1), 2),
            'avg_kills_per_fight': round(stats['kills'] / max(stats['fights'], 1), 2),
            'source': 'dps.report'
        }
        
        Q = Query()
        aggregated_table.upsert(record, Q.account_name == acc)
    
    db.close()
    
    print(f"\n\n✓ Terminé! {total_accounts} comptes intégrés")
    
    # Verify
    db2 = TinyDB("data/player_stats.json")
    agg = db2.table('aggregated_career_stats')
    print(f"Total dans la table: {len(agg.all())}")
    
    # Show top 10
    top = sorted(agg.all(), key=lambda x: x.get('total_kills', 0), reverse=True)[:10]
    print("\nTop 10 par kills:")
    for i, t in enumerate(top, 1):
        print(f"  {i:2d}. {t['account_name']}: {t['total_kills']:4d} kills, {t['total_deaths']:4d} deaths, K/D={t['kd_ratio']:5.2f}")
    
    db2.close()

if __name__ == "__main__":
    main()
