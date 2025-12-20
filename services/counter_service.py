"""
GW2 CounterPicker - Stats-Based Counter Service
Pure data-driven counter recommendations without LLM dependencies
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from tinydb import Query, TinyDB

from counter_engine import CounterPickEngine
from logger import get_logger

logger = get_logger('counter_service')


class FightContext(str, Enum):
    """Type of WvW combat - affects stats and recommendations"""
    ZERG = "zerg"
    GUILD_RAID = "guild_raid"
    ROAM = "roam"
    UNKNOWN = "unknown"
    
    @classmethod
    def from_string(cls, value: str) -> 'FightContext':
        """Convert string to FightContext, defaults to UNKNOWN"""
        if not value or value == 'auto':
            return cls.UNKNOWN
        try:
            return cls(value.lower())
        except ValueError:
            return cls.UNKNOWN


def guess_fight_context(
    ally_count: int,
    enemy_count: int,
    duration_sec: float,
    subgroup_count: int = 1,
    main_guild_ratio: float = 0.0
) -> FightContext:
    """
    Auto-detect fight context based on available metrics.
    
    Heuristics:
    - Roaming: <= 10 allies AND <= 12 enemies
    - Zerg: >= 25 allies OR >= 30 enemies
    - Guild Raid: 10-25 allies with high guild cohesion OR structured subgroups
    - Unknown: ambiguous cases that need user confirmation
    """
    if ally_count <= 10 and enemy_count <= 12:
        return FightContext.ROAM
    
    if ally_count >= 25 or enemy_count >= 30:
        return FightContext.ZERG
    
    if 10 <= ally_count <= 25:
        if main_guild_ratio >= 0.5:
            return FightContext.GUILD_RAID
        if subgroup_count >= 2:
            return FightContext.GUILD_RAID
    
    if 10 <= ally_count <= 25:
        if enemy_count >= 20:
            return FightContext.ZERG
        return FightContext.UNKNOWN
    
    return FightContext.UNKNOWN


@dataclass
class AllyBuildRecord:
    """Detailed build information for an ally player"""
    player_name: str
    account: str
    profession: str
    elite_spec: str
    role: str
    group: int
    damage_out: int
    damage_in: int
    dps: float
    healing: int
    cleanses: int
    boon_strips: int
    down_contrib: int
    deaths: int
    boon_gen: Dict[str, float]
    kills: int = 0
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class FightRecord:
    """Record of a single fight for learning"""
    fight_id: str
    timestamp: str
    source: str
    source_name: str
    enemy_composition: Dict[str, int]
    ally_composition: Dict[str, int]
    ally_builds: List[Dict[str, Any]]
    outcome: str
    duration_sec: float
    ally_deaths: int
    ally_kills: int
    enemy_deaths: int
    total_ally_damage: int
    total_enemy_damage: int
    context_detected: str = "unknown"
    context_confirmed: Optional[str] = None
    
    @property
    def context(self) -> str:
        """Returns confirmed context if set, otherwise detected"""
        return self.context_confirmed or self.context_detected
    
    def to_dict(self) -> dict:
        data = asdict(self)
        data['context'] = self.context
        return data
    
    @classmethod
    def from_dict(cls, data: dict) -> 'FightRecord':
        data = {k: v for k, v in data.items() if k != 'context'}
        return cls(**data)


class CounterService:
    """
    Stats-based counter recommendation service
    Uses historical fight data and rule-based engine
    """
    
    def __init__(self, db_path: Path = Path("data/fights.db")):
        """Initialize counter service with TinyDB storage"""
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.db = TinyDB(str(db_path))
        self.fights_table = self.db.table('fights')
        self.stats_table = self.db.table('stats')
        self.builds_table = self.db.table('builds')
        self.analyzed_files_table = self.db.table('analyzed_files')
        self.fingerprints_table = self.db.table('fight_fingerprints')
        self.feedback_table = self.db.table('feedback')
        self.settings_table = self.db.table('settings')
        
        self.counter_engine = CounterPickEngine()
    
    def is_file_already_analyzed(self, filename: str, filesize: int) -> bool:
        """Check if a file with the same name and size has already been analyzed"""
        FileQuery = Query()
        existing = self.analyzed_files_table.search(
            (FileQuery.filename == filename) & (FileQuery.filesize == filesize)
        )
        return len(existing) > 0
    
    def mark_file_as_analyzed(self, filename: str, filesize: int, fight_id: str) -> None:
        """Mark a file as analyzed to prevent duplicate processing"""
        self.analyzed_files_table.insert({
            'filename': filename,
            'filesize': filesize,
            'fight_id': fight_id,
            'analyzed_at': datetime.now().isoformat()
        })
    
    def generate_fight_fingerprint(self, fight_data: dict) -> str:
        """
        Generate a unique fingerprint for a fight that INCLUDES the perspective.
        
        This ensures that:
        - Same guild members uploading same fight = DUPLICATE (blocked)
        - Allied guild uploading their perspective = DIFFERENT (allowed)
        - Enemy guild uploading their perspective = DIFFERENT (allowed)
        """
        duration = fight_data.get('duration_sec', 0)
        duration_bucket = int(duration // 5) * 5
        
        allies = fight_data.get('allies', [])
        ally_accounts = sorted([a.get('account', a.get('name', 'Unknown'))[:20] for a in allies])
        ally_accounts_hash = "_".join(ally_accounts[:10])
        
        ally_specs = sorted([a.get('profession', 'Unknown') for a in allies])
        ally_specs_hash = "_".join(ally_specs)
        
        total_damage = fight_data.get('fight_stats', {}).get('ally_damage', 0)
        damage_bucket = int(total_damage // 50000) * 50000
        
        fingerprint_data = f"{duration_bucket}|{ally_accounts_hash}|{ally_specs_hash}|{damage_bucket}"
        return hashlib.md5(fingerprint_data.encode()).hexdigest()[:16]
    
    def is_fight_duplicate(self, fingerprint: str) -> bool:
        """Check if a fight with this fingerprint already exists"""
        FpQuery = Query()
        existing = self.fingerprints_table.search(FpQuery.fingerprint == fingerprint)
        return len(existing) > 0
    
    def mark_fight_fingerprint(self, fingerprint: str, fight_id: str) -> None:
        """Store a fight fingerprint to prevent duplicates"""
        self.fingerprints_table.insert({
            'fingerprint': fingerprint,
            'fight_id': fight_id,
            'created_at': datetime.now().isoformat()
        })
    
    def cleanup_old_fingerprints(self, days_old: int = 7) -> None:
        """Remove fingerprints older than X days"""
        cutoff = datetime.now() - timedelta(days=days_old)
        cutoff_str = cutoff.isoformat()
        
        FpQuery = Query()
        removed = self.fingerprints_table.remove(FpQuery.created_at < cutoff_str)
        if removed:
            logger.info(f"Cleaned up {len(removed)} old fingerprints")
    
    def record_fight(
        self,
        fight_data: dict,
        filename: str = None,
        filesize: int = None,
        context: str = "auto"
    ) -> Optional[str]:
        """
        Record a fight for learning with detailed ally build information
        
        Args:
            fight_data: Parsed fight data
            filename: Original filename (for deduplication)
            filesize: File size in bytes (for deduplication)
            context: Fight context - "auto", "zerg", "guild_raid", "roam", or "unknown"
        
        Returns the fight_id, or None if file was already analyzed
        """
        if filename and filesize:
            if self.is_file_already_analyzed(filename, filesize):
                logger.debug(f"Skipping duplicate file: {filename} ({filesize} bytes)")
                return None
        
        fingerprint = self.generate_fight_fingerprint(fight_data)
        if self.is_fight_duplicate(fingerprint):
            logger.debug(f"Skipping duplicate fight (fingerprint: {fingerprint})")
            if filename and filesize:
                self.mark_file_as_analyzed(filename, filesize, f"duplicate_{fingerprint}")
            return None
        
        duration_sec = fight_data.get('duration_sec', 0)
        if duration_sec < 60:
            logger.debug(f"Skipping short fight ({duration_sec}s) - minimum 60s required")
            if filename and filesize:
                self.mark_file_as_analyzed(filename, filesize, f"short_{duration_sec}s")
            return None
        
        fight_id = f"fight_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.fights_table)}"
        
        enemy_comp = {}
        ally_comp = {}
        
        if 'enemy_composition' in fight_data:
            enemy_comp = fight_data['enemy_composition'].get('spec_counts', {})
        
        if not enemy_comp and 'enemies' in fight_data:
            for enemy in fight_data['enemies']:
                spec = enemy.get('profession', 'Unknown')
                if spec and spec != 'Unknown':
                    enemy_comp[spec] = enemy_comp.get(spec, 0) + 1
        
        if 'composition' in fight_data:
            ally_comp = fight_data['composition'].get('spec_counts', {})
        
        if not ally_comp and 'allies' in fight_data:
            for ally in fight_data['allies']:
                spec = ally.get('profession', 'Unknown')
                if spec and spec != 'Unknown':
                    ally_comp[spec] = ally_comp.get(spec, 0) + 1
        
        ally_builds = []
        for ally in fight_data.get('allies', []):
            build_record = AllyBuildRecord(
                player_name=ally.get('name', 'Unknown'),
                account=ally.get('account', ''),
                profession=ally.get('profession', 'Unknown'),
                elite_spec=ally.get('profession', 'Unknown'),
                role=ally.get('role', 'dps'),
                group=ally.get('group', 0),
                damage_out=ally.get('damage_out', ally.get('damage', 0)),
                damage_in=ally.get('damage_in', 0),
                dps=ally.get('dps', 0),
                healing=ally.get('healing', 0),
                cleanses=ally.get('cleanses', 0),
                boon_strips=ally.get('boon_strips', 0),
                down_contrib=ally.get('down_contrib', 0),
                deaths=ally.get('deaths', 0),
                kills=ally.get('kills', 0),
                boon_gen=ally.get('boon_gen', {})
            )
            ally_builds.append(build_record.to_dict())
        
        outcome = fight_data.get('fight_outcome', 'unknown')
        if outcome == 'unknown':
            fight_stats = fight_data.get('fight_stats', {})
            ally_deaths = fight_stats.get('ally_deaths', 0)
            ally_kills = fight_stats.get('ally_kills', 0)
            
            if ally_kills > 0 and ally_deaths == 0:
                outcome = 'victory'
            elif ally_kills > ally_deaths:
                outcome = 'victory'
            elif ally_deaths > ally_kills * 2 and ally_deaths >= 3:
                outcome = 'defeat'
            elif ally_deaths > ally_kills and ally_deaths >= 5:
                outcome = 'defeat'
            else:
                outcome = 'draw'
        
        ally_count = len(fight_data.get('allies', []))
        enemy_count = len(fight_data.get('enemies', []))
        
        subgroups = set(b.get('group', 0) for b in ally_builds if b.get('group', 0) > 0)
        subgroup_count = len(subgroups) if subgroups else 1
        
        main_guild_ratio = 0.0
        
        if context == "auto" or not context:
            detected_context = guess_fight_context(
                ally_count=ally_count,
                enemy_count=enemy_count,
                duration_sec=duration_sec,
                subgroup_count=subgroup_count,
                main_guild_ratio=main_guild_ratio
            )
            context_detected = detected_context.value
            context_confirmed = None
        else:
            context_detected = guess_fight_context(
                ally_count=ally_count,
                enemy_count=enemy_count,
                duration_sec=duration_sec,
                subgroup_count=subgroup_count,
                main_guild_ratio=main_guild_ratio
            ).value
            context_confirmed = FightContext.from_string(context).value
        
        record = FightRecord(
            fight_id=fight_id,
            timestamp=fight_data.get('timestamp', datetime.now().isoformat()),
            source=fight_data.get('source', 'evtc'),
            source_name=fight_data.get('source_name', 'unknown'),
            enemy_composition=enemy_comp,
            ally_composition=ally_comp,
            ally_builds=ally_builds,
            outcome=outcome,
            duration_sec=fight_data.get('duration_sec', 0),
            ally_deaths=fight_data.get('fight_stats', {}).get('ally_deaths', 0),
            ally_kills=fight_data.get('fight_stats', {}).get('ally_kills', 0),
            enemy_deaths=fight_data.get('fight_stats', {}).get('ally_kills', 0),
            total_ally_damage=fight_data.get('fight_stats', {}).get('ally_damage', 0),
            total_enemy_damage=fight_data.get('fight_stats', {}).get('enemy_damage_taken', 0),
            context_detected=context_detected,
            context_confirmed=context_confirmed
        )
        
        self.fights_table.insert(record.to_dict())
        self._update_stats()
        self._store_build_performance(ally_builds, enemy_comp, outcome, record.context)
        
        logger.info(f"Recorded fight {fight_id}: {outcome} [{record.context}] vs {list(enemy_comp.keys())[:3]}... ({len(ally_builds)} builds)")
        
        if filename and filesize:
            self.mark_file_as_analyzed(filename, filesize, fight_id)
        
        self.mark_fight_fingerprint(fingerprint, fight_id)
        
        return fight_id
    
    def _store_build_performance(
        self,
        ally_builds: List[dict],
        enemy_comp: Dict[str, int],
        outcome: str,
        context: str = "unknown"
    ) -> None:
        """Store individual build performance against specific enemy compositions"""
        for build in ally_builds:
            spec = build.get('elite_spec', build.get('profession', 'Unknown'))
            role = build.get('role', 'dps')
            
            dps = build.get('dps', 0)
            healing = build.get('healing', 0)
            down_contrib = build.get('down_contrib', 0)
            deaths = build.get('deaths', 0)
            
            if role == 'healer':
                score = healing + (build.get('cleanses', 0) * 10)
            elif role == 'stab':
                score = sum(build.get('boon_gen', {}).values()) * 100
            elif role == 'dps_strip':
                score = build.get('boon_strips', 0) * 50 + dps
            else:
                score = dps + (down_contrib * 2)
            
            score = max(0, score - (deaths * 5000))
            
            self.builds_table.insert({
                'spec': spec,
                'role': role,
                'context': context,
                'enemy_comp_hash': self._hash_composition(enemy_comp),
                'enemy_comp': enemy_comp,
                'outcome': outcome,
                'performance_score': score,
                'dps': dps,
                'healing': healing,
                'cleanses': build.get('cleanses', 0),
                'boon_strips': build.get('boon_strips', 0),
                'down_contrib': down_contrib,
                'deaths': deaths,
                'boon_gen': build.get('boon_gen', {}),
                'timestamp': datetime.now().isoformat()
            })
    
    def _hash_composition(self, comp: Dict[str, int]) -> str:
        """Create a hash for an enemy composition for quick lookups"""
        sorted_comp = sorted(comp.items())
        return "-".join([f"{spec}:{count}" for spec, count in sorted_comp])
    
    def _update_stats(self) -> None:
        """Update global stats"""
        total_fights = len(self.fights_table)
        victories = len(self.fights_table.search(Query().outcome == 'victory'))
        
        self.stats_table.truncate()
        self.stats_table.insert({
            'total_fights': total_fights,
            'victories': victories,
            'win_rate': round((victories / total_fights * 100) if total_fights > 0 else 0, 1),
            'last_updated': datetime.now().isoformat()
        })
    
    def get_stats(self) -> dict:
        """Get current learning stats"""
        stats = self.stats_table.all()
        if stats:
            return stats[0]
        return {
            'total_fights': 0,
            'victories': 0,
            'win_rate': 0,
            'last_updated': None
        }
    
    def _calculate_composition_similarity(
        self, 
        comp1: Dict[str, int], 
        comp2: Dict[str, int],
        weight_by_role: bool = True
    ) -> float:
        """
        Calcule la similarité entre deux compositions avec pondération optionnelle par rôle.
        Utilise une distance de Manhattan pondérée, plus robuste que cosinus pour vecteurs creux.
        
        Args:
            comp1: Première composition {spec: count}
            comp2: Deuxième composition {spec: count}
            weight_by_role: Appliquer les poids par importance stratégique
        
        Returns:
            Score de similarité entre 0.0 (totalement différent) et 1.0 (identique)
        """
        from role_detector import STAB_SPECS, HEALER_SPECS, BOON_SPECS, STRIP_DPS_SPECS
        
        # Poids par importance stratégique (stab/heal > boon > strip > dps)
        ROLE_WEIGHTS = {
            'stab': 2.0,      # Stab providers sont critiques
            'healer': 1.8,    # Healers aussi
            'boon': 1.5,      # Boon providers importants
            'strip': 1.3,     # Strip utile
            'dps': 1.0        # DPS baseline
        }
        
        def get_spec_weight(spec: str) -> float:
            """Retourne le poids stratégique d'une spec"""
            if not weight_by_role:
                return 1.0
            if spec in STAB_SPECS:
                return ROLE_WEIGHTS['stab']
            if spec in HEALER_SPECS:
                return ROLE_WEIGHTS['healer']
            if spec in BOON_SPECS:
                return ROLE_WEIGHTS['boon']
            if spec in STRIP_DPS_SPECS:
                return ROLE_WEIGHTS['strip']
            return ROLE_WEIGHTS['dps']
        
        # Toutes les specs présentes dans au moins une compo
        all_specs = set(comp1.keys()) | set(comp2.keys())
        
        if not all_specs:
            return 0.0
        
        # Distance Manhattan pondérée
        total_distance = 0.0
        total_weight = 0.0
        
        for spec in all_specs:
            count1 = comp1.get(spec, 0)
            count2 = comp2.get(spec, 0)
            weight = get_spec_weight(spec)
            
            total_distance += abs(count1 - count2) * weight
            total_weight += max(count1, count2) * weight
        
        # Normaliser : 1.0 = identique, 0.0 = totalement différent
        if total_weight == 0:
            return 0.0
        
        similarity = 1.0 - (total_distance / (2 * total_weight))
        return max(0.0, min(1.0, similarity))
    
    def _find_similar_fights(
        self,
        enemy_comp: Dict[str, int],
        limit: int = 30,
        context: str = None,
        time_decay: bool = True
    ) -> List[dict]:
        """
        Find fights with similar enemy compositions, avec pondération temporelle.
        
        Args:
            enemy_comp: Enemy composition to match against
            limit: Maximum number of fights to return
            context: Fight context filter (zerg/guild_raid/roam)
            time_decay: Apply time-based weighting (recent fights = more weight)
        
        Returns:
            List of similar fights, sorted by relevance
        """
        all_fights = self.fights_table.all()
        
        scored_fights = []
        now = datetime.now()
        
        for fight in all_fights:
            if context:
                fight_context = fight.get('context_confirmed') or fight.get('context_detected') or fight.get('context', 'unknown')
                if fight_context != context:
                    continue
            
            fight_enemy_comp = fight.get('enemy_composition', {})
            
            # Utiliser la nouvelle méthode de similarité pondérée par rôle
            similarity = self._calculate_composition_similarity(enemy_comp, fight_enemy_comp, weight_by_role=True)
            
            if similarity < 0.3:
                continue
            
            # Facteur temporel : fights récents = plus de poids
            time_weight = 1.0
            if time_decay:
                try:
                    fight_time = datetime.fromisoformat(fight.get('timestamp', now.isoformat()))
                    days_old = (now - fight_time).days
                    
                    # Décroissance exponentielle douce
                    if days_old <= 7:
                        time_weight = 1.0
                    elif days_old <= 30:
                        time_weight = 0.9
                    elif days_old <= 60:
                        time_weight = 0.7
                    elif days_old <= 90:
                        time_weight = 0.5
                    else:
                        time_weight = 0.3
                except:
                    time_weight = 0.8  # Fallback si pas de timestamp
            
            # Score final combiné
            final_score = similarity * time_weight
            
            scored_fights.append({
                'fight': fight,
                'similarity': similarity,
                'time_weight': time_weight,
                'final_score': final_score
            })
        
        # Trier par score final (similarité × temps)
        scored_fights.sort(key=lambda x: x['final_score'], reverse=True)
        return [sf['fight'] for sf in scored_fights[:limit]]
    
    def _analyze_enemy_needs(self, enemy_comp: Dict[str, int]) -> Dict[str, float]:
        """
        Analyse la compo ennemie pour déterminer nos besoins défensifs/offensifs.
        
        Args:
            enemy_comp: Composition ennemie {spec: count}
        
        Returns:
            Dict avec scores de besoin (0.0 à 1.0) pour chaque rôle tactique
        """
        from role_detector import STAB_SPECS, HEALER_SPECS, BOON_SPECS
        
        total_enemies = sum(enemy_comp.values())
        if total_enemies == 0:
            return {'strip': 0.5, 'stab': 0.5, 'heal': 0.5, 'boon': 0.5, 'burst': 0.5}
        
        # Compter les specs par rôle ennemi
        enemy_stab_count = sum(count for spec, count in enemy_comp.items() if spec in STAB_SPECS)
        enemy_healer_count = sum(count for spec, count in enemy_comp.items() if spec in HEALER_SPECS)
        enemy_boon_count = sum(count for spec, count in enemy_comp.items() if spec in BOON_SPECS)
        enemy_scourge_count = enemy_comp.get('Scourge', 0) + enemy_comp.get('Harbinger', 0)
        
        # Ratios
        stab_ratio = enemy_stab_count / total_enemies
        healer_ratio = enemy_healer_count / total_enemies
        boon_ratio = enemy_boon_count / total_enemies
        condi_ratio = enemy_scourge_count / total_enemies
        
        needs = {
            # Beaucoup de boons ennemis → besoin élevé de strip
            'strip': min(1.0, (stab_ratio + boon_ratio) * 1.5),
            
            # Beaucoup de condi ennemis → besoin de cleanse/heal
            'heal': min(1.0, 0.3 + condi_ratio * 1.2 + healer_ratio * 0.5),
            
            # Baseline stab toujours utile, augmenté si ils ont du CC
            'stab': min(1.0, 0.4 + enemy_scourge_count / total_enemies),
            
            # Besoin de boons proportionnel à leur sustain
            'boon': min(1.0, 0.4 + (healer_ratio + stab_ratio) * 0.8),
            
            # Burst damage si ils ont beaucoup de sustain
            'burst': min(1.0, 0.5 + (healer_ratio + stab_ratio) * 1.0),
        }
        
        return needs
    
    def _get_meta_tags(self, enemy_comp: Dict[str, int], needs: Dict[str, float]) -> List[str]:
        """
        Génère des tags lisibles en français pour la compo ennemie.
        
        Args:
            enemy_comp: Composition ennemie
            needs: Besoins tactiques calculés
        
        Returns:
            Liste de tags descriptifs
        """
        tags = []
        
        # Tags basés sur les besoins tactiques
        if needs['strip'] > 0.7:
            tags.append("🛡️ Beaucoup de boons")
        if needs['heal'] > 0.7:
            tags.append("☠️ Beaucoup d'altérations")
        if needs['burst'] > 0.7:
            tags.append("🏰 Beaucoup de supports")
        
        # Tags basés sur la taille
        total = sum(enemy_comp.values())
        if total <= 10:
            tags.append("👥 Petit groupe")
        elif total >= 30:
            tags.append("🌊 Gros blob")
        
        return tags
    
    def _calculate_confidence(
        self,
        similar_fights: List[dict],
        best_builds: Dict[str, dict],
        enemy_comp: Dict[str, int]
    ) -> Dict[str, Any]:
        """
        Calcule un niveau de confiance détaillé pour la recommandation.
        
        Args:
            similar_fights: Liste des fights similaires trouvés
            best_builds: Meilleurs builds recommandés par rôle
            enemy_comp: Composition ennemie analysée
        
        Returns:
            Dict avec score de confiance, niveau, couleur et explications
        """
        confidence_factors = {
            'data_quantity': 0.0,
            'data_quality': 0.0,
            'consistency': 0.0,
            'recency': 0.0
        }
        
        # 1. Quantité de données (plus de fights = plus de confiance)
        fight_count = len(similar_fights)
        if fight_count >= 20:
            confidence_factors['data_quantity'] = 1.0
        elif fight_count >= 10:
            confidence_factors['data_quantity'] = 0.8
        elif fight_count >= 5:
            confidence_factors['data_quantity'] = 0.6
        elif fight_count >= 2:
            confidence_factors['data_quantity'] = 0.4
        else:
            confidence_factors['data_quantity'] = 0.2
        
        # 2. Qualité des données (variance des winrates = cohérence)
        if best_builds:
            winrates = [b['win_rate'] for b in best_builds.values()]
            if winrates:
                avg_wr = sum(winrates) / len(winrates)
                variance = sum((wr - avg_wr) ** 2 for wr in winrates) / len(winrates)
                
                # Faible variance = haute confiance (résultats cohérents)
                if variance < 100:  # Winrates très cohérents
                    confidence_factors['data_quality'] = 1.0
                elif variance < 300:
                    confidence_factors['data_quality'] = 0.7
                else:
                    confidence_factors['data_quality'] = 0.5
            else:
                confidence_factors['data_quality'] = 0.5
        else:
            confidence_factors['data_quality'] = 0.3
        
        # 3. Consistance (tous les builds ont assez de samples)
        if best_builds:
            min_fights = min(b['fights_played'] for b in best_builds.values())
            if min_fights >= 5:
                confidence_factors['consistency'] = 1.0
            elif min_fights >= 3:
                confidence_factors['consistency'] = 0.7
            else:
                confidence_factors['consistency'] = 0.4
        else:
            confidence_factors['consistency'] = 0.3
        
        # 4. Récence (fights récents = meilleure confiance pour la meta actuelle)
        if similar_fights:
            now = datetime.now()
            recent_fights = 0
            for fight in similar_fights:
                try:
                    fight_time = datetime.fromisoformat(fight.get('timestamp', now.isoformat()))
                    if (now - fight_time).days <= 30:
                        recent_fights += 1
                except:
                    pass
            
            recency_ratio = recent_fights / len(similar_fights)
            confidence_factors['recency'] = recency_ratio
        else:
            confidence_factors['recency'] = 0.0
        
        # Score global (moyenne pondérée)
        weights = {
            'data_quantity': 0.35,  # Quantité est le plus important
            'data_quality': 0.25,   # Qualité des données
            'consistency': 0.25,    # Consistance des résultats
            'recency': 0.15         # Récence (meta actuelle)
        }
        
        overall_confidence = sum(
            confidence_factors[k] * weights[k] 
            for k in confidence_factors
        )
        
        # Convertir en pourcentage et catégorie
        confidence_pct = round(overall_confidence * 100, 1)
        
        if confidence_pct >= 80:
            level = "Élevée"
            color = "success"
        elif confidence_pct >= 60:
            level = "Moyenne"
            color = "warning"
        else:
            level = "Faible"
            color = "danger"
        
        return {
            'score': confidence_pct,
            'level': level,
            'color': color,
            'factors': confidence_factors,
            'fights_analyzed': fight_count,
            'explanation': f"{fight_count} fights similaires analysés, confiance {level.lower()}"
        }
    
    def _spec_covers_need(self, spec: str, need: str) -> bool:
        """
        Helper pour vérifier si une spec couvre un besoin tactique.
        
        Args:
            spec: Nom de la spécialisation
            need: Type de besoin (strip/stab/heal/boon/burst)
        
        Returns:
            True si la spec couvre ce besoin
        """
        from role_detector import STAB_SPECS, HEALER_SPECS, BOON_SPECS, STRIP_DPS_SPECS
        
        if need == 'stab':
            return spec in STAB_SPECS
        elif need == 'heal':
            return spec in HEALER_SPECS
        elif need == 'boon':
            return spec in BOON_SPECS
        elif need == 'strip':
            return spec in STRIP_DPS_SPECS
        elif need == 'burst':
            return spec in ['Willbender', 'Vindicator', 'Bladesworn', 'Reaper']
        return False
    
    def get_best_builds_with_role_coverage(
        self, 
        enemy_comp: Dict[str, int], 
        context: str = None,
        squad_size: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Recommande une composition complète qui couvre tous les besoins tactiques.
        
        Args:
            enemy_comp: Composition ennemie
            context: Contexte du fight
            squad_size: Taille du squad à recommander
        
        Returns:
            Liste de builds recommandés avec quantités optimales
        """
        from role_detector import STAB_SPECS, HEALER_SPECS, BOON_SPECS, STRIP_DPS_SPECS
        
        # 1. Analyser les besoins tactiques
        needs = self._analyze_enemy_needs(enemy_comp)
        
        # 2. Récupérer les meilleurs builds par rôle
        best_by_role = self.get_best_builds_against(enemy_comp, context)
        
        if not best_by_role:
            return []
        
        # 3. Scorer chaque spec selon sa couverture des besoins
        spec_scores = {}
        for role, build_info in best_by_role.items():
            spec = build_info['spec']
            
            # Score de base : winrate normalisé
            base_score = build_info['win_rate'] / 100.0
            
            # Bonus selon la couverture des besoins
            coverage_score = 0.0
            
            if spec in STAB_SPECS:
                coverage_score += needs['stab'] * 0.3
            if spec in HEALER_SPECS:
                coverage_score += needs['heal'] * 0.3
            if spec in BOON_SPECS:
                coverage_score += needs['boon'] * 0.25
            if spec in STRIP_DPS_SPECS:
                coverage_score += needs['strip'] * 0.25
            
            # Bonus burst pour certaines specs
            if spec in ['Willbender', 'Vindicator', 'Bladesworn']:
                coverage_score += needs['burst'] * 0.2
            
            # Score final : 60% winrate + 40% couverture des besoins
            final_score = base_score * 0.6 + coverage_score * 0.4
            
            spec_scores[spec] = {
                **build_info,
                'coverage_score': round(coverage_score, 3),
                'final_score': round(final_score, 3),
                'needs_covered': [k for k, v in needs.items() if v > 0.5 and self._spec_covers_need(spec, k)]
            }
        
        # 4. Trier par score final
        sorted_builds = sorted(spec_scores.values(), key=lambda x: x['final_score'], reverse=True)
        
        # 5. Distribuer les slots (heuristique simple mais efficace)
        recommended_comp = []
        remaining_slots = squad_size
        
        for build in sorted_builds[:6]:  # Top 6 specs
            if remaining_slots <= 0:
                break
            
            # Allouer des slots selon le rôle et le score
            if build['role'] in ['stab', 'healer']:
                # Supports : 2-3 slots
                slots = min(3, max(2, remaining_slots // 5))
            elif build['role'] == 'boon':
                # Boon providers : 2 slots
                slots = min(2, remaining_slots // 6)
            else:
                # DPS : peut être plus nombreux
                slots = min(4, remaining_slots // 4)
            
            slots = max(1, min(slots, remaining_slots))
            
            if slots > 0:
                recommended_comp.append({
                    **build,
                    'recommended_count': slots
                })
                remaining_slots -= slots
        
        return recommended_comp
    
    def get_best_builds_against(self, enemy_comp: Dict[str, int], context: str = None) -> Dict[str, dict]:
        """
        Find the best performing builds against a similar enemy composition
        Returns dict of {role: best_build_info} for each role
        """
        all_builds = self.builds_table.all()
        
        if not all_builds:
            return {}
        
        enemy_specs = set(enemy_comp.keys())
        
        enemy_hash = self._hash_composition(enemy_comp)
        Fq = Query()
        fb_rows = self.feedback_table.search(Fq.enemy_comp_hash == enemy_hash)
        fb_total = len(fb_rows)
        fb_success = sum(1 for r in fb_rows if r.get('worked'))
        fb_rate = (fb_success / fb_total) if fb_total > 0 else None
        
        cfg = self.settings_table.all()
        feedback_weight = (cfg[0].get('feedback_weight', 0.0) if cfg else 0.0) or 0.0
        
        build_stats = {}
        winning_fight_comps = {}
        
        for build in all_builds:
            if context and build.get('context') != context:
                continue
            
            build_enemy_specs = set(build.get('enemy_comp', {}).keys())
            
            intersection = len(enemy_specs & build_enemy_specs)
            union = len(enemy_specs | build_enemy_specs)
            similarity = intersection / union if union > 0 else 0
            
            if similarity < 0.3:
                continue
            
            spec = build.get('spec', 'Unknown')
            role = build.get('role', 'dps')
            key = (spec, role)
            fight_id = build.get('fight_id', '')
            
            if key not in build_stats:
                build_stats[key] = {
                    'spec': spec,
                    'role': role,
                    'wins': 0,
                    'total': 0,
                    'scores': [],
                    'avg_dps': [],
                    'avg_healing': [],
                    'avg_strips': [],
                    'avg_cleanses': [],
                    'counts_in_wins': []
                }
            
            build_stats[key]['total'] += 1
            build_stats[key]['scores'].append(build.get('performance_score', 0))
            build_stats[key]['avg_dps'].append(build.get('dps', 0))
            build_stats[key]['avg_healing'].append(build.get('healing', 0))
            build_stats[key]['avg_strips'].append(build.get('boon_strips', 0))
            build_stats[key]['avg_cleanses'].append(build.get('cleanses', 0))
            
            if build.get('outcome') == 'victory':
                build_stats[key]['wins'] += 1
                if fight_id:
                    if fight_id not in winning_fight_comps:
                        winning_fight_comps[fight_id] = {}
                    if key not in winning_fight_comps[fight_id]:
                        winning_fight_comps[fight_id][key] = 0
                    winning_fight_comps[fight_id][key] += 1
        
        for fight_id, comp in winning_fight_comps.items():
            for key, count in comp.items():
                if key in build_stats:
                    build_stats[key]['counts_in_wins'].append(count)
        
        best_by_role = {}
        
        for key, stats in build_stats.items():
            spec, role = key
            total = stats['total']
            
            if total < 2:
                continue
            
            win_rate = round((stats['wins'] / total) * 100, 1)
            avg_score = sum(stats['scores']) / len(stats['scores']) if stats['scores'] else 0
            
            if fb_rate is not None and feedback_weight > 0:
                factor = 1 + feedback_weight * (fb_rate - 0.5)
                win_rate = round(max(0, min(100, win_rate * factor)), 1)
            
            counts = stats.get('counts_in_wins', [])
            recommended_count = round(sum(counts) / len(counts)) if counts else 1
            recommended_count = max(1, recommended_count)
            
            build_info = {
                'spec': spec,
                'role': role,
                'win_rate': win_rate,
                'fights_played': total,
                'avg_score': round(avg_score, 0),
                'avg_dps': round(sum(stats['avg_dps']) / len(stats['avg_dps']), 0) if stats['avg_dps'] else 0,
                'avg_healing': round(sum(stats['avg_healing']) / len(stats['avg_healing']), 0) if stats['avg_healing'] else 0,
                'avg_strips': round(sum(stats['avg_strips']) / len(stats['avg_strips']), 1) if stats['avg_strips'] else 0,
                'avg_cleanses': round(sum(stats['avg_cleanses']) / len(stats['avg_cleanses']), 1) if stats['avg_cleanses'] else 0,
                'recommended_count': recommended_count
            }
            
            if role not in best_by_role or build_info['win_rate'] > best_by_role[role]['win_rate']:
                best_by_role[role] = build_info
            elif build_info['win_rate'] == best_by_role[role]['win_rate']:
                if build_info['avg_score'] > best_by_role[role]['avg_score']:
                    best_by_role[role] = build_info
        
        return best_by_role
    
    def _format_enemy_comp(self, enemy_comp: Dict[str, int]) -> str:
        """Format enemy composition for display"""
        sorted_comp = sorted(enemy_comp.items(), key=lambda x: x[1], reverse=True)
        return " + ".join([f"{count} {spec}" for spec, count in sorted_comp])
    
    async def generate_counter(self, enemy_comp: Dict[str, int], context: str = "zerg") -> dict:
        """
        Generate counter recommendation using stats and rules
        
        Args:
            enemy_comp: Enemy composition {spec: count}
            context: Fight context - "zerg", "guild_raid", "roam"
        
        Returns dict with recommendation and metadata
        """
        stats = self.get_stats()
        similar_fights = self._find_similar_fights(enemy_comp, context=context)
        enemy_str = self._format_enemy_comp(enemy_comp)
        
        best_builds = self.get_best_builds_against(enemy_comp, context=context)
        
        # Phase 2: Calculer le niveau de confiance
        confidence = self._calculate_confidence(similar_fights, best_builds, enemy_comp)
        
        # Phase 3: Analyser les besoins tactiques et générer les meta-tags
        enemy_needs = self._analyze_enemy_needs(enemy_comp)
        meta_tags = self._get_meta_tags(enemy_comp, enemy_needs)
        
        # Phase 4: Générer une composition complète optimisée
        recommended_composition = self.get_best_builds_with_role_coverage(enemy_comp, context, squad_size=20)
        
        conter_specs = []
        for role, build in list(best_builds.items())[:5]:
            count = build.get('recommended_count', 1)
            spec = build.get('spec', 'Unknown')
            conter_specs.append(f"{count}x {spec}")
        
        if not conter_specs:
            if context == 'roam':
                conter_specs = ["1x Willbender", "1x Deadeye", "1x Soulbeast"]
            elif context == 'guild_raid':
                conter_specs = ["2x Spellbreaker", "2x Scourge", "2x Firebrand", "1x Scrapper"]
            else:
                conter_specs = ["3x Spellbreaker", "3x Scourge", "2x Firebrand", "2x Scrapper"]
        
        counter_lines = []
        if conter_specs:
            counter_lines.append(f"CONTER: {', '.join(conter_specs)}")
        
        has_fb = any('Firebrand' in spec for spec in enemy_comp.keys())
        has_scrapper = any('Scrapper' in spec for spec in enemy_comp.keys())
        has_scourge = any('Scourge' in spec for spec in enemy_comp.keys())
        has_herald = any('Herald' in spec or 'Vindicator' in spec for spec in enemy_comp.keys())
        has_thief = any('Thief' in spec or 'Specter' in spec or 'Deadeye' in spec or 'Daredevil' in spec for spec in enemy_comp.keys())
        has_druid = any('Druid' in spec for spec in enemy_comp.keys())
        has_tempest = any('Tempest' in spec for spec in enemy_comp.keys())
        has_virtuoso = any('Virtuoso' in spec for spec in enemy_comp.keys())
        
        priority_targets = []
        if has_druid or has_tempest:
            priority_targets.append("Healers (Druid/Tempest)")
        if has_fb:
            priority_targets.append("Firebrand")
        if has_herald:
            priority_targets.append("Herald")
        if has_scourge:
            priority_targets.append("Scourge")
        
        if priority_targets:
            counter_lines.append(f"FOCUS: {' > '.join(priority_targets[:3])}")
        else:
            top_enemy = sorted(enemy_comp.items(), key=lambda x: x[1], reverse=True)[:3]
            counter_lines.append(f"FOCUS: {' > '.join([spec for spec, _ in top_enemy])}")
        
        if context == 'roam':
            if has_thief:
                counter_lines.append("TACTIQUE: Révélation + CC chain, ne pas les laisser reset")
            elif has_virtuoso:
                counter_lines.append("TACTIQUE: Gap closer rapide, burst avant les clones")
            elif has_druid:
                counter_lines.append("TACTIQUE: Focus le Druid en premier, burst coordonné")
            else:
                counter_lines.append("TACTIQUE: Burst le plus squishy, kite si nécessaire")
        elif context == 'guild_raid':
            if has_fb and has_scrapper:
                counter_lines.append("TACTIQUE: Strip les aegis puis burst power synchronisé")
            elif has_scourge:
                counter_lines.append("TACTIQUE: Push rapide, ne pas laisser les shades s'installer")
            else:
                counter_lines.append("TACTIQUE: Coordination des burst windows sur le call")
        else:
            if has_fb:
                counter_lines.append("TACTIQUE: Strip les aegis avant le push, focus les FB")
            elif has_scrapper:
                counter_lines.append("TACTIQUE: Burst power coordonné pour percer le barrier")
            elif has_herald:
                counter_lines.append("TACTIQUE: Focus les Herald, ils feed les boons")
            else:
                counter_lines.append("TACTIQUE: Burst coordonné sur le tag ennemi")
        
        if similar_fights:
            wins = sum(1 for f in similar_fights if f.get('outcome') == 'victory')
            precision = round((wins / len(similar_fights)) * 100, 1)
        else:
            precision = 80.0
        
        return {
            'success': True,
            'counter': "\n".join(counter_lines[:4]),
            'precision': precision,
            'fights_analyzed': stats['total_fights'],
            'similar_fights': len(similar_fights),
            'model': 'stats_engine',
            'enemy_composition': enemy_str,
            'enemy_comp_dict': enemy_comp,
            'best_builds': best_builds,
            'recommended_composition': recommended_composition,
            'confidence': confidence,
            'enemy_needs': enemy_needs,
            'meta_tags': meta_tags,
            'generated_at': datetime.now().isoformat(),
            'context': context
        }
    
    def get_status(self) -> dict:
        """Get current service status for display"""
        stats = self.get_stats()
        
        unique_players = set()
        for fight in self.fights_table.all():
            for build in fight.get('ally_builds', []):
                account = build.get('account', '')
                if account:
                    unique_players.add(account)
        
        fights_with_composition = len([
            f for f in self.fights_table.all()
            if 'enemy_composition' in f and f['enemy_composition']
        ])
        
        return {
            'total_fights': fights_with_composition,
            'win_rate': stats['win_rate'],
            'unique_players': len(unique_players),
            'last_updated': stats.get('last_updated'),
            'status': 'active',
            'engine': 'stats_based'
        }
    
    def record_feedback(self, enemy_comp: Dict[str, int], worked: bool, context: str = "zerg") -> None:
        """Record user feedback on counter recommendations"""
        self.feedback_table.insert({
            'timestamp': datetime.now().isoformat(),
            'enemy_comp': enemy_comp or {},
            'enemy_comp_hash': self._hash_composition(enemy_comp or {}),
            'worked': bool(worked),
            'context': context
        })
    
    def get_feedback_summary(self) -> dict:
        """Get summary of user feedback"""
        rows = self.feedback_table.all()
        agg = {}
        for r in rows:
            h = r.get('enemy_comp_hash') or 'unknown'
            if h not in agg:
                agg[h] = {'hash': h, 'total': 0, 'worked': 0, 'contexts': {}}
            agg[h]['total'] += 1
            if r.get('worked'):
                agg[h]['worked'] += 1
            ctx = r.get('context', 'zerg')
            agg[h]['contexts'][ctx] = agg[h]['contexts'].get(ctx, 0) + 1
        
        result = []
        for h, v in agg.items():
            rate = (v['worked'] / v['total']) if v['total'] > 0 else 0.0
            result.append({
                'enemy_comp_hash': h,
                'total': v['total'],
                'worked': v['worked'],
                'success_rate': round(rate, 3),
                'contexts': v['contexts']
            })
        return {'count': len(rows), 'by_comp': result}
    
    def get_settings(self) -> dict:
        """Get service settings"""
        rows = self.settings_table.all()
        if rows:
            return rows[0]
        # Phase 2-4: Feedback weight par défaut à 0.35 (recommandation GPT-5.1)
        self.settings_table.insert({'feedback_weight': 0.35})
        return {'feedback_weight': 0.35}
    
    def update_settings(self, values: dict) -> dict:
        """Update service settings"""
        cur = self.get_settings()
        cur.update(values or {})
        self.settings_table.truncate()
        self.settings_table.insert(cur)
        return cur


# Global instance
_counter_service: Optional[CounterService] = None


def get_counter_service() -> CounterService:
    """Get or create the global counter service instance"""
    global _counter_service
    if _counter_service is None:
        _counter_service = CounterService()
    return _counter_service
