"""
Script to recalculate ally_composition from ally_builds for existing fights.
Note: enemy_composition cannot be reconstructed without original logs.
"""

from counter_ai import fights_table, fights_db
from tinydb import Query


def recalculate_compositions():
    """Recalculate ally_composition from ally_builds"""
    
    all_fights = fights_table.all()
    print(f"Found {len(all_fights)} fights to process")
    
    updated = 0
    
    for fight in all_fights:
        fight_id = fight.get('fight_id')
        ally_builds = fight.get('ally_builds', [])
        current_ally_comp = fight.get('ally_composition', {})
        
        # Rebuild ally_composition from ally_builds
        new_ally_comp = {}
        for build in ally_builds:
            spec = build.get('profession', build.get('elite_spec', 'Unknown'))
            if spec and spec != 'Unknown':
                new_ally_comp[spec] = new_ally_comp.get(spec, 0) + 1
        
        # Update if different or empty
        if new_ally_comp and new_ally_comp != current_ally_comp:
            FightQuery = Query()
            fights_table.update({'ally_composition': new_ally_comp}, FightQuery.fight_id == fight_id)
            updated += 1
    
    print(f"\n=== Composition Recalculation Complete ===")
    print(f"Total fights: {len(all_fights)}")
    print(f"Updated ally_composition: {updated}")
    print(f"\nNote: enemy_composition cannot be reconstructed without original log files.")
    print(f"New uploads will have correct enemy_composition.")


if __name__ == "__main__":
    recalculate_compositions()
