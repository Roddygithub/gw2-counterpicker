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
    
    # Supprimer la limite pour traiter tous les logs
    # MAX_LOGS = 50  # Ancienne limite
    
    print("Building log file index...")
    log_index = {}
    log_files = list(logs_dir.rglob("*.zevtc"))
    print(f"Found {len(log_files)} log files, processing all...")
    
    for log_file in log_files:
        ts = extract_timestamp_from_filename(log_file.name)
        if ts:
            log_index[ts] = log_file
    
    # Get all fights that need enemy_composition
    all_fights = fights_table.all()
    fights_needing_update = [f for f in all_fights if not f.get('enemy_composition')]
    print(f"Fights needing enemy_composition: {len(fights_needing_update)}")
    
    updated = 0
    no_log = 0
    parse_errors = 0
    no_enemies = 0
    processed = 0
    
    total_to_process = len(fights_needing_update)
    print(f"Starting to process all {total_to_process} fights...")
    
    for i, fight in enumerate(fights_needing_update):  # Traiter tous les combats
        processed += 1
        if i % 10 == 0 or i == total_to_process - 1:
            print(f"Processing {i+1}/{total_to_process} - Updated: {updated}, No log: {no_log}, No enemies: {no_enemies}, Errors: {parse_errors}")
        
        source_name = fight.get('source_name', '')
        if not source_name:
            no_log += 1
            continue
            
        ts = extract_timestamp_from_url(source_name)
        if not ts:
            no_log += 1
            continue
            
        if ts not in log_index:
            # Vérifier si le fichier existe avec un préfixe différent
            found = False
            for log_ts, log_file in log_index.items():
                if log_ts in source_name or source_name in str(log_file):
                    ts = log_ts
                    found = True
                    break
            if not found:
                no_log += 1
                continue
        
        log_file = log_index[ts]
        
        try:
            # Vérifier la taille du fichier d'abord
            file_size = log_file.stat().st_size / (1024 * 1024)  # Taille en Mo
            if file_size > 10:  # Ignorer les fichiers trop gros pour le test
                print(f"  Skipping large file: {log_file.name} ({file_size:.1f}MB)")
                continue
                
            print(f"  Parsing {log_file.name}...")
            parsed = parser.parse_evtc_file(str(log_file))
            
            # Debug: vérifier les joueurs et ennemis
            print(f"  Debug: Found {len(parsed.players)} players, {len(parsed.enemies)} enemies")
            if parsed.players:
                print(f"  Debug: First player team_id: {parsed.players[0].team_id}")
            
            if not parsed.enemies:
                print(f"  No enemies found in {log_file.name}")
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
                result = fights_table.update(
                    {'enemy_composition': enemy_comp},
                    FightQuery.fight_id == fight['fight_id']
                )
                if result:
                    updated += 1
                    print(f"  Updated fight {fight.get('fight_id', '')[:8]}... with {len(enemy_comp)} enemy specs")
                else:
                    print(f"  Failed to update fight {fight.get('fight_id', '')[:8]}...")
            else:
                print(f"  No valid enemy specs in {log_file.name}")
                no_enemies += 1
                
        except Exception as e:
            parse_errors += 1
            if parse_errors <= 10:  # Augmenter la limite d'erreurs affichées
                import traceback
                print(f"  Error parsing {log_file.name}: {str(e)}")
                print(f"  {traceback.format_exc().splitlines()[-1]}")
    
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
