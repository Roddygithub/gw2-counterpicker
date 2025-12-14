"""
Script to re-import logs and update enemy_composition for existing fights.
Uses fingerprinting to match existing fights and update them instead of creating duplicates.
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from parser import RealEVTCParser
from counter_ai import fights_table, fights_db, counter_ai
from tinydb import Query


def generate_simple_fingerprint(duration_sec, ally_specs, ally_damage):
    """Generate a simple fingerprint for matching existing fights"""
    import hashlib
    
    duration_bucket = int(duration_sec // 5) * 5
    ally_specs_sorted = "_".join(sorted(ally_specs))
    damage_bucket = int(ally_damage // 50000) * 50000
    
    fingerprint_data = f"{duration_bucket}|{ally_specs_sorted}|{damage_bucket}"
    return hashlib.md5(fingerprint_data.encode()).hexdigest()[:16]


def find_matching_fight(duration_sec, ally_specs, ally_damage):
    """Find an existing fight that matches these parameters"""
    all_fights = fights_table.all()
    
    target_duration = int(duration_sec // 5) * 5
    target_damage = int(ally_damage // 50000) * 50000
    target_specs = set(ally_specs)
    
    for fight in all_fights:
        fight_duration = int(fight.get('duration_sec', 0) // 5) * 5
        fight_damage = int(fight.get('total_ally_damage', 0) // 50000) * 50000
        fight_specs = set(fight.get('ally_composition', {}).keys())
        
        # Match if duration, damage bucket, and specs are similar
        if (fight_duration == target_duration and 
            fight_damage == target_damage and
            len(target_specs & fight_specs) >= len(target_specs) * 0.7):  # 70% spec overlap
            return fight
    
    return None


def reimport_logs():
    """Re-import logs to update enemy_composition"""
    
    logs_dir = Path("/home/roddy/Téléchargements/Logs WvW")
    parser = RealEVTCParser()
    
    if not logs_dir.exists():
        print(f"ERROR: Logs directory not found: {logs_dir}")
        return
    
    # Find all .zevtc files
    log_files = list(logs_dir.rglob("*.zevtc"))
    print(f"Found {len(log_files)} log files")
    
    updated = 0
    skipped = 0
    errors = 0
    no_match = 0
    
    for i, log_file in enumerate(log_files):
        if i % 100 == 0:
            print(f"Processing {i}/{len(log_files)}...")
        
        try:
            # Parse the log
            # Parse the log file
            parsed = parser.parse_evtc_file(str(log_file))
            
            if not parsed or not parsed.players:
                skipped += 1
                continue
            
            # Extract data for matching
            duration_sec = parsed.duration_seconds
            ally_specs = [p.elite_spec or p.profession for p in parsed.players]
            ally_damage = sum(p.damage_dealt for p in parsed.players)
            
            # Find matching existing fight
            existing_fight = find_matching_fight(duration_sec, ally_specs, ally_damage)
            
            if existing_fight:
                # Check if enemy_composition is empty
                current_enemy_comp = existing_fight.get('enemy_composition', {})
                
                if not current_enemy_comp:
                    # Build enemy_composition from parsed log
                    enemy_comp = {}
                    for enemy in parsed.enemies:
                        spec = enemy.elite_spec or enemy.profession
                        if spec and spec != 'Unknown':
                            enemy_comp[spec] = enemy_comp.get(spec, 0) + 1
                    
                    if enemy_comp:
                        # Update the fight with enemy_composition
                        FightQuery = Query()
                        fights_table.update(
                            {'enemy_composition': enemy_comp},
                            FightQuery.fight_id == existing_fight['fight_id']
                        )
                        updated += 1
                    else:
                        skipped += 1
                else:
                    skipped += 1  # Already has enemy_composition
            else:
                no_match += 1
                
        except Exception as e:
            errors += 1
            if errors <= 5:
                print(f"Error parsing {log_file.name}: {e}")
    
    print(f"\n=== Re-import Complete ===")
    print(f"Total files: {len(log_files)}")
    print(f"Updated with enemy_composition: {updated}")
    print(f"Skipped (already had data or no enemies): {skipped}")
    print(f"No matching fight found: {no_match}")
    print(f"Errors: {errors}")
    
    # Show sample of updated fights
    print(f"\n=== Sample Updated Fights ===")
    sample_fights = [f for f in fights_table.all() if f.get('enemy_composition')][:3]
    for fight in sample_fights:
        print(f"Fight: {fight.get('fight_id')[:30]}...")
        print(f"  Enemy comp: {fight.get('enemy_composition')}")
        print()


if __name__ == "__main__":
    reimport_logs()
