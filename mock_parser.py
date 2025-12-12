"""
GW2 CounterPicker - Mock EVTC Parser
Ultra-realistic simulated parsing until we integrate python-evtc
"""

import random
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any

from models import (
    AnalysisResult, PlayerBuild, CompositionAnalysis,
    EveningReport, HourlyEvolution, TopPlayer, HeatmapData
)


class MockEVTCParser:
    """
    Mock parser that generates realistic WvW data
    Will be replaced with real python-evtc parsing
    """
    
    # Realistic WvW meta specs and their frequencies (2025 meta)
    META_SPECS = {
        "Firebrand": {"weight": 25, "role": "Support", "prof": "Guardian"},
        "Scrapper": {"weight": 18, "role": "Support", "prof": "Engineer"},
        "Scourge": {"weight": 15, "role": "Backline", "prof": "Necromancer"},
        "Herald": {"weight": 12, "role": "Frontline", "prof": "Revenant"},
        "Spellbreaker": {"weight": 10, "role": "Frontline", "prof": "Warrior"},
        "Tempest": {"weight": 8, "role": "Backline", "prof": "Elementalist"},
        "Willbender": {"weight": 6, "role": "Roamer", "prof": "Guardian"},
        "Vindicator": {"weight": 5, "role": "Frontline", "prof": "Revenant"},
        "Harbinger": {"weight": 5, "role": "Backline", "prof": "Necromancer"},
        "Chronomancer": {"weight": 4, "role": "Support", "prof": "Mesmer"},
        "Berserker": {"weight": 4, "role": "Frontline", "prof": "Warrior"},
        "Reaper": {"weight": 3, "role": "Frontline", "prof": "Necromancer"},
        "Dragonhunter": {"weight": 3, "role": "Backline", "prof": "Guardian"},
        "Catalyst": {"weight": 3, "role": "Backline", "prof": "Elementalist"},
        "Weaver": {"weight": 2, "role": "Backline", "prof": "Elementalist"},
        "Mechanist": {"weight": 2, "role": "Support", "prof": "Engineer"},
        "Virtuoso": {"weight": 2, "role": "Backline", "prof": "Mesmer"},
        "Renegade": {"weight": 2, "role": "Support", "prof": "Revenant"},
        "Specter": {"weight": 1, "role": "Support", "prof": "Thief"},
        "Soulbeast": {"weight": 1, "role": "Roamer", "prof": "Ranger"},
        "Deadeye": {"weight": 1, "role": "Roamer", "prof": "Thief"},
        "Daredevil": {"weight": 1, "role": "Roamer", "prof": "Thief"},
        "Untamed": {"weight": 1, "role": "Roamer", "prof": "Ranger"},
        "Druid": {"weight": 1, "role": "Support", "prof": "Ranger"},
        "Holosmith": {"weight": 1, "role": "Roamer", "prof": "Engineer"},
        "Bladesworn": {"weight": 1, "role": "Roamer", "prof": "Warrior"},
        "Mirage": {"weight": 1, "role": "Roamer", "prof": "Mesmer"},
    }
    
    # EU Server names for realism
    EU_SERVERS = [
        "Jade Sea [FR]", "Fort Ranik [FR]", "Augury Rock [FR]",
        "Vizunah Square [FR]", "Arborstone [FR]",
        "Kodash [DE]", "Riverside [DE]", "Elona Reach [DE]",
        "Abaddon's Mouth [DE]", "Drakkar Lake [DE]",
        "Baruch Bay [SP]", "Ruins of Surmia [SP]",
        "Dzagonur [DE]", "Miller's Sound [DE]",
        "Seafarer's Rest [EN]", "Desolation [EN]", "Gandara [EN]",
        "Far Shiverpeaks [EN]", "Ring of Fire [EN]",
        "Underworld [EN]", "Piken Square [EN]", "Aurora Glade [EN]",
        "Whiteside Ridge [EN]", "Vabbi [EN]"
    ]
    
    # WvW Map names
    WVW_MAPS = [
        "Eternal Battlegrounds",
        "Alpine Borderlands (Blue)",
        "Alpine Borderlands (Green)", 
        "Desert Borderlands (Red)",
        "Edge of the Mists"
    ]
    
    # Realistic player name patterns
    PLAYER_PREFIXES = [
        "Dark", "Shadow", "Iron", "Storm", "Fire", "Ice", "Death", "Blood",
        "Ancient", "Eternal", "Silent", "Swift", "Brave", "Noble", "Wild",
        "Chaos", "Void", "Light", "Thunder", "Frost", "Ember", "Steel"
    ]
    
    PLAYER_SUFFIXES = [
        "walker", "blade", "hunter", "guard", "knight", "mage", "lord",
        "bringer", "seeker", "slayer", "master", "born", "heart", "soul",
        "fist", "eye", "wind", "flame", "storm", "fury", "rage"
    ]
    
    # Zone names for heatmap
    ZONES = [
        "Stonemist Castle", "North Camp", "South Camp", "East Camp", "West Camp",
        "North Tower", "South Tower", "NE Tower", "NW Tower", "SE Tower", "SW Tower",
        "Bay Keep", "Hills Keep", "Garrison", "North Sentry", "South Sentry",
        "Overlook", "Valley", "Lowlands", "Fire Keep", "Air Keep", "Earth Keep",
        "Water Gate", "Inner Gate", "Outer Gate"
    ]
    
    def _weighted_random_spec(self) -> str:
        """Pick a spec based on meta weights"""
        specs = list(self.META_SPECS.keys())
        weights = [self.META_SPECS[s]["weight"] for s in specs]
        return random.choices(specs, weights=weights, k=1)[0]
    
    def _generate_player_name(self) -> str:
        """Generate a realistic player name"""
        if random.random() < 0.3:
            # Some players use simple names
            return f"{random.choice(self.PLAYER_PREFIXES)}{random.randint(1, 999)}"
        return f"{random.choice(self.PLAYER_PREFIXES)}{random.choice(self.PLAYER_SUFFIXES)}"
    
    def _generate_account_name(self, player_name: str) -> str:
        """Generate account name"""
        return f"{player_name}.{random.randint(1000, 9999)}"
    
    def _generate_player_build(self, is_commander: bool = False) -> PlayerBuild:
        """Generate a realistic player build"""
        spec = self._weighted_random_spec()
        spec_info = self.META_SPECS[spec]
        player_name = self._generate_player_name()
        
        # Generate weapons based on spec
        weapons_by_spec = {
            "Firebrand": ["Axe/Shield", "Staff"],
            "Scrapper": ["Hammer", "Shield/Mace"],
            "Scourge": ["Scepter/Torch", "Staff"],
            "Herald": ["Hammer", "Staff"],
            "Spellbreaker": ["Hammer", "Dagger/Shield"],
            "Tempest": ["Staff", "Dagger/Warhorn"],
            "Willbender": ["Greatsword", "Sword/Focus"],
            "Vindicator": ["Greatsword", "Staff"],
            "Harbinger": ["Pistol/Dagger", "Staff"],
            "Chronomancer": ["Shield/Sword", "Staff"],
            "Berserker": ["Hammer", "Longbow"],
            "Reaper": ["Greatsword", "Axe/Warhorn"],
            "Catalyst": ["Hammer", "Staff"],
        }
        
        weapons = weapons_by_spec.get(spec, ["Unknown"])
        
        return PlayerBuild(
            player_name=player_name,
            account_name=self._generate_account_name(player_name),
            profession=spec_info["prof"],
            elite_spec=spec,
            role=spec_info["role"],
            weapons=weapons,
            is_commander=is_commander,
            damage_dealt=random.randint(50000, 500000) if spec_info["role"] != "Support" else random.randint(10000, 100000),
            healing_done=random.randint(100000, 800000) if spec_info["role"] == "Support" else random.randint(0, 50000),
            deaths=random.randint(0, 5),
            kills=random.randint(0, 15)
        )
    
    def _generate_composition(self, player_count: int) -> CompositionAnalysis:
        """Generate a realistic squad composition"""
        builds = []
        
        # First player is commander
        builds.append(self._generate_player_build(is_commander=True))
        
        # Generate rest of squad
        for _ in range(player_count - 1):
            builds.append(self._generate_player_build())
        
        # Calculate spec counts
        spec_counts = {}
        role_distribution = {}
        
        for build in builds:
            spec_counts[build.elite_spec] = spec_counts.get(build.elite_spec, 0) + 1
            role_distribution[build.role] = role_distribution.get(build.role, 0) + 1
        
        # Calculate ratios
        total = len(builds)
        frontline_count = role_distribution.get("Frontline", 0)
        support_count = role_distribution.get("Support", 0)
        
        frontline_ratio = frontline_count / total if total > 0 else 0
        support_ratio = support_count / total if total > 0 else 0
        
        # Determine squad type
        if support_ratio > 0.4:
            squad_type = "Support Heavy / Sustain Blob"
        elif frontline_ratio > 0.4:
            squad_type = "Melee Train / Push Comp"
        elif role_distribution.get("Backline", 0) / total > 0.4:
            squad_type = "Ranged Poke / Siege Comp"
        else:
            squad_type = "Balanced Composition"
        
        return CompositionAnalysis(
            total_players=total,
            builds=builds,
            spec_counts=spec_counts,
            role_distribution=role_distribution,
            frontline_ratio=frontline_ratio,
            support_ratio=support_ratio,
            estimated_squad_type=squad_type
        )
    
    def parse_dps_report_url(self, url: str) -> AnalysisResult:
        """Parse a dps.report URL (mocked)"""
        # Generate realistic data
        enemy_count = random.randint(20, 55)
        our_count = random.randint(20, 50)
        
        enemy_comp = self._generate_composition(enemy_count)
        our_comp = self._generate_composition(our_count)
        
        our_kills = random.randint(5, 35)
        our_deaths = random.randint(3, 30)
        
        if our_kills > our_deaths * 1.5:
            outcome = "Victory"
        elif our_deaths > our_kills * 1.5:
            outcome = "Defeat"
        else:
            outcome = "Draw"
        
        return AnalysisResult(
            report_url=url,
            fight_duration=random.randint(30, 300),
            map_name=random.choice(self.WVW_MAPS),
            timestamp=datetime.now() - timedelta(hours=random.randint(0, 24)),
            our_composition=our_comp,
            enemy_composition=enemy_comp,
            our_kills=our_kills,
            our_deaths=our_deaths,
            outcome=outcome
        )
    
    def parse_evening_files(self, file_infos: List[Dict[str, Any]]) -> EveningReport:
        """Parse multiple .evtc files for evening analysis"""
        session_id = str(uuid.uuid4())
        file_count = len(file_infos)
        
        # Simulate fight count based on files
        total_fights = file_count
        total_duration = file_count * random.randint(3, 8)  # minutes per fight
        
        # Pick enemy server
        enemy_server = random.choice(self.EU_SERVERS)
        
        # Generate average composition (weighted towards evening's "style")
        avg_comp = self._generate_composition(random.randint(35, 50))
        
        # Generate hourly evolution
        hourly_evolution = []
        base_hour = 20  # Start at 20:00
        
        for i in range(4):  # 4 hours of play
            hour = f"{base_hour + i}:00"
            
            # Vary the composition slightly each hour
            hour_spec_counts = {}
            for spec, count in avg_comp.spec_counts.items():
                variance = random.randint(-3, 3)
                new_count = max(0, count + variance)
                if new_count > 0:
                    hour_spec_counts[spec] = new_count
            
            # Generate notable changes
            changes = []
            if i > 0:
                # Simulate meta shifts during the evening
                shifts = [
                    f"FB count increased to {random.randint(8, 15)}",
                    f"More Scourges spotted ({random.randint(5, 12)})",
                    f"Enemy switched to melee train",
                    f"Added {random.randint(2, 5)} Spellbreakers",
                    f"Backline reduced, more frontline pressure",
                ]
                changes = [random.choice(shifts)]
            
            hourly_evolution.append(HourlyEvolution(
                hour=hour,
                spec_counts=hour_spec_counts,
                notable_changes=changes
            ))
        
        # Generate top players
        top_players = []
        for rank in range(1, 11):
            spec = self._weighted_random_spec()
            times_seen = random.randint(15, total_fights)
            avg_damage = random.randint(80000, 350000)
            
            if avg_damage > 250000:
                threat = "Extreme"
            elif avg_damage > 180000:
                threat = "High"
            elif avg_damage > 100000:
                threat = "Medium"
            else:
                threat = "Low"
            
            player_name = self._generate_player_name()
            top_players.append(TopPlayer(
                rank=rank,
                player_name=player_name,
                account_name=self._generate_account_name(player_name),
                elite_spec=spec,
                times_seen=times_seen,
                avg_damage=avg_damage,
                avg_kills=round(random.uniform(2.5, 12.0), 1),
                threat_level=threat
            ))
        
        # Most played per class
        professions = ["Guardian", "Warrior", "Revenant", "Engineer", "Ranger",
                      "Thief", "Elementalist", "Mesmer", "Necromancer"]
        most_played = {}
        for prof in professions:
            specs_for_prof = [s for s, info in self.META_SPECS.items() if info["prof"] == prof]
            if specs_for_prof:
                most_played[prof] = random.choice(specs_for_prof)
        
        # Generate heatmap data
        heatmap_zones = []
        selected_zones = random.sample(self.ZONES, min(12, len(self.ZONES)))
        for zone in selected_zones:
            fight_count = random.randint(1, 15)
            heatmap_zones.append(HeatmapData(
                zone_name=zone,
                fight_count=fight_count,
                total_kills=fight_count * random.randint(5, 25),
                intensity=min(1.0, fight_count / 15)
            ))
        
        # Sort by intensity
        heatmap_zones.sort(key=lambda x: x.intensity, reverse=True)
        
        # Generate key insights
        insights = [
            f"🎯 Enemy server: {enemy_server}",
            f"📊 {total_fights} fights analyzed over {total_duration} minutes",
            f"🔥 Dominant spec: {avg_comp.dominant_specs[0][0]} ({avg_comp.dominant_specs[0][1]} players avg)",
            f"⚔️ Enemy plays {avg_comp.estimated_squad_type}",
            f"🏰 Most contested zone: {heatmap_zones[0].zone_name}",
            f"👤 Top threat: {top_players[0].player_name} ({top_players[0].elite_spec})",
        ]
        
        return EveningReport(
            session_id=session_id,
            created_at=datetime.now(),
            total_files_analyzed=file_count,
            total_fights=total_fights,
            total_duration_minutes=total_duration,
            enemy_server=enemy_server,
            enemy_alliance=f"Alliance {random.randint(1, 5)}",
            average_composition=avg_comp,
            hourly_evolution=hourly_evolution,
            top_players=top_players,
            most_played_per_class=most_played,
            heatmap_zones=heatmap_zones,
            key_insights=insights
        )
