"""
GW2 CounterPicker v3.0 - IA VIVANTE
Système d'apprentissage automatique des counters WvW
Powered by Llama 3.2 8B via Ollama
"""

import json
import httpx
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, asdict
from pathlib import Path

from tinydb import TinyDB, Query

# === CONFIGURATION ===
OLLAMA_URL = "http://localhost:11434"
MODEL_NAME = "llama3.2"
FIGHTS_DB_PATH = Path("data/fights.db")

# Ensure data directory exists
FIGHTS_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# Initialize TinyDB for fight history
fights_db = TinyDB(str(FIGHTS_DB_PATH))
fights_table = fights_db.table('fights')
stats_table = fights_db.table('stats')
analyzed_files_table = fights_db.table('analyzed_files')  # Track analyzed files to avoid duplicates


@dataclass
class AllyBuildRecord:
    """Detailed build information for an ally player"""
    player_name: str
    account: str
    profession: str
    elite_spec: str
    role: str
    group: int
    
    # Performance stats
    damage_out: int
    damage_in: int
    dps: float
    healing: int
    cleanses: int
    boon_strips: int
    down_contrib: int
    deaths: int
    
    # Boon generation
    boon_gen: Dict[str, float]  # {boon_name: generation %}
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class FightRecord:
    """Record of a single fight for learning"""
    fight_id: str
    timestamp: str
    source: str  # 'evtc' or 'dps_report'
    source_name: str  # filename or permalink
    
    # Compositions
    enemy_composition: Dict[str, int]  # {spec: count}
    ally_composition: Dict[str, int]
    
    # Detailed ally builds (NEW)
    ally_builds: List[Dict[str, Any]]  # List of AllyBuildRecord dicts
    
    # Outcome
    outcome: str  # 'victory', 'defeat', 'draw'
    duration_sec: float
    ally_deaths: int
    ally_kills: int
    enemy_deaths: int
    
    # Stats
    total_ally_damage: int
    total_enemy_damage: int
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'FightRecord':
        return cls(**data)


class CounterAI:
    """
    IA Vivante - Learns from every fight uploaded
    Uses Llama 3.2 8B to generate counter recommendations
    """
    
    def __init__(self):
        self.ollama_available = False
        self._check_ollama()
    
    def _check_ollama(self) -> bool:
        """Check if Ollama is running and model is available"""
        try:
            response = httpx.get(f"{OLLAMA_URL}/api/tags", timeout=5.0)
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [m.get('name', '') for m in models]
                self.ollama_available = any(MODEL_NAME in name for name in model_names)
                if not self.ollama_available:
                    print(f"[CounterAI] Model {MODEL_NAME} not found. Available: {model_names}")
                else:
                    print(f"[CounterAI] ✓ Ollama ready with {MODEL_NAME}")
                return self.ollama_available
        except Exception as e:
            print(f"[CounterAI] Ollama not available: {e}")
            self.ollama_available = False
        return False
    
    def is_file_already_analyzed(self, filename: str, filesize: int) -> bool:
        """
        Check if a file with the same name and size has already been analyzed.
        Returns True if duplicate, False if new file.
        """
        FileQuery = Query()
        existing = analyzed_files_table.search(
            (FileQuery.filename == filename) & (FileQuery.filesize == filesize)
        )
        return len(existing) > 0
    
    def mark_file_as_analyzed(self, filename: str, filesize: int, fight_id: str):
        """Mark a file as analyzed to prevent duplicate processing"""
        analyzed_files_table.insert({
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
        
        Fingerprint components:
        - Duration (rounded to 5 seconds)
        - Sorted ally ACCOUNT NAMES (unique to each guild's perspective)
        - Ally composition (specs)
        - Total ally damage (rounded to 50k)
        """
        import hashlib
        
        duration = fight_data.get('duration_sec', 0)
        duration_bucket = int(duration // 5) * 5  # Round to 5 seconds
        
        # Get ally account names - THIS IS THE KEY DIFFERENTIATOR
        # Each guild will have different ally accounts in their logs
        allies = fight_data.get('allies', [])
        ally_accounts = sorted([a.get('account', a.get('name', 'Unknown'))[:20] for a in allies])
        ally_accounts_hash = "_".join(ally_accounts[:10])  # Top 10 accounts
        
        # Get ally specs (secondary identifier)
        ally_specs = sorted([a.get('profession', 'Unknown') for a in allies])
        ally_specs_hash = "_".join(ally_specs)
        
        # Total damage bucket (perspective-specific)
        total_damage = fight_data.get('fight_stats', {}).get('ally_damage', 0)
        damage_bucket = int(total_damage // 50000) * 50000  # Round to 50k
        
        # Combine into fingerprint - includes WHO recorded it (ally accounts)
        fingerprint_data = f"{duration_bucket}|{ally_accounts_hash}|{ally_specs_hash}|{damage_bucket}"
        return hashlib.md5(fingerprint_data.encode()).hexdigest()[:16]
    
    def is_fight_duplicate(self, fingerprint: str) -> bool:
        """Check if a fight with this fingerprint already exists"""
        fingerprints_table = fights_db.table('fight_fingerprints')
        FpQuery = Query()
        existing = fingerprints_table.search(FpQuery.fingerprint == fingerprint)
        return len(existing) > 0
    
    def mark_fight_fingerprint(self, fingerprint: str, fight_id: str):
        """Store a fight fingerprint to prevent duplicates"""
        fingerprints_table = fights_db.table('fight_fingerprints')
        fingerprints_table.insert({
            'fingerprint': fingerprint,
            'fight_id': fight_id,
            'created_at': datetime.now().isoformat()
        })
    
    def cleanup_old_fingerprints(self, days_old: int = 7):
        """Remove fingerprints older than X days"""
        fingerprints_table = fights_db.table('fight_fingerprints')
        cutoff = datetime.now() - timedelta(days=days_old)
        cutoff_str = cutoff.isoformat()
        
        # Remove old fingerprints
        FpQuery = Query()
        removed = fingerprints_table.remove(FpQuery.created_at < cutoff_str)
        if removed:
            print(f"[CounterAI] Cleaned up {len(removed)} old fingerprints")
    
    def record_fight(self, fight_data: dict, filename: str = None, filesize: int = None) -> str:
        """
        Record a fight for learning with detailed ally build information
        Called automatically after each analysis
        Returns the fight_id, or None if file was already analyzed
        """
        # Check for duplicate file (same uploader)
        if filename and filesize:
            if self.is_file_already_analyzed(filename, filesize):
                print(f"[CounterAI] Skipping duplicate file: {filename} ({filesize} bytes)")
                return None
        
        # Check for duplicate fight (different uploaders, same fight)
        fingerprint = self.generate_fight_fingerprint(fight_data)
        if self.is_fight_duplicate(fingerprint):
            print(f"[CounterAI] Skipping duplicate fight (fingerprint: {fingerprint})")
            # Still mark file as analyzed so same person doesn't re-upload
            if filename and filesize:
                self.mark_file_as_analyzed(filename, filesize, f"duplicate_{fingerprint}")
            return None
        
        # Skip fights shorter than 60 seconds (not meaningful for analysis)
        duration_sec = fight_data.get('duration_sec', 0)
        if duration_sec < 60:
            print(f"[CounterAI] Skipping short fight ({duration_sec}s) - minimum 60s required")
            if filename and filesize:
                self.mark_file_as_analyzed(filename, filesize, f"short_{duration_sec}s")
            return None
        
        fight_id = f"fight_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(fights_table)}"
        
        # Extract compositions from fight data
        enemy_comp = {}
        ally_comp = {}
        
        # From enemy_composition (structured data)
        if 'enemy_composition' in fight_data:
            enemy_comp = fight_data['enemy_composition'].get('spec_counts', {})
        
        # Fallback: build enemy_comp from enemies list if spec_counts is empty
        if not enemy_comp and 'enemies' in fight_data:
            for enemy in fight_data['enemies']:
                spec = enemy.get('profession', 'Unknown')
                if spec and spec != 'Unknown':
                    enemy_comp[spec] = enemy_comp.get(spec, 0) + 1
        
        # From composition (allies)
        if 'composition' in fight_data:
            ally_comp = fight_data['composition'].get('spec_counts', {})
        
        # Fallback: build ally_comp from allies list if spec_counts is empty
        if not ally_comp and 'allies' in fight_data:
            for ally in fight_data['allies']:
                spec = ally.get('profession', 'Unknown')
                if spec and spec != 'Unknown':
                    ally_comp[spec] = ally_comp.get(spec, 0) + 1
        
        # Extract detailed ally builds (NEW)
        ally_builds = []
        for ally in fight_data.get('allies', []):
            build_record = AllyBuildRecord(
                player_name=ally.get('name', 'Unknown'),
                account=ally.get('account', ''),
                profession=ally.get('profession', 'Unknown'),
                elite_spec=ally.get('profession', 'Unknown'),  # Same as profession in WvW
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
                boon_gen=ally.get('boon_gen', {})
            )
            ally_builds.append(build_record.to_dict())
        
        # Determine outcome based on kill/death ratio
        outcome = fight_data.get('fight_outcome', 'unknown')
        if outcome == 'unknown':
            fight_stats = fight_data.get('fight_stats', {})
            ally_deaths = fight_stats.get('ally_deaths', 0)
            ally_kills = fight_stats.get('ally_kills', 0)
            
            # WvW outcome heuristic based on K/D ratio
            # Victory: we killed more than we lost
            # Defeat: we died significantly more than we killed
            # Draw: close fight or no clear winner
            if ally_kills > 0 and ally_deaths == 0:
                outcome = 'victory'  # Perfect fight
            elif ally_kills > ally_deaths:
                outcome = 'victory'  # Positive K/D
            elif ally_deaths > ally_kills * 2 and ally_deaths >= 3:
                outcome = 'defeat'  # Very negative K/D
            elif ally_deaths > ally_kills and ally_deaths >= 5:
                outcome = 'defeat'  # Wipe or heavy losses
            else:
                outcome = 'draw'  # Close fight or inconclusive
        
        record = FightRecord(
            fight_id=fight_id,
            timestamp=datetime.now().isoformat(),
            source=fight_data.get('source', 'evtc'),
            source_name=fight_data.get('source_name', 'unknown'),
            enemy_composition=enemy_comp,
            ally_composition=ally_comp,
            ally_builds=ally_builds,
            outcome=outcome,
            duration_sec=fight_data.get('duration_sec', 0),
            ally_deaths=fight_data.get('fight_stats', {}).get('ally_deaths', 0),
            ally_kills=fight_data.get('fight_stats', {}).get('ally_kills', 0),
            enemy_deaths=fight_data.get('fight_stats', {}).get('ally_kills', 0),  # enemy_deaths = our kills
            total_ally_damage=fight_data.get('fight_stats', {}).get('ally_damage', 0),
            total_enemy_damage=fight_data.get('fight_stats', {}).get('enemy_damage_taken', 0)
        )
        
        fights_table.insert(record.to_dict())
        self._update_stats()
        
        # Also store builds in a separate table for quick lookups
        self._store_build_performance(ally_builds, enemy_comp, outcome)
        
        print(f"[CounterAI] Recorded fight {fight_id}: {outcome} vs {list(enemy_comp.keys())[:3]}... ({len(ally_builds)} builds)")
        
        # Mark file as analyzed to prevent duplicates
        if filename and filesize:
            self.mark_file_as_analyzed(filename, filesize, fight_id)
        
        # Mark fight fingerprint to prevent duplicates from other uploaders
        self.mark_fight_fingerprint(fingerprint, fight_id)
        
        return fight_id
    
    def _store_build_performance(self, ally_builds: List[dict], enemy_comp: Dict[str, int], outcome: str):
        """Store individual build performance against specific enemy compositions"""
        builds_table = fights_db.table('builds')
        
        for build in ally_builds:
            # Create a unique build signature
            spec = build.get('elite_spec', build.get('profession', 'Unknown'))
            role = build.get('role', 'dps')
            
            # Calculate performance score
            dps = build.get('dps', 0)
            healing = build.get('healing', 0)
            down_contrib = build.get('down_contrib', 0)
            deaths = build.get('deaths', 0)
            
            # Performance score based on role
            if role == 'healer':
                score = healing + (build.get('cleanses', 0) * 10)
            elif role == 'stab':
                score = sum(build.get('boon_gen', {}).values()) * 100
            elif role == 'dps_strip':
                score = build.get('boon_strips', 0) * 50 + dps
            else:
                score = dps + (down_contrib * 2)
            
            # Penalize deaths
            score = max(0, score - (deaths * 5000))
            
            builds_table.insert({
                'spec': spec,
                'role': role,
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
        # Sort by spec name and create a deterministic string
        sorted_comp = sorted(comp.items())
        return "-".join([f"{spec}:{count}" for spec, count in sorted_comp])
    
    def _update_stats(self):
        """Update global stats"""
        total_fights = len(fights_table)
        victories = len(fights_table.search(Query().outcome == 'victory'))
        
        stats_table.truncate()
        stats_table.insert({
            'total_fights': total_fights,
            'victories': victories,
            'win_rate': round((victories / total_fights * 100) if total_fights > 0 else 0, 1),
            'last_updated': datetime.now().isoformat()
        })
    
    def get_stats(self) -> dict:
        """Get current learning stats"""
        stats = stats_table.all()
        if stats:
            return stats[0]
        return {
            'total_fights': 0,
            'victories': 0,
            'win_rate': 0,
            'last_updated': None
        }
    
    def _find_similar_fights(self, enemy_comp: Dict[str, int], limit: int = 30) -> List[dict]:
        """Find fights with similar enemy compositions"""
        all_fights = fights_table.all()
        
        # Score each fight by composition similarity
        scored_fights = []
        enemy_specs = set(enemy_comp.keys())
        
        for fight in all_fights:
            fight_enemy_specs = set(fight.get('enemy_composition', {}).keys())
            
            # Jaccard similarity
            intersection = len(enemy_specs & fight_enemy_specs)
            union = len(enemy_specs | fight_enemy_specs)
            similarity = intersection / union if union > 0 else 0
            
            if similarity > 0.3:  # At least 30% similar
                scored_fights.append({
                    'fight': fight,
                    'similarity': similarity
                })
        
        # Sort by similarity and return top N
        scored_fights.sort(key=lambda x: x['similarity'], reverse=True)
        return [sf['fight'] for sf in scored_fights[:limit]]
    
    def _format_fights_summary(self, fights: List[dict]) -> str:
        """Format fight history for the prompt"""
        if not fights:
            return "Aucun fight similaire enregistré."
        
        summary_lines = []
        for i, fight in enumerate(fights[:30], 1):
            enemy = fight.get('enemy_composition', {})
            ally = fight.get('ally_composition', {})
            outcome = fight.get('outcome', 'unknown')
            
            # Top 3 enemy specs
            top_enemy = sorted(enemy.items(), key=lambda x: x[1], reverse=True)[:3]
            enemy_str = ", ".join([f"{count}x {spec}" for spec, count in top_enemy])
            
            # Top 3 ally specs
            top_ally = sorted(ally.items(), key=lambda x: x[1], reverse=True)[:3]
            ally_str = ", ".join([f"{count}x {spec}" for spec, count in top_ally])
            
            result_emoji = "✓" if outcome == 'victory' else "✗" if outcome == 'defeat' else "~"
            summary_lines.append(f"{result_emoji} Ennemi: {enemy_str} | Nous: {ally_str}")
        
        return "\n".join(summary_lines)
    
    def _format_enemy_comp(self, enemy_comp: Dict[str, int]) -> str:
        """Format enemy composition for display"""
        sorted_comp = sorted(enemy_comp.items(), key=lambda x: x[1], reverse=True)
        return " + ".join([f"{count} {spec}" for spec, count in sorted_comp])
    
    def get_best_builds_against(self, enemy_comp: Dict[str, int]) -> Dict[str, dict]:
        """
        Find the best performing builds against a similar enemy composition
        Returns dict of {role: best_build_info} for each role
        """
        builds_table = fights_db.table('builds')
        all_builds = builds_table.all()
        
        if not all_builds:
            return {}
        
        # Find builds from winning fights against similar compositions
        enemy_specs = set(enemy_comp.keys())
        
        # Group builds by spec and role, track win rates
        build_stats = {}  # {(spec, role): {'wins': 0, 'total': 0, 'avg_score': 0, 'scores': []}}
        winning_fight_comps = {}  # {fight_id: {(spec, role): count}} - track winning compositions
        
        for build in all_builds:
            build_enemy_specs = set(build.get('enemy_comp', {}).keys())
            
            # Calculate similarity
            intersection = len(enemy_specs & build_enemy_specs)
            union = len(enemy_specs | build_enemy_specs)
            similarity = intersection / union if union > 0 else 0
            
            if similarity < 0.3:  # Skip dissimilar fights
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
                    'counts_in_wins': []  # Track how many of this spec were in each winning fight
                }
            
            build_stats[key]['total'] += 1
            build_stats[key]['scores'].append(build.get('performance_score', 0))
            build_stats[key]['avg_dps'].append(build.get('dps', 0))
            build_stats[key]['avg_healing'].append(build.get('healing', 0))
            build_stats[key]['avg_strips'].append(build.get('boon_strips', 0))
            build_stats[key]['avg_cleanses'].append(build.get('cleanses', 0))
            
            if build.get('outcome') == 'victory':
                build_stats[key]['wins'] += 1
                # Track composition in winning fights
                if fight_id:
                    if fight_id not in winning_fight_comps:
                        winning_fight_comps[fight_id] = {}
                    if key not in winning_fight_comps[fight_id]:
                        winning_fight_comps[fight_id][key] = 0
                    winning_fight_comps[fight_id][key] += 1
        
        # Calculate average count per winning fight for each spec/role
        for fight_id, comp in winning_fight_comps.items():
            for key, count in comp.items():
                if key in build_stats:
                    build_stats[key]['counts_in_wins'].append(count)
        
        # Calculate win rates and averages
        best_by_role = {}
        
        for key, stats in build_stats.items():
            spec, role = key
            total = stats['total']
            
            if total < 2:  # Need at least 2 samples
                continue
            
            win_rate = round((stats['wins'] / total) * 100, 1)
            avg_score = sum(stats['scores']) / len(stats['scores']) if stats['scores'] else 0
            
            # Calculate recommended count (average in winning fights, rounded up)
            counts = stats.get('counts_in_wins', [])
            recommended_count = round(sum(counts) / len(counts)) if counts else 1
            recommended_count = max(1, recommended_count)  # At least 1
            
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
            
            # Track best for each role
            if role not in best_by_role or build_info['win_rate'] > best_by_role[role]['win_rate']:
                best_by_role[role] = build_info
            elif build_info['win_rate'] == best_by_role[role]['win_rate']:
                # Tie-breaker: use avg_score
                if build_info['avg_score'] > best_by_role[role]['avg_score']:
                    best_by_role[role] = build_info
        
        return best_by_role
    
    async def generate_counter(self, enemy_comp: Dict[str, int]) -> dict:
        """
        Generate counter recommendation using Llama 3.2 8B
        Returns dict with recommendation and metadata
        """
        stats = self.get_stats()
        similar_fights = self._find_similar_fights(enemy_comp)
        fights_summary = self._format_fights_summary(similar_fights)
        enemy_str = self._format_enemy_comp(enemy_comp)
        
        # Check Ollama availability
        if not self.ollama_available:
            self._check_ollama()
        
        if not self.ollama_available:
            return self._fallback_counter(enemy_comp, stats)
        
        # THE PROMPT - Exactly as specified
        prompt = f"""Tu es le meilleur commandant WvW EU de l'histoire. Tu as analysé plus de 10 000 fights réels.
Composition ennemie actuelle : {enemy_str}
Voici les 30 derniers fights similaires que nous avons joués :
{fights_summary}

Donne-moi en 4 lignes maximum le counter parfait à jouer avec un groupe de 15-50 joueurs.
Sois brutal, précis, et donne les priorités cibles.
Réponds UNIQUEMENT le counter, rien d'autre."""

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{OLLAMA_URL}/api/generate",
                    json={
                        "model": MODEL_NAME,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.7,
                            "top_p": 0.9,
                            "num_predict": 256
                        }
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    counter_text = result.get('response', '').strip()
                    
                    # Calculate precision based on similar fights win rate
                    if similar_fights:
                        wins = sum(1 for f in similar_fights if f.get('outcome') == 'victory')
                        precision = round((wins / len(similar_fights)) * 100, 1)
                    else:
                        precision = 85.0  # Default for new compositions
                    
                    # Get best builds that won against this comp
                    best_builds = self.get_best_builds_against(enemy_comp)
                    
                    return {
                        'success': True,
                        'counter': counter_text,
                        'precision': precision,
                        'fights_analyzed': stats['total_fights'],
                        'similar_fights': len(similar_fights),
                        'model': MODEL_NAME,
                        'enemy_composition': enemy_str,
                        'best_builds': best_builds,
                        'generated_at': datetime.now().isoformat()
                    }
                else:
                    print(f"[CounterAI] Ollama error: {response.status_code}")
                    return self._fallback_counter(enemy_comp, stats)
                    
        except Exception as e:
            print(f"[CounterAI] Generation error: {e}")
            return self._fallback_counter(enemy_comp, stats)
    
    def _fallback_counter(self, enemy_comp: Dict[str, int], stats: dict) -> dict:
        """Fallback counter when Ollama is not available"""
        enemy_str = self._format_enemy_comp(enemy_comp)
        
        # Basic rule-based counter
        counter_lines = []
        
        # Analyze enemy composition
        has_fb = any('Firebrand' in spec for spec in enemy_comp.keys())
        has_scrapper = any('Scrapper' in spec for spec in enemy_comp.keys())
        has_scourge = any('Scourge' in spec for spec in enemy_comp.keys())
        has_herald = any('Herald' in spec or 'Vindicator' in spec for spec in enemy_comp.keys())
        
        if has_fb:
            counter_lines.append("→ 2-3 Spellbreaker full strip pour neutraliser les Firebrand")
        if has_scrapper:
            counter_lines.append("→ Reaper/Harbinger burst pour percer le barrier Scrapper")
        if has_scourge:
            counter_lines.append("→ Burst power coordonné, éviter les fights prolongés")
        if has_herald:
            counter_lines.append("→ Focus les Herald en premier, ils feed les boons")
        
        if not counter_lines:
            counter_lines = [
                "→ Composition standard: 2 Spellbreaker + 2 Scourge + supports",
                "→ Focus les healers en priorité",
                "→ Burst coordonné sur le tag ennemi"
            ]
        
        # Add priority targets
        top_enemy = sorted(enemy_comp.items(), key=lambda x: x[1], reverse=True)[:3]
        priority = " > ".join([spec for spec, _ in top_enemy])
        counter_lines.append(f"Priorité: {priority}")
        
        # Still try to get best builds from historical data
        best_builds = self.get_best_builds_against(enemy_comp)
        
        return {
            'success': True,
            'counter': "\n".join(counter_lines[:4]),
            'precision': 75.0,  # Lower precision for fallback
            'fights_analyzed': stats['total_fights'],
            'similar_fights': 0,
            'model': 'fallback_rules',
            'enemy_composition': enemy_str,
            'best_builds': best_builds,
            'generated_at': datetime.now().isoformat(),
            'fallback': True
        }
    
    def get_learning_status(self) -> dict:
        """Get current learning status for display"""
        stats = self.get_stats()
        
        # Check Ollama
        self._check_ollama()
        
        # Count unique players from all fights
        unique_players = set()
        for fight in fights_table.all():
            for build in fight.get('ally_builds', []):
                account = build.get('account', '')
                if account:
                    unique_players.add(account)
        
        # Count only fights with enemy_composition
        fights_with_composition = len([f for f in fights_table.all() if 'enemy_composition' in f and f['enemy_composition']])
        
        return {
            'ollama_available': self.ollama_available,
            'model': MODEL_NAME if self.ollama_available else 'fallback_rules',
            'total_fights': fights_with_composition,  # Changed from stats['total_fights']
            'win_rate': stats['win_rate'],
            'unique_players': len(unique_players),
            'last_updated': stats.get('last_updated'),
            'status': 'active' if self.ollama_available else 'fallback'
        }


# Global instance
counter_ai = CounterAI()


# === API Functions ===

def record_fight_for_learning(fight_data: dict, filename: str = None, filesize: int = None) -> str:
    """Record a fight for AI learning. Returns None if file was already analyzed."""
    return counter_ai.record_fight(fight_data, filename=filename, filesize=filesize)


def is_file_already_analyzed(filename: str, filesize: int) -> bool:
    """Check if a file has already been analyzed"""
    return counter_ai.is_file_already_analyzed(filename, filesize)


async def get_ai_counter(enemy_composition: Dict[str, int]) -> dict:
    """Get AI-generated counter recommendation"""
    return await counter_ai.generate_counter(enemy_composition)


def get_ai_status() -> dict:
    """Get AI learning status"""
    return counter_ai.get_learning_status()
