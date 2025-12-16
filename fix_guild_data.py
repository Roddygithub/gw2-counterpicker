#!/usr/bin/env python3
"""
Script to fix corrupted guild data and reset stats.
Run this once to clean up the incorrect guild_stats data.
"""
from tinydb import TinyDB, Query
from pathlib import Path

def fix_guild_stats():
    """Clear corrupted guild stats data"""
    db_path = Path("data/player_stats.json")
    if not db_path.exists():
        print("Database not found")
        return
    
    db = TinyDB(str(db_path))
    guild_stats = db.table('guild_stats')
    
    # Check current state
    total = len(guild_stats.all())
    unique_guilds = set(r.get('guild_id') for r in guild_stats.all())
    
    print(f"Current state: {total} records, {len(unique_guilds)} unique guild(s)")
    print(f"Guild IDs: {unique_guilds}")
    
    if len(unique_guilds) <= 1 and total > 100:
        print("\nDetected corrupted data (all records have same guild_id)")
        print("Clearing guild_stats table...")
        guild_stats.truncate()
        print("Done! Guild stats cleared. Users can re-import for their specific guilds.")
    else:
        print("\nData looks OK or already cleaned")

def show_player_stats():
    """Show player stats summary"""
    db_path = Path("data/player_stats.json")
    if not db_path.exists():
        print("Database not found")
        return
    
    db = TinyDB(str(db_path))
    fights = db.table('fights')
    
    total = len(fights.all())
    print(f"\nPlayer fights: {total} records")
    
    if total > 0:
        # Check kills
        total_kills = sum(f.get('kills', 0) for f in fights.all())
        total_deaths = sum(f.get('deaths', 0) for f in fights.all())
        print(f"Total kills in DB: {total_kills}")
        print(f"Total deaths in DB: {total_deaths}")
        
        # Sample accounts
        accounts = set(f.get('account_name', '') for f in fights.all())
        print(f"Unique accounts: {len(accounts)}")

if __name__ == "__main__":
    print("=== GW2 CounterPicker Data Fix ===\n")
    fix_guild_stats()
    show_player_stats()
