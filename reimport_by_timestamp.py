"""
Script to update enemy_composition by matching log timestamps with fight source_names.
"""

import re
from pathlib import Path
from parser import RealEVTCParser
from counter_ai import fights_table
from tinydb import Query


def extract_timestamp_from_url(url):
    """Extract timestamp like 20251205-233553 from wvw.report URL"""
    match = re.search(r'(\d{8}-\d{6})', url)
    return match.group(1) if match else None


def extract_timestamp_from_filename(filename):
    """Extract timestamp from filename like 20251205-233553.zevtc"""
    match = re.search(r'(\d{8}-\d{6})', filename)
    return match.group(1) if match else None


def main():
    logs_dir = Path("/home/roddy/Téléchargements/Logs WvW")
    parser = RealEVTCParser()
    
    # Build index of log files by timestamp
    print("Building log file index...")
    log_index = {}
    for log_file in logs_dir.rglob("*.zevtc"):
        ts = extract_timestamp_from_filename(log_file.name)
        if ts:
            log_index[ts] = log_file
    print(f"Found {len(log_index)} unique timestamps in logs")
    
    # Get all fights that need enemy_composition
    all_fights = fights_table.all()
    fights_needing_update = [f for f in all_fights if not f.get('enemy_composition')]
    print(f"Fights needing enemy_composition: {len(fights_needing_update)}")
    
    updated = 0
    no_log = 0
    parse_errors = 0
    no_enemies = 0
    
    for i, fight in enumerate(fights_needing_update):
        if i % 100 == 0:
            print(f"Processing {i}/{len(fights_needing_update)}...")
        
        source_name = fight.get('source_name', '')
        ts = extract_timestamp_from_url(source_name)
        
        if not ts or ts not in log_index:
            no_log += 1
            continue
        
        log_file = log_index[ts]
        
        try:
            parsed = parser.parse_evtc_file(str(log_file))
            
            if not parsed.enemies:
                no_enemies += 1
                continue
            
            # Build enemy_composition
            enemy_comp = {}
            for e in parsed.enemies:
                spec = e.elite_spec or e.profession
                if spec and spec != 'Unknown':
                    enemy_comp[spec] = enemy_comp.get(spec, 0) + 1
            
            if enemy_comp:
                FightQuery = Query()
                fights_table.update(
                    {'enemy_composition': enemy_comp},
                    FightQuery.fight_id == fight['fight_id']
                )
                updated += 1
            else:
                no_enemies += 1
                
        except Exception as e:
            parse_errors += 1
            if parse_errors <= 5:
                print(f"  Error parsing {log_file.name}: {e}")
    
    print(f"\n=== Update Complete ===")
    print(f"Updated: {updated}")
    print(f"No matching log: {no_log}")
    print(f"No enemies found: {no_enemies}")
    print(f"Parse errors: {parse_errors}")
    
    # Verify
    with_enemies = sum(1 for f in fights_table.all() if f.get('enemy_composition'))
    print(f"\nTotal fights with enemy_composition: {with_enemies}")


if __name__ == "__main__":
    main()
