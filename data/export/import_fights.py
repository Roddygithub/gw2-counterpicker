#!/usr/bin/env python3
"""
Import fight data from JSON to database
"""

import json
from pathlib import Path
from tinydb import TinyDB

def import_fights_from_json():
    """Import fights from JSON to database"""
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
