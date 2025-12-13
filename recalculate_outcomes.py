"""
Script to recalculate fight outcomes based on the new kill/death ratio logic.
Run this once after updating the outcome calculation.
"""

from counter_ai import fights_table, fights_db
from tinydb import Query


def recalculate_outcomes():
    """Recalculate outcomes for all existing fights"""
    
    all_fights = fights_table.all()
    print(f"Found {len(all_fights)} fights to recalculate")
    
    updated = 0
    victories = 0
    defeats = 0
    draws = 0
    
    for fight in all_fights:
        fight_id = fight.get('fight_id')
        ally_deaths = fight.get('ally_deaths', 0)
        ally_kills = fight.get('ally_kills', 0)
        ally_damage = fight.get('total_ally_damage', 0)
        enemy_damage = fight.get('total_enemy_damage', 0)  # Damage we dealt to enemies
        old_outcome = fight.get('outcome', 'unknown')
        
        # For existing data without kills, use damage ratio as proxy
        # If we dealt significantly more damage than we took deaths, likely a win
        if ally_kills > 0:
            # New data with kills - use K/D ratio
            if ally_kills > 0 and ally_deaths == 0:
                new_outcome = 'victory'
            elif ally_kills > ally_deaths:
                new_outcome = 'victory'
            elif ally_deaths > ally_kills * 2 and ally_deaths >= 3:
                new_outcome = 'defeat'
            elif ally_deaths > ally_kills and ally_deaths >= 5:
                new_outcome = 'defeat'
            else:
                new_outcome = 'draw'
        else:
            # Legacy data - use damage/death heuristic
            # Good fight: low deaths AND high damage output
            # Bad fight: high deaths
            ally_count = sum(fight.get('ally_composition', {}).values()) or 1
            deaths_per_player = ally_deaths / ally_count
            
            if ally_deaths == 0:
                new_outcome = 'victory'  # No deaths = likely win
            elif ally_deaths <= 2 and ally_damage > 100000:
                new_outcome = 'victory'  # Low deaths, good damage
            elif deaths_per_player >= 0.8:  # 80%+ of squad died
                new_outcome = 'defeat'
            elif ally_deaths >= 5:
                new_outcome = 'defeat'
            elif ally_deaths <= 3:
                new_outcome = 'draw'  # Close fight
            else:
                new_outcome = 'draw'
        
        # Update if different
        if new_outcome != old_outcome:
            FightQuery = Query()
            fights_table.update({'outcome': new_outcome}, FightQuery.fight_id == fight_id)
            updated += 1
        
        # Count outcomes
        if new_outcome == 'victory':
            victories += 1
        elif new_outcome == 'defeat':
            defeats += 1
        else:
            draws += 1
    
    # Update global stats
    stats_table = fights_db.table('stats')
    total_fights = len(all_fights)
    win_rate = round((victories / total_fights * 100), 1) if total_fights > 0 else 0
    
    stats_table.truncate()
    stats_table.insert({
        'total_fights': total_fights,
        'victories': victories,
        'defeats': defeats,
        'draws': draws,
        'win_rate': win_rate,
        'last_updated': __import__('datetime').datetime.now().isoformat()
    })
    
    print(f"\n=== Recalculation Complete ===")
    print(f"Total fights: {total_fights}")
    print(f"Updated: {updated}")
    print(f"Victories: {victories} ({victories/total_fights*100:.1f}%)")
    print(f"Defeats: {defeats} ({defeats/total_fights*100:.1f}%)")
    print(f"Draws: {draws} ({draws/total_fights*100:.1f}%)")
    print(f"New win rate: {win_rate}%")


if __name__ == "__main__":
    recalculate_outcomes()
