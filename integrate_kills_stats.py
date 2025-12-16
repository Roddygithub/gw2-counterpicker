#!/usr/bin/env python3
"""
Integrate kills stats from dps.report batch upload into player_stats.json
"""
import json
from pathlib import Path
from tinydb import TinyDB, Query

PROGRESS_FILE = Path("data/batch_upload_progress.json")
PLAYER_STATS_FILE = Path("data/player_stats.json")

def main():
    print("=== Intégration des stats kills dans player_stats.json ===\n")
    
    # Load batch upload progress
    with open(PROGRESS_FILE, 'r') as f:
        progress = json.load(f)
    
    dps_stats = progress['stats']['accounts']
    print(f"Stats dps.report: {len(dps_stats)} comptes, {progress['stats']['total_kills']} kills")
    
    # Open player stats DB
    db = TinyDB(str(PLAYER_STATS_FILE))
    fights_table = db.table('fights')
    
    all_fights = fights_table.all()
    print(f"Combats dans player_stats.json: {len(all_fights)}")
    
    # Get unique accounts in fights table
    accounts_in_db = set()
    for fight in all_fights:
        acc = fight.get('account_name', '')
        if acc:
            accounts_in_db.add(acc)
    
    print(f"Comptes uniques dans fights: {len(accounts_in_db)}")
    
    # Find matching accounts
    matched = accounts_in_db & set(dps_stats.keys())
    print(f"Comptes avec données dps.report: {len(matched)}")
    
    if not matched:
        print("\nAucun compte correspondant trouvé!")
        return
    
    # Show stats for matched accounts
    print("\n=== Stats par compte ===")
    for acc in sorted(matched):
        dps = dps_stats[acc]
        # Count fights in DB for this account
        db_fights = [f for f in all_fights if f.get('account_name') == acc]
        db_kills = sum(f.get('kills', 0) for f in db_fights)
        db_deaths = sum(f.get('deaths', 0) for f in db_fights)
        
        print(f"\n{acc}:")
        print(f"  DB actuel: {len(db_fights)} fights, {db_kills} kills, {db_deaths} deaths")
        print(f"  dps.report: {dps['fights']} fights, {dps['kills']} kills, {dps['deaths']} deaths")
    
    # Option 1: Update existing fights with kills data
    # This is complex because we'd need to match fights by timestamp
    
    # Option 2: Create a separate aggregated stats table
    # This is simpler and more reliable
    
    print("\n=== Création table stats agrégées ===")
    
    aggregated_table = db.table('aggregated_career_stats')
    
    for acc in matched:
        dps = dps_stats[acc]
        
        # Get additional info from fights
        db_fights = [f for f in all_fights if f.get('account_name') == acc]
        
        # Calculate specs played
        specs_played = {}
        roles_played = {}
        total_damage = 0
        total_duration = 0
        victories = 0
        defeats = 0
        
        for f in db_fights:
            spec = f.get('elite_spec') or f.get('profession', 'Unknown')
            specs_played[spec] = specs_played.get(spec, 0) + 1
            
            role = f.get('role', 'Unknown')
            roles_played[role] = roles_played.get(role, 0) + 1
            
            total_damage += f.get('damage_out', 0)
            total_duration += f.get('fight_duration', 0)
            
            if f.get('outcome') == 'victory':
                victories += 1
            elif f.get('outcome') == 'defeat':
                defeats += 1
        
        # Use dps.report kills/deaths (more accurate)
        record = {
            'account_name': acc,
            'total_fights': dps['fights'],
            'total_kills': dps['kills'],
            'total_deaths': dps['deaths'],
            'total_damage': dps['damage'],
            'total_victories': victories,
            'total_defeats': defeats,
            'total_duration': total_duration,
            'specs_played': specs_played,
            'roles_played': roles_played,
            'kd_ratio': round(dps['kills'] / max(dps['deaths'], 1), 2),
            'avg_kills_per_fight': round(dps['kills'] / max(dps['fights'], 1), 2),
            'source': 'dps.report'
        }
        
        # Upsert
        Q = Query()
        aggregated_table.upsert(record, Q.account_name == acc)
    
    print(f"Stats agrégées créées pour {len(matched)} comptes")
    
    # Show final stats for main user
    main_user = 'esskape.5047'
    if main_user in matched:
        Q = Query()
        user_stats = aggregated_table.get(Q.account_name == main_user)
        print(f"\n=== Stats finales pour {main_user} ===")
        print(f"  Kills: {user_stats['total_kills']}")
        print(f"  Deaths: {user_stats['total_deaths']}")
        print(f"  K/D: {user_stats['kd_ratio']}")
        print(f"  Fights: {user_stats['total_fights']}")
    
    db.close()
    print("\n✓ Intégration terminée!")

if __name__ == "__main__":
    main()
