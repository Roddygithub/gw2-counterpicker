#!/usr/bin/env python3
"""
Fetch GW2 API data for specializations, skills, traits, and professions.
Creates a local reference file (gw2_data.json) for fine-tuning and prompt enrichment.

This script downloads data ONCE from the official GW2 API and stores it locally.
The data is then used to:
1. Enrich the fine-tuning dataset with real game mechanics
2. Provide context in prompts during inference

Usage:
    python scripts/fetch_gw2_api_data.py

Output:
    data/gw2_data.json - Complete reference data
    data/gw2_wvw_specs.json - WvW-focused specialization data
"""

import json
import httpx
import time
from pathlib import Path
from typing import Dict, List, Any

# GW2 API base URL
GW2_API_BASE = "https://api.guildwars2.com/v2"

# Output paths
OUTPUT_DIR = Path("data")
FULL_DATA_PATH = OUTPUT_DIR / "gw2_data.json"
WVW_SPECS_PATH = OUTPUT_DIR / "gw2_wvw_specs.json"

# Elite specializations we care about for WvW
ELITE_SPECS = {
    # Guardian
    "Firebrand", "Willbender", "Dragonhunter",
    # Warrior
    "Spellbreaker", "Berserker", "Bladesworn",
    # Revenant
    "Herald", "Vindicator", "Renegade",
    # Engineer
    "Scrapper", "Holosmith", "Mechanist",
    # Ranger
    "Druid", "Soulbeast", "Untamed",
    # Thief
    "Daredevil", "Deadeye", "Specter",
    # Elementalist
    "Tempest", "Weaver", "Catalyst",
    # Mesmer
    "Chronomancer", "Mirage", "Virtuoso",
    # Necromancer
    "Reaper", "Scourge", "Harbinger"
}

# WvW role tags based on spec mechanics
WVW_ROLE_TAGS = {
    # Guardian
    "Firebrand": ["support", "heal", "stability", "boon", "frontline"],
    "Willbender": ["roam", "dps", "mobility", "burst"],
    "Dragonhunter": ["dps", "traps", "burst", "backline"],
    # Warrior
    "Spellbreaker": ["frontline", "strip", "cc", "boon_corrupt"],
    "Berserker": ["dps", "burst", "frontline", "pressure"],
    "Bladesworn": ["burst", "dps", "roam", "oneshot"],
    # Revenant
    "Herald": ["frontline", "boon", "facetank", "stability"],
    "Vindicator": ["dps", "burst", "leap", "frontline"],
    "Renegade": ["support", "alacrity", "backline", "condi"],
    # Engineer
    "Scrapper": ["support", "superspeed", "cleanse", "gyro"],
    "Holosmith": ["dps", "burst", "roam", "pressure"],
    "Mechanist": ["support", "alacrity", "heal", "backline"],
    # Ranger
    "Druid": ["heal", "support", "spirits", "backline"],
    "Soulbeast": ["dps", "burst", "roam", "oneshot"],
    "Untamed": ["dps", "cc", "pet", "pressure"],
    # Thief
    "Daredevil": ["roam", "mobility", "burst", "ganker"],
    "Deadeye": ["sniper", "burst", "backline", "oneshot"],
    "Specter": ["support", "barrier", "stealth", "roam"],
    # Elementalist
    "Tempest": ["support", "aura", "heal", "backline"],
    "Weaver": ["dps", "condi", "pressure", "backline"],
    "Catalyst": ["dps", "combo", "burst", "frontline"],
    # Mesmer
    "Chronomancer": ["support", "boon", "portal", "utility"],
    "Mirage": ["condi", "dps", "roam", "pressure"],
    "Virtuoso": ["dps", "burst", "backline", "blade"],
    # Necromancer
    "Reaper": ["dps", "shroud", "frontline", "cleave"],
    "Scourge": ["condi", "corrupt", "barrier", "backline"],
    "Harbinger": ["condi", "dps", "elixir", "pressure"]
}

# WvW-specific descriptions
WVW_DESCRIPTIONS = {
    "Firebrand": "Support Guardian with Tomes. Provides mass stability (Stand Your Ground, Tome of Courage), Aegis spam, heals, and cleanses. Core of any zerg backline.",
    "Willbender": "Mobile burst Guardian. Excellent roamer with high mobility and burst damage. Less common in zergs.",
    "Dragonhunter": "Trap-based burst Guardian. Strong backline DPS with longbow and traps. Good for picks.",
    "Spellbreaker": "Boon strip specialist Warrior. Full Counter reflects, Winds of Disenchantment strips all boons in area. Essential frontline.",
    "Berserker": "Burst DPS Warrior. High damage in Berserk mode, good frontline pressure with greatsword.",
    "Bladesworn": "One-shot burst Warrior. Dragon Slash can delete players. High risk/reward roamer.",
    "Herald": "Facetank Revenant. Glint facet provides boons, very tanky frontline with high sustain.",
    "Vindicator": "Leap burst Revenant. Alliance stance provides big damage leaps. Strong frontline DPS.",
    "Renegade": "Support Revenant. Kalla stance provides alacrity and condi pressure. Backline support.",
    "Scrapper": "Utility Engineer. Gyros provide superspeed, stealth, and cleanses. Essential for mobility.",
    "Holosmith": "Burst DPS Engineer. Photon Forge mode for high damage. Good roamer.",
    "Mechanist": "Support Engineer. Mech provides alacrity and heals. Strong backline support.",
    "Druid": "Heal Ranger. Celestial Avatar for burst heals and spirits for buffs. Classic healer.",
    "Soulbeast": "Burst DPS Ranger. Merged pet for high burst damage. Excellent roamer and ganker.",
    "Untamed": "CC Ranger. Unleashed pet for heavy CC. Good frontline disruption.",
    "Daredevil": "Mobile Thief. Staff for mobility and evades. Classic roamer and +1 in fights.",
    "Deadeye": "Sniper Thief. Rifle for long-range burst. Can one-shot squishies from range.",
    "Specter": "Support Thief. Scepter for barrier and ally targeting. Unique support role.",
    "Tempest": "Aura support Elementalist. Overloads provide auras and heals. Backline support.",
    "Weaver": "Condi DPS Elementalist. Dual attunements for sustained pressure. Backline damage.",
    "Catalyst": "Combo Elementalist. Jade Sphere for combo fields. Can frontline with hammer.",
    "Chronomancer": "Utility Mesmer. Wells and portals for group utility. Boon extension.",
    "Mirage": "Condi Mesmer. Ambush skills for condi pressure. Good roamer.",
    "Virtuoso": "Burst DPS Mesmer. Blades for ranged burst damage. Strong backline DPS.",
    "Reaper": "Melee Necromancer. Shroud for cleave damage. Frontline bruiser.",
    "Scourge": "Condi Necromancer. Shades for boon corrupt and barrier. Essential backline.",
    "Harbinger": "Condi DPS Necromancer. Elixirs and Blight for sustained damage. Backline pressure."
}

# Key skills to know for countering
KEY_SKILLS = {
    "Firebrand": ["Tome of Courage (F3) - mass stability", "Stand Your Ground - stability shout", "Mantra of Liberation - stunbreak"],
    "Spellbreaker": ["Winds of Disenchantment - AoE boon strip bubble", "Full Counter - block and reflect", "Breaching Strike - boon strip"],
    "Scourge": ["Serpent Siphon - boon corrupt", "Trail of Anguish - fear", "Shade skills - AoE pressure"],
    "Scrapper": ["Sneak Gyro - group stealth", "Blast Gyro - CC", "Med Kit - heals and superspeed"],
    "Herald": ["Facet of Nature - boon share", "Impossible Odds - quickness", "Infuse Light - big heal"],
    "Reaper": ["Reaper's Shroud - high cleave", "Executioner's Scythe - CC", "Chilled to the Bone - elite CC"],
    "Tempest": ["Overload Water - big heal", "Rebound - revive utility", "Aftershock - protection"],
    "Virtuoso": ["Bladesong Sorrow - burst", "Thousand Cuts - sustained damage", "Signet of the Ether - reset"],
    "Soulbeast": ["One Wolf Pack - burst buff", "Worldly Impact - CC", "Sic 'Em - damage boost"],
    "Deadeye": ["Death's Judgment - snipe", "Shadow Meld - stealth reset", "Malicious Backstab - burst"]
}

# Counters and weaknesses
COUNTERS = {
    "Firebrand": {"countered_by": ["Spellbreaker", "Scourge"], "weak_to": ["boon strip", "boon corrupt", "CC chains"]},
    "Willbender": {"countered_by": ["Spellbreaker", "Reaper"], "weak_to": ["CC", "condi pressure"]},
    "Dragonhunter": {"countered_by": ["Mirage", "Scourge"], "weak_to": ["condi", "mobility"]},
    "Spellbreaker": {"countered_by": ["Scourge", "Harbinger"], "weak_to": ["condi pressure", "kiting"]},
    "Berserker": {"countered_by": ["Scourge", "Mirage"], "weak_to": ["condi", "kiting"]},
    "Bladesworn": {"countered_by": ["Daredevil", "Mirage"], "weak_to": ["interrupts", "mobility"]},
    "Herald": {"countered_by": ["Spellbreaker", "Scourge"], "weak_to": ["boon strip", "condi pressure"]},
    "Vindicator": {"countered_by": ["Spellbreaker", "Scourge"], "weak_to": ["boon strip", "CC"]},
    "Renegade": {"countered_by": ["Spellbreaker", "Soulbeast"], "weak_to": ["burst", "focus fire"]},
    "Scrapper": {"countered_by": ["Spellbreaker", "Scourge"], "weak_to": ["boon strip", "focus fire"]},
    "Holosmith": {"countered_by": ["Scourge", "Mirage"], "weak_to": ["condi", "kiting"]},
    "Mechanist": {"countered_by": ["Soulbeast", "Deadeye"], "weak_to": ["burst", "mech focus"]},
    "Druid": {"countered_by": ["Soulbeast", "Deadeye"], "weak_to": ["burst", "focus fire"]},
    "Soulbeast": {"countered_by": ["Spellbreaker", "Reaper"], "weak_to": ["CC", "sustain fights"]},
    "Untamed": {"countered_by": ["Scourge", "Mirage"], "weak_to": ["condi", "kiting"]},
    "Daredevil": {"countered_by": ["Reaper", "Spellbreaker"], "weak_to": ["AoE", "reveals"]},
    "Deadeye": {"countered_by": ["Daredevil", "Mirage"], "weak_to": ["mobility", "stealth reveal"]},
    "Specter": {"countered_by": ["Spellbreaker", "Scourge"], "weak_to": ["boon strip", "reveals"]},
    "Tempest": {"countered_by": ["Spellbreaker", "Soulbeast"], "weak_to": ["burst", "interrupts"]},
    "Weaver": {"countered_by": ["Spellbreaker", "Soulbeast"], "weak_to": ["burst", "CC"]},
    "Catalyst": {"countered_by": ["Spellbreaker", "Scourge"], "weak_to": ["boon strip", "focus fire"]},
    "Chronomancer": {"countered_by": ["Spellbreaker", "Scourge"], "weak_to": ["boon strip", "focus fire"]},
    "Mirage": {"countered_by": ["Reaper", "Spellbreaker"], "weak_to": ["cleave", "reveals"]},
    "Virtuoso": {"countered_by": ["Spellbreaker", "Daredevil"], "weak_to": ["gap closers", "pressure"]},
    "Reaper": {"countered_by": ["Soulbeast", "Deadeye"], "weak_to": ["kiting", "burst"]},
    "Scourge": {"countered_by": ["Soulbeast", "Deadeye"], "weak_to": ["burst", "focus fire"]},
    "Harbinger": {"countered_by": ["Spellbreaker", "Soulbeast"], "weak_to": ["burst", "boon strip"]}
}


def fetch_endpoint(endpoint: str, params: Dict = None) -> Any:
    """Fetch data from GW2 API endpoint"""
    url = f"{GW2_API_BASE}/{endpoint}"
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, params=params)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"  ⚠ {endpoint}: HTTP {response.status_code}")
                return None
    except Exception as e:
        print(f"  ✗ {endpoint}: {e}")
        return None


def fetch_all_ids(endpoint: str) -> List[int]:
    """Fetch all IDs from an endpoint"""
    data = fetch_endpoint(endpoint)
    return data if data else []


def fetch_by_ids(endpoint: str, ids: List[int], batch_size: int = 200) -> List[Dict]:
    """Fetch items by IDs in batches"""
    results = []
    for i in range(0, len(ids), batch_size):
        batch = ids[i:i + batch_size]
        ids_str = ",".join(map(str, batch))
        data = fetch_endpoint(endpoint, {"ids": ids_str})
        if data:
            results.extend(data)
        time.sleep(0.1)  # Rate limiting
    return results


def fetch_specializations() -> Dict[str, Dict]:
    """Fetch all specializations and filter to elite specs"""
    print("Fetching specializations...")
    
    # Get all spec IDs
    all_ids = fetch_all_ids("specializations")
    if not all_ids:
        return {}
    
    # Fetch all specs
    all_specs = fetch_by_ids("specializations", all_ids)
    
    # Filter to elite specs we care about
    elite_specs = {}
    for spec in all_specs:
        name = spec.get("name", "")
        if name in ELITE_SPECS and spec.get("elite", False):
            elite_specs[name] = {
                "id": spec.get("id"),
                "name": name,
                "profession": spec.get("profession"),
                "elite": True,
                "minor_traits": spec.get("minor_traits", []),
                "major_traits": spec.get("major_traits", []),
                "icon": spec.get("icon", "")
            }
    
    print(f"  ✓ Found {len(elite_specs)} elite specializations")
    return elite_specs


def fetch_professions() -> Dict[str, Dict]:
    """Fetch profession data"""
    print("Fetching professions...")
    
    professions = {}
    prof_names = ["Guardian", "Warrior", "Revenant", "Engineer", "Ranger", 
                  "Thief", "Elementalist", "Mesmer", "Necromancer"]
    
    for prof in prof_names:
        data = fetch_endpoint(f"professions/{prof}")
        if data:
            professions[prof] = {
                "name": prof,
                "specializations": data.get("specializations", []),
                "weapons": list(data.get("weapons", {}).keys()),
                "icon": data.get("icon", "")
            }
        time.sleep(0.1)
    
    print(f"  ✓ Found {len(professions)} professions")
    return professions


def fetch_traits(trait_ids: List[int]) -> Dict[int, Dict]:
    """Fetch trait data for given IDs"""
    print(f"Fetching {len(trait_ids)} traits...")
    
    all_traits = fetch_by_ids("traits", trait_ids)
    
    traits = {}
    for trait in all_traits:
        traits[trait.get("id")] = {
            "id": trait.get("id"),
            "name": trait.get("name"),
            "description": trait.get("description", ""),
            "slot": trait.get("slot"),
            "tier": trait.get("tier")
        }
    
    print(f"  ✓ Fetched {len(traits)} traits")
    return traits


def build_wvw_spec_data(specs: Dict, professions: Dict) -> Dict[str, Dict]:
    """Build WvW-focused specialization data"""
    print("Building WvW spec data...")
    
    wvw_specs = {}
    
    for spec_name in ELITE_SPECS:
        spec_data = specs.get(spec_name, {})
        profession = spec_data.get("profession", "Unknown")
        
        wvw_specs[spec_name] = {
            "name": spec_name,
            "profession": profession,
            "role_tags": WVW_ROLE_TAGS.get(spec_name, []),
            "wvw_description": WVW_DESCRIPTIONS.get(spec_name, ""),
            "key_skills": KEY_SKILLS.get(spec_name, []),
            "counters": COUNTERS.get(spec_name, {}),
            "api_id": spec_data.get("id"),
            "icon": spec_data.get("icon", "")
        }
    
    print(f"  ✓ Built data for {len(wvw_specs)} specs")
    return wvw_specs


def main():
    print("=" * 60)
    print("GW2 API Data Fetcher for WvW Counter-Picker")
    print("=" * 60)
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Fetch data from API
    specs = fetch_specializations()
    professions = fetch_professions()
    
    # Collect all trait IDs from specs
    all_trait_ids = []
    for spec in specs.values():
        all_trait_ids.extend(spec.get("minor_traits", []))
        all_trait_ids.extend(spec.get("major_traits", []))
    
    traits = fetch_traits(list(set(all_trait_ids)))
    
    # Build full data file
    full_data = {
        "version": "1.0",
        "fetched_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "specializations": specs,
        "professions": professions,
        "traits": {str(k): v for k, v in traits.items()}  # JSON keys must be strings
    }
    
    with open(FULL_DATA_PATH, 'w', encoding='utf-8') as f:
        json.dump(full_data, f, indent=2, ensure_ascii=False)
    print(f"\n✓ Full data saved to {FULL_DATA_PATH}")
    
    # Build WvW-focused spec data
    wvw_specs = build_wvw_spec_data(specs, professions)
    
    with open(WVW_SPECS_PATH, 'w', encoding='utf-8') as f:
        json.dump(wvw_specs, f, indent=2, ensure_ascii=False)
    print(f"✓ WvW spec data saved to {WVW_SPECS_PATH}")
    
    # Show sample
    print("\n" + "=" * 60)
    print("Sample WvW Spec Data:")
    print("=" * 60)
    sample_spec = wvw_specs.get("Firebrand", {})
    print(json.dumps(sample_spec, indent=2))
    
    print("\n✓ Done! Data ready for fine-tuning enrichment.")


if __name__ == "__main__":
    main()
