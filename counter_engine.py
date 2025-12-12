"""
GW2 CounterPicker - Counter Pick Intelligence Engine
The brain that analyzes enemy compositions and generates perfect counters
"""

from typing import List, Dict
from models import CompositionAnalysis, CounterRecommendation, CounterBuild


class CounterPickEngine:
    """
    Advanced counter-pick recommendation engine
    Uses WvW meta knowledge to generate optimal responses
    """
    
    # Counter relationships: what counters what
    COUNTERS = {
        "Firebrand": {
            "countered_by": ["Scourge", "Spellbreaker", "Chronomancer"],
            "reason": "Boon corrupt and strip destroys FB sustain"
        },
        "Scrapper": {
            "countered_by": ["Spellbreaker", "Scourge", "Revenant"],
            "reason": "Boon strip removes superspeed and stability"
        },
        "Scourge": {
            "countered_by": ["Spellbreaker", "Willbender", "Reaper"],
            "reason": "High mobility and burst damage before barriers go up"
        },
        "Herald": {
            "countered_by": ["Scourge", "Chronomancer", "Spellbreaker"],
            "reason": "Boon corrupt turns their boons against them"
        },
        "Spellbreaker": {
            "countered_by": ["Scourge", "Tempest", "Catalyst"],
            "reason": "Ranged pressure and conditions bypass Full Counter"
        },
        "Tempest": {
            "countered_by": ["Spellbreaker", "Willbender", "Vindicator"],
            "reason": "Gap closers and interrupts disrupt overloads"
        },
        "Willbender": {
            "countered_by": ["Scourge", "Reaper", "Spellbreaker"],
            "reason": "Chill and CC chain catches mobility skills"
        },
        "Vindicator": {
            "countered_by": ["Scourge", "Chronomancer", "Tempest"],
            "reason": "Boon strip and CC interrupt Legendary Alliance"
        },
        "Harbinger": {
            "countered_by": ["Spellbreaker", "Scrapper", "Firebrand"],
            "reason": "Cleanses and resistance counter conditions"
        },
        "Chronomancer": {
            "countered_by": ["Spellbreaker", "Scourge", "Willbender"],
            "reason": "Boon strip removes distortion uptime"
        },
        "Berserker": {
            "countered_by": ["Scourge", "Chronomancer", "Firebrand"],
            "reason": "Conditions and CC chain interrupt berserk mode"
        },
        "Reaper": {
            "countered_by": ["Firebrand", "Scrapper", "Tempest"],
            "reason": "Stability and cleanses counter chill spam"
        },
        "Catalyst": {
            "countered_by": ["Spellbreaker", "Willbender", "Vindicator"],
            "reason": "Burst damage and mobility counter jade sphere setup"
        },
    }
    
    # Role counters
    ROLE_COUNTERS = {
        "Support": ["Scourge", "Spellbreaker", "Chronomancer"],
        "Frontline": ["Scourge", "Tempest", "Catalyst"],
        "Backline": ["Willbender", "Vindicator", "Spellbreaker"],
        "Roamer": ["Scrapper", "Herald", "Firebrand"],
    }
    
    # Strategy templates based on enemy composition type
    STRATEGIES = {
        "Support Heavy / Sustain Blob": {
            "notes": [
                "🎯 Focus boon corrupt builds - their sustain relies on boons",
                "⚡ Stack Scourges to corrupt stability and resistance",
                "🗡️ Add Spellbreakers to strip aegis before big damage",
                "📍 Force extended fights - they'll run out of cooldowns",
                "❌ Avoid: Short poke fights where they can reset",
            ],
            "key_targets": ["Firebrands", "Scrappers", "Any commander tag"],
            "avoid": ["Chasing into keeps", "Splitting forces", "1v1 against support"],
        },
        "Melee Train / Push Comp": {
            "notes": [
                "🎯 Kite and use ranged pressure - don't engage in melee",
                "⚡ Stack immobilize and chill to slow their push",
                "🗡️ Focus their supports first to remove sustain",
                "📍 Use terrain - fight on bridges, stairs, chokepoints",
                "❌ Avoid: Standing still and trading melee",
            ],
            "key_targets": ["Herald tag", "Supports in back", "Isolated frontline"],
            "avoid": ["Meeting their push head-on", "Open field fights", "Blob vs blob"],
        },
        "Ranged Poke / Siege Comp": {
            "notes": [
                "🎯 Rush in fast before they can siege up",
                "⚡ Stack mobility - Willbenders, Vindicators, speed",
                "🗡️ Dive their backline with burst damage",
                "📍 Don't let them setup - constant pressure",
                "❌ Avoid: Long sieges, poking back, playing their game",
            ],
            "key_targets": ["Scourges", "Tempests", "Catalysts"],
            "avoid": ["Standing at range", "Letting them siege", "Tower trades"],
        },
        "Balanced Composition": {
            "notes": [
                "🎯 Identify their win condition and deny it",
                "⚡ Play to your composition's strengths",
                "🗡️ Focus targets of opportunity - overextenders",
                "📍 Control tempo - push when you have advantage",
                "❌ Avoid: Predictable patterns, single strategies",
            ],
            "key_targets": ["Commander", "Supports", "Isolated players"],
            "avoid": ["Overcommitting", "Ego plays", "Ignoring callouts"],
        },
    }
    
    # Build recommendations with links
    BUILD_DATABASE = {
        "Scourge": {
            "role": "Backline",
            "url": "https://metabattle.com/wiki/Build:Scourge_-_Zerg_Shadefire",
            "priority_vs": ["Support Heavy", "Frontline Heavy"]
        },
        "Spellbreaker": {
            "role": "Frontline",
            "url": "https://metabattle.com/wiki/Build:Spellbreaker_-_Zerg_Hammer",
            "priority_vs": ["Support Heavy", "Boon Heavy"]
        },
        "Firebrand": {
            "role": "Support",
            "url": "https://metabattle.com/wiki/Build:Firebrand_-_Zerg_Support",
            "priority_vs": ["Condition Heavy", "Melee Heavy"]
        },
        "Scrapper": {
            "role": "Support",
            "url": "https://metabattle.com/wiki/Build:Scrapper_-_Zerg_Gyro_Support",
            "priority_vs": ["Melee Heavy", "Ranged Heavy"]
        },
        "Herald": {
            "role": "Frontline",
            "url": "https://metabattle.com/wiki/Build:Herald_-_Zerg_Frontline",
            "priority_vs": ["Ranged Heavy", "Low Stability"]
        },
        "Chronomancer": {
            "role": "Support",
            "url": "https://metabattle.com/wiki/Build:Chronomancer_-_Zerg_Support",
            "priority_vs": ["Boon Heavy", "Support Heavy"]
        },
        "Tempest": {
            "role": "Backline",
            "url": "https://metabattle.com/wiki/Build:Tempest_-_Zerg_Staff",
            "priority_vs": ["Melee Heavy", "Clumped Enemy"]
        },
        "Willbender": {
            "role": "Roamer",
            "url": "https://metabattle.com/wiki/Build:Willbender_-_Roamer",
            "priority_vs": ["Backline Heavy", "Ranged Heavy"]
        },
        "Vindicator": {
            "role": "Frontline",
            "url": "https://metabattle.com/wiki/Build:Vindicator_-_Zerg_Greatsword",
            "priority_vs": ["Ranged Heavy", "Spread Formation"]
        },
        "Harbinger": {
            "role": "Backline",
            "url": "https://metabattle.com/wiki/Build:Harbinger_-_Zerg_Condi",
            "priority_vs": ["Low Cleanse", "Melee Heavy"]
        },
        "Reaper": {
            "role": "Frontline",
            "url": "https://metabattle.com/wiki/Build:Reaper_-_Zerg_Greatsword",
            "priority_vs": ["Low Stability", "Spread Formation"]
        },
        "Catalyst": {
            "role": "Backline",
            "url": "https://metabattle.com/wiki/Build:Catalyst_-_Zerg_Hammer",
            "priority_vs": ["Melee Heavy", "Clumped Enemy"]
        },
    }
    
    def generate_counter(self, enemy_comp: CompositionAnalysis) -> CounterRecommendation:
        """Generate optimal counter recommendation for enemy composition"""
        
        recommended_builds = []
        counter_scores = {}
        
        # Analyze enemy specs and find counters
        for spec, count in enemy_comp.spec_counts.items():
            if spec in self.COUNTERS:
                for counter_spec in self.COUNTERS[spec]["countered_by"]:
                    if counter_spec not in counter_scores:
                        counter_scores[counter_spec] = 0
                    # Weight by how many of that spec they have
                    counter_scores[counter_spec] += count
        
        # Also consider role-based counters
        for role, count in enemy_comp.role_distribution.items():
            if role in self.ROLE_COUNTERS:
                for counter_spec in self.ROLE_COUNTERS[role]:
                    if counter_spec not in counter_scores:
                        counter_scores[counter_spec] = 0
                    counter_scores[counter_spec] += count * 0.5
        
        # Sort by counter effectiveness
        sorted_counters = sorted(counter_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Generate build recommendations
        for i, (spec, score) in enumerate(sorted_counters[:8]):
            if spec in self.BUILD_DATABASE:
                build_info = self.BUILD_DATABASE[spec]
                
                # Determine priority (1-5)
                if i < 2:
                    priority = 5
                elif i < 4:
                    priority = 4
                elif i < 6:
                    priority = 3
                else:
                    priority = 2
                
                # Generate reason
                reason = self._generate_counter_reason(spec, enemy_comp)
                
                recommended_builds.append(CounterBuild(
                    elite_spec=spec,
                    role=build_info["role"],
                    priority=priority,
                    reason=reason,
                    build_url=build_info["url"]
                ))
        
        # Get strategy based on enemy comp type
        strategy = self.STRATEGIES.get(
            enemy_comp.estimated_squad_type,
            self.STRATEGIES["Balanced Composition"]
        )
        
        # Calculate confidence score
        confidence = min(95, 60 + len(enemy_comp.spec_counts) * 2)
        
        return CounterRecommendation(
            recommended_builds=recommended_builds,
            strategy_notes=strategy["notes"],
            key_targets=strategy["key_targets"],
            avoid_list=strategy["avoid"],
            confidence_score=confidence
        )
    
    def _generate_counter_reason(self, counter_spec: str, enemy_comp: CompositionAnalysis) -> str:
        """Generate a specific reason for recommending this counter"""
        dominant_spec = enemy_comp.dominant_specs[0][0] if enemy_comp.dominant_specs else "Unknown"
        
        reasons = {
            "Scourge": f"Corrupt {enemy_comp.spec_counts.get('Firebrand', 0)} FBs and strip enemy boons",
            "Spellbreaker": f"Strip stability from {enemy_comp.role_distribution.get('Frontline', 0)} frontliners",
            "Firebrand": f"Counter {enemy_comp.role_distribution.get('Backline', 0)} backline with Aegis spam",
            "Scrapper": f"Superspeed your squad past their {dominant_spec} pressure",
            "Herald": f"Facetank their {enemy_comp.total_players} players with boon uptime",
            "Chronomancer": f"Strip and distort against their {dominant_spec} burst",
            "Tempest": f"Overload on their clumped {enemy_comp.estimated_squad_type}",
            "Willbender": f"Dive their {enemy_comp.role_distribution.get('Backline', 0)} backline players",
            "Vindicator": f"Greatsword rush through their {enemy_comp.role_distribution.get('Support', 0)} supports",
            "Harbinger": f"Condition pressure their low-cleanse comp",
            "Reaper": f"Shroud through their {dominant_spec} damage",
            "Catalyst": f"Jade Sphere zone control against their push",
        }
        
        return reasons.get(counter_spec, f"Strong against {dominant_spec}")
    
    def get_current_meta(self) -> Dict:
        """Get current WvW meta data for 2025"""
        return {
            "tier_s": [
                {"spec": "Firebrand", "role": "Support", "usage": 94},
                {"spec": "Scrapper", "role": "Support", "usage": 89},
                {"spec": "Scourge", "role": "Backline", "usage": 85},
            ],
            "tier_a": [
                {"spec": "Herald", "role": "Frontline", "usage": 78},
                {"spec": "Spellbreaker", "role": "Frontline", "usage": 72},
                {"spec": "Tempest", "role": "Backline", "usage": 68},
            ],
            "tier_b": [
                {"spec": "Willbender", "role": "Roamer", "usage": 55},
                {"spec": "Vindicator", "role": "Frontline", "usage": 52},
                {"spec": "Harbinger", "role": "Backline", "usage": 48},
                {"spec": "Chronomancer", "role": "Support", "usage": 45},
            ],
            "tier_c": [
                {"spec": "Berserker", "role": "Frontline", "usage": 35},
                {"spec": "Reaper", "role": "Frontline", "usage": 32},
                {"spec": "Catalyst", "role": "Backline", "usage": 28},
            ],
            "rising": [
                {"spec": "Vindicator", "change": "+12%", "reason": "Alliance stance buffs"},
                {"spec": "Harbinger", "change": "+8%", "reason": "Elixir rework"},
            ],
            "falling": [
                {"spec": "Dragonhunter", "change": "-15%", "reason": "Trap nerfs"},
                {"spec": "Weaver", "change": "-10%", "reason": "Sword nerf"},
            ],
            "last_updated": "December 2025"
        }
