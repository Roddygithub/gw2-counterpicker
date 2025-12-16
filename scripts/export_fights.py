#!/usr/bin/env python3
"""
Export fight data from local database to JSON for deployment
"""

import json
from pathlib import Path
from tinydb import TinyDB

def export_fights_to_json():
    """Export all fights with enemy_composition to JSON"""
    db = TinyDB('data/fights.db')
    fights = db.table('fights')
    
    # Filter fights with enemy_composition
    fights_with_composition = [
        fight for fight in fights.all() 
        if 'enemy_composition' in fight and fight['enemy_composition']
    ]
    
    # Create export directory
    export_dir = Path('data/export')
    export_dir.mkdir(exist_ok=True)
    
    # Save to JSON
    with open(export_dir / 'fights_export.json', 'w') as f:
        json.dump(fights_with_composition, f, indent=2)
    
    print(f"Exported {len(fights_with_composition)} fights to data/export/fights_export.json")
    
    # Create import script
    import_script = """#!/usr/bin/env python3
\"\"\"
Import fight data from JSON to database
\"\"\"

import json
from pathlib import Path
from tinydb import TinyDB

def import_fights_from_json():
    \"\"\"Import fights from JSON to database\"\"\"
    # Check if export file exists
    export_file = Path('data/export/fights_export.json')
    if not export_file.exists():
        print("No export file found, starting with empty database")
        return
    
    # Load exported data
    with open(export_file) as f:
        fights = json.load(f)
    
    # Import to database
    db = TinyDB('data/fights.db')
    fights_table = db.table('fights')
    
    # Clear existing data and import
    fights_table.truncate()
    fights_table.insert_multiple(fights)
    
    print(f"Imported {len(fights)} fights to database")

if __name__ == "__main__":
    import_fights_from_json()
"""
    
    with open(export_dir / 'import_fights.py', 'w') as f:
        f.write(import_script)
    
    print("Created import script at data/export/import_fights.py")

if __name__ == "__main__":
    export_fights_to_json()
