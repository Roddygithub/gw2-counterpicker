#!/usr/bin/env python3
"""
Script to recalculate player stats from fights database.
This fixes the kills=0 issue by recalculating from recent fights that have kills data.
"""
from tinydb import TinyDB, Query
from pathlib import Path
from datetime import datetime

def recalculate_player_stats():
    """Recalculate player stats from fights database"""
    # Load fights from AI database
    fights_db = TinyDB('data/fights.db')
    fights_table = fights_db.table('fights')
    
    # Load player stats database
    player_db = TinyDB('data/player_stats.json')
    player_fights_table = player_db.table('fights')
    
    all_fights = fights_table.all()
    print(f"Total fights in AI database: {len(all_fights)}")
    
    # Count fights with kills data
    fights_with_kills = [f for f in all_fights if any(a.get('kills', 0) > 0 for a in f.get('ally_builds', []))]
    print(f"Fights with kills data: {len(fights_with_kills)}")
    
    # Collect stats per account
    account_stats = {}
    
    for fight in all_fights:
        ally_builds = fight.get('ally_builds', [])
        fight_outcome = fight.get('outcome', 'draw')
        duration = fight.get('duration_sec', 0)
        enemy_count = sum(fight.get('enemy_composition', {}).values())
        ally_count = len(ally_builds)
        timestamp = fight.get('timestamp', '')
        
        for ally in ally_builds:
            account = ally.get('account', '')
            if not account:
                continue
            
            account_lower = account.lower()
            
            if account_lower not in account_stats:
                account_stats[account_lower] = {
                    'account_name': account,
                    'fights': [],
                    'total_kills': 0,
                    'total_deaths': 0,
                    'total_damage': 0,
                    'total_healing': 0,
                }
            
            kills = ally.get('kills', 0)
            deaths = ally.get('deaths', 0)
            damage = ally.get('damage_out', ally.get('dps', 0) * max(duration, 1))
            healing = ally.get('healing', 0)
            
            account_stats[account_lower]['total_kills'] += kills
            account_stats[account_lower]['total_deaths'] += deaths
            account_stats[account_lower]['total_damage'] += damage
            account_stats[account_lower]['total_healing'] += healing
            account_stats[account_lower]['fights'].append({
                'timestamp': timestamp,
                'outcome': fight_outcome,
                'kills': kills,
                'deaths': deaths,
                'damage': damage,
                'spec': ally.get('elite_spec', ally.get('profession', '')),
                'role': ally.get('role', 'dps'),
            })
    
    print(f"\nUnique accounts found: {len(account_stats)}")
    
    # Show top accounts by kills
    sorted_accounts = sorted(account_stats.items(), key=lambda x: x[1]['total_kills'], reverse=True)
    print("\nTop 10 accounts by kills:")
    for acc, stats in sorted_accounts[:10]:
        kd = stats['total_kills'] / max(stats['total_deaths'], 1)
        print(f"  {stats['account_name']}: {stats['total_kills']} kills, {stats['total_deaths']} deaths, K/D={kd:.2f}, {len(stats['fights'])} fights")
    
    # Option to update player_stats database
    print("\n" + "="*50)
    response = input("Do you want to update player_stats.json with recalculated data? (y/n): ")
    
    if response.lower() == 'y':
        # Clear and rebuild player fights table
        player_fights_table.truncate()
        
        inserted = 0
        for account_lower, stats in account_stats.items():
            for fight in stats['fights']:
                record = {
                    'account_id': account_lower,
                    'account_name': stats['account_name'],
                    'character_name': stats['account_name'].split('.')[0],
                    'profession': fight['spec'],
                    'elite_spec': fight['spec'],
                    'role': fight['role'],
                    'fight_date': fight['timestamp'],
                    'fight_duration': 60,  # Default
                    'damage_out': fight['damage'],
                    'damage_in': 0,
                    'kills': fight['kills'],
                    'deaths': fight['deaths'],
                    'downs': 0,
                    'cleanses': 0,
                    'strips': 0,
                    'healing': 0,
                    'barrier': 0,
                    'boon_uptime': {},
                    'outcome': fight['outcome'],
                    'enemy_count': 0,
                    'ally_count': 0,
                    'map_name': '',
                    'dps': fight['damage'] // 60,
                }
                player_fights_table.insert(record)
                inserted += 1
        
        print(f"Inserted {inserted} fight records")
        print("Done! Refresh the page to see updated stats.")
    else:
        print("Cancelled. No changes made.")

if __name__ == "__main__":
    recalculate_player_stats()
