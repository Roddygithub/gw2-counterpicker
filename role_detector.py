"""
GW2 CounterPicker - Role Detection Module
Centralized role detection logic for WvW builds
"""

import re
from typing import Dict, Optional

# =============================================================================
# ROLE DETECTION CONSTANTS
# =============================================================================

# Primary stab providers (Guardian)
STAB_SPECS = {'Firebrand', 'Luminary'}

# Primary healers (various classes)
HEALER_SPECS = {'Druid', 'Troubadour', 'Specter', 'Vindicator', 'Tempest', 'Scrapper'}

# Primary boon providers
BOON_SPECS = {'Herald', 'Renegade', 'Chronomancer', 'Paragon'}

# DPS specs that commonly strip boons
STRIP_DPS_SPECS = {'Spellbreaker', 'Chronomancer', 'Reaper', 'Harbinger', 'Scourge', 'Ritualist'}

# Spec to base class mapping
SPEC_TO_CLASS = {
    'Firebrand': 'Guardian', 'Dragonhunter': 'Guardian', 'Willbender': 'Guardian',
    'Scrapper': 'Engineer', 'Holosmith': 'Engineer', 'Mechanist': 'Engineer',
    'Scourge': 'Necromancer', 'Reaper': 'Necromancer', 'Harbinger': 'Necromancer',
    'Herald': 'Revenant', 'Renegade': 'Revenant', 'Vindicator': 'Revenant',
    'Spellbreaker': 'Warrior', 'Berserker': 'Warrior', 'Bladesworn': 'Warrior',
    'Tempest': 'Elementalist', 'Weaver': 'Elementalist', 'Catalyst': 'Elementalist',
    'Chronomancer': 'Mesmer', 'Mirage': 'Mesmer', 'Virtuoso': 'Mesmer',
    'Druid': 'Ranger', 'Soulbeast': 'Ranger', 'Untamed': 'Ranger',
    'Daredevil': 'Thief', 'Deadeye': 'Thief', 'Specter': 'Thief'
}


def estimate_role_from_profession(profession: str) -> str:
    """
    Estimate enemy role based on profession name (no stats available).
    Used for enemies where we only have spec name.
    """
    if profession in STAB_SPECS:
        return 'stab'
    if profession in HEALER_SPECS:
        return 'healer'
    if profession in BOON_SPECS:
        return 'boon'
    if profession in STRIP_DPS_SPECS:
        return 'dps_strip'
    return 'dps'


def detect_role_advanced(profession: str, stats: Dict) -> str:
    """
    Advanced role detection using multiple stats:
    - healing: total healing done
    - stab_gen: stability generation %
    - cleanses_per_sec: condition cleanses per second
    - strips: boon strips count
    - down_contrib: down contribution (damage to downed)
    - barrier: barrier generated
    - duration: fight duration in seconds
    """
    healing = stats.get('healing', 0)
    stab_gen = stats.get('stab_gen', 0)
    cleanses_per_sec = stats.get('cleanses_per_sec', 0)
    strips = stats.get('strips', 0)
    duration = stats.get('duration', 60)
    
    # Normalize stats per minute for comparison
    strips_per_min = (strips / duration) * 60 if duration > 0 else 0
    healing_per_sec = healing / duration if duration > 0 else 0
    
    # === STAB DETECTION (priority) ===
    if profession in STAB_SPECS:
        return 'stab'
    if stab_gen >= 5.0:
        return 'stab'
    
    # === BOON DETECTION (before healer to avoid Paragon misdetection) ===
    if profession in BOON_SPECS:
        return 'boon'
    
    # === HEALER DETECTION ===
    if healing_per_sec >= 800:
        return 'healer'
    if profession in HEALER_SPECS and healing_per_sec >= 300:
        return 'healer'
    if profession in {'Scrapper', 'Tempest'} and healing_per_sec >= 500:
        return 'healer'
    
    # === DPS DETECTION (with sub-roles) ===
    if strips_per_min >= 10 and profession in STRIP_DPS_SPECS:
        return 'dps_strip'
    if strips_per_min >= 20:
        return 'dps_strip'
    
    # === FALLBACK DETECTION ===
    if cleanses_per_sec >= 0.5 and profession in HEALER_SPECS:
        return 'healer'
    if profession in {'Scrapper', 'Tempest'} and cleanses_per_sec >= 0.3:
        return 'healer'
    
    return 'dps'


def parse_duration_string(duration_str: str) -> float:
    """Parse duration string like '2m 30s 500ms' to seconds."""
    if isinstance(duration_str, (int, float)):
        return float(duration_str) / 1000 if duration_str > 1000 else float(duration_str)
    
    duration_sec = 0.0
    m = re.search(r'(\d+)m', duration_str)
    if m:
        duration_sec += int(m.group(1)) * 60
    s = re.search(r'(\d+)s', duration_str)
    if s:
        duration_sec += int(s.group(1))
    ms = re.search(r'(\d+)ms', duration_str)
    if ms:
        duration_sec += int(ms.group(1)) / 1000
    
    return max(duration_sec, 1.0)  # Avoid division by zero


def get_base_class(spec: str) -> str:
    """Get base class from elite spec name."""
    return SPEC_TO_CLASS.get(spec, spec)
