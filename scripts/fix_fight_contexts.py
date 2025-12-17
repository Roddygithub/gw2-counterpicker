#!/usr/bin/env python3
"""
Fix fight contexts by applying auto-detection to all existing fights.

This script analyzes each fight and applies the detect_fight_context logic
to properly categorize fights as zerg, guild_raid, or roam.
"""

import sys
from pathlib import Path
from collections import Counter

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tinydb import TinyDB

FIGHTS_DB_PATH = Path("data/fights.db")


def detect_context(fight: dict) -> str:
    """
    Detect fight context based on player counts.
    
    Logic:
    - roam: 1-10 players total (allies + enemies)
    - guild_raid: 10-25 players total
    - zerg: 25+ players total
    """
    ally_count = fight.get('ally_count', 0)
    enemy_count = fight.get('enemy_count', 0)
    
    # Also check composition sizes if counts not available
    if ally_count == 0:
        ally_comp = fight.get('ally_composition', {})
        ally_count = sum(ally_comp.values()) if ally_comp else 0
    
    if enemy_count == 0:
        enemy_comp = fight.get('enemy_composition', {})
        enemy_count = sum(enemy_comp.values()) if enemy_comp else 0
    
    total = ally_count + enemy_count
    
    if total <= 10:
        return 'roam'
    elif total <= 25:
        return 'guild_raid'
    else:
        return 'zerg'


def main():
    print("=" * 60)
    print("Fix Fight Contexts - Auto-detection")
    print("=" * 60)
    
    if not FIGHTS_DB_PATH.exists():
        print(f"Error: {FIGHTS_DB_PATH} not found")
        return
    
    db = TinyDB(str(FIGHTS_DB_PATH))
    fights_table = db.table('fights')
    fights = fights_table.all()
    
    print(f"\nLoaded {len(fights)} fights")
    
    # Current distribution
    current_contexts = Counter(f.get('context', 'unknown') for f in fights)
    print(f"\nCurrent context distribution:")
    for ctx, count in sorted(current_contexts.items()):
        print(f"  - {ctx}: {count}")
    
    # Apply auto-detection
    updates = {'roam': 0, 'guild_raid': 0, 'zerg': 0}
    changes = 0
    
    for fight in fights:
        old_context = fight.get('context', 'unknown')
        new_context = detect_context(fight)
        
        if old_context != new_context:
            # Update the fight
            fights_table.update({'context': new_context}, doc_ids=[fight.doc_id])
            changes += 1
        
        updates[new_context] += 1
    
    print(f"\n✓ Applied auto-detection to all fights")
    print(f"  Changed: {changes} fights")
    
    # New distribution
    print(f"\nNew context distribution:")
    for ctx, count in sorted(updates.items()):
        print(f"  - {ctx}: {count}")
    
    # Show some examples
    print("\n" + "=" * 60)
    print("Sample fights by context:")
    print("=" * 60)
    
    # Reload to get updated data
    fights = fights_table.all()
    
    for ctx in ['roam', 'guild_raid', 'zerg']:
        ctx_fights = [f for f in fights if f.get('context') == ctx]
        if ctx_fights:
            sample = ctx_fights[0]
            ally_count = sample.get('ally_count', 0)
            enemy_count = sample.get('enemy_count', 0)
            enemy_comp = sample.get('enemy_composition', {})
            print(f"\n{ctx.upper()} example:")
            print(f"  Allies: {ally_count}, Enemies: {enemy_count}")
            print(f"  Enemy comp: {dict(list(enemy_comp.items())[:5])}")


if __name__ == "__main__":
    main()
