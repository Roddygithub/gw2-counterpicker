"""
GW2 CounterPicker - Data Models
All the structures needed to represent WvW intelligence data
"""

from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime
from enum import Enum


class Profession(str, Enum):
    """GW2 Professions"""
    GUARDIAN = "Guardian"
    WARRIOR = "Warrior"
    REVENANT = "Revenant"
    ENGINEER = "Engineer"
    RANGER = "Ranger"
    THIEF = "Thief"
    ELEMENTALIST = "Elementalist"
    MESMER = "Mesmer"
    NECROMANCER = "Necromancer"


class EliteSpec(str, Enum):
    """WvW Meta Elite Specs 2025"""
    # Guardian
    FIREBRAND = "Firebrand"
    WILLBENDER = "Willbender"
    DRAGONHUNTER = "Dragonhunter"
    
    # Warrior
    SPELLBREAKER = "Spellbreaker"
    BERSERKER = "Berserker"
    BLADESWORN = "Bladesworn"
    
    # Revenant
    HERALD = "Herald"
    RENEGADE = "Renegade"
    VINDICATOR = "Vindicator"
    
    # Engineer
    SCRAPPER = "Scrapper"
    HOLOSMITH = "Holosmith"
    MECHANIST = "Mechanist"
    
    # Ranger
    DRUID = "Druid"
    SOULBEAST = "Soulbeast"
    UNTAMED = "Untamed"
    
    # Thief
    DAREDEVIL = "Daredevil"
    DEADEYE = "Deadeye"
    SPECTER = "Specter"
    
    # Elementalist
    TEMPEST = "Tempest"
    WEAVER = "Weaver"
    CATALYST = "Catalyst"
    
    # Mesmer
    CHRONOMANCER = "Chronomancer"
    MIRAGE = "Mirage"
    VIRTUOSO = "Virtuoso"
    
    # Necromancer
    REAPER = "Reaper"
    SCOURGE = "Scourge"
    HARBINGER = "Harbinger"


class BuildRole(str, Enum):
    """WvW Build Roles"""
    FRONTLINE = "Frontline"
    BACKLINE = "Backline"
    SUPPORT = "Support"
    ROAMER = "Roamer"
    SIEGER = "Sieger"


class PlayerBuild(BaseModel):
    """Represents a player's build"""
    player_name: str
    account_name: Optional[str] = None
    profession: str
    elite_spec: str
    role: str
    weapons: List[str] = []
    is_commander: bool = False
    damage_dealt: int = 0
    healing_done: int = 0
    deaths: int = 0
    kills: int = 0
    
    @property
    def icon_name(self) -> str:
        """Get the icon filename for this spec"""
        return self.elite_spec.lower().replace(" ", "_")


class CompositionAnalysis(BaseModel):
    """Analysis of a squad/zerg composition"""
    total_players: int
    builds: List[PlayerBuild]
    spec_counts: Dict[str, int] = {}
    role_distribution: Dict[str, int] = {}
    
    # Computed stats
    frontline_ratio: float = 0.0
    support_ratio: float = 0.0
    estimated_squad_type: str = "Unknown"
    
    @property
    def dominant_specs(self) -> List[tuple]:
        """Get top 5 most played specs"""
        sorted_specs = sorted(self.spec_counts.items(), key=lambda x: x[1], reverse=True)
        return sorted_specs[:5]


class CounterBuild(BaseModel):
    """A recommended counter build"""
    elite_spec: str
    role: str
    priority: int  # 1-5, 5 being highest priority
    reason: str
    build_url: Optional[str] = None
    
    @property
    def icon_name(self) -> str:
        return self.elite_spec.lower().replace(" ", "_")


class CounterRecommendation(BaseModel):
    """Full counter recommendation for a composition"""
    recommended_builds: List[CounterBuild]
    strategy_notes: List[str]
    key_targets: List[str]  # Priority targets to focus
    avoid_list: List[str]  # What to avoid doing
    confidence_score: float  # 0-100
    
    @property
    def top_priority_builds(self) -> List[CounterBuild]:
        return [b for b in self.recommended_builds if b.priority >= 3]


class AnalysisResult(BaseModel):
    """Result from single report analysis"""
    report_url: str
    fight_duration: int  # seconds
    map_name: str
    timestamp: datetime
    
    # Our squad
    our_composition: Optional[CompositionAnalysis] = None
    
    # Enemy squad
    enemy_composition: CompositionAnalysis
    
    # Fight outcome
    our_kills: int
    our_deaths: int
    outcome: str  # "Victory", "Defeat", "Draw", "Stalemate"
