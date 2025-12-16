"""
Performance Statistics Service
Calculates and stores global performance metrics for player comparison using Gaussian distribution.

Metrics tracked per role:
- DPS: damage_per_sec, down_contrib_per_sec
- Strip: strips_per_sec, cc_per_sec
- Boon: quickness_gen, resistance_gen, aegis_gen, superspeed_gen, stability_gen, protection_gen, 
        vigor_gen, might_gen, fury_gen, regeneration_gen, resolution_gen, swiftness_gen, alacrity_gen
- Stab: aegis_gen, stability_gen
- Heal: regeneration_gen, healing_per_sec, barrier_per_sec, cleanses_per_sec, resurrects_per_sec
"""

import math
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any
from pathlib import Path
from tinydb import TinyDB, Query
from datetime import datetime
from logger import get_logger

logger = get_logger('performance_stats')

# Database for performance stats
db_path = Path(__file__).parent.parent / "data" / "performance_stats.json"
db_path.parent.mkdir(parents=True, exist_ok=True)
performance_db = TinyDB(str(db_path))

# Tables
global_stats_table = performance_db.table('global_stats')
raw_samples_table = performance_db.table('raw_samples')


# Define metrics per role category
ROLE_METRICS = {
    'dps': {
        'damage_per_sec': 'Damage/s',
        'down_contrib_per_sec': 'Down Contrib/s'
    },
    'strip': {
        'strips_per_sec': 'Strips/s',
        'cc_per_sec': 'CC/s'
    },
    'boon': {
        'quickness_gen': 'Quickness',
        'resistance_gen': 'Resistance',
        'aegis_gen': 'Aegis',
        'superspeed_gen': 'Superspeed',
        'stability_gen': 'Stability',
        'protection_gen': 'Protection',
        'vigor_gen': 'Vigor',
        'might_gen': 'Might',
        'fury_gen': 'Fury',
        'regeneration_gen': 'Regeneration',
        'resolution_gen': 'Resolution',
        'swiftness_gen': 'Swiftness',
        'alacrity_gen': 'Alacrity'
    },
    'stab': {
        'aegis_gen': 'Aegis',
        'stability_gen': 'Stability'
    },
    'heal': {
        'regeneration_gen': 'Regeneration',
        'healing_per_sec': 'Healing/s',
        'barrier_per_sec': 'Barrier/s',
        'cleanses_per_sec': 'Cleanses/s',
        'resurrects_per_sec': 'Resurrects/s'
    }
}


@dataclass
class MetricStats:
    """Statistics for a single metric"""
    metric_name: str
    sample_count: int
    mean: float
    std_dev: float
    min_val: float
    max_val: float
    # Gaussian distribution boundaries
    minus_2_std: float  # mean - 2*std
    minus_1_std: float  # mean - 1*std
    plus_1_std: float   # mean + 1*std
    plus_2_std: float   # mean + 2*std
    last_updated: str
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    def get_percentile(self, value: float) -> float:
        """Calculate percentile for a value using normal distribution CDF"""
        if self.std_dev == 0:
            return 50.0 if value >= self.mean else 0.0
        z_score = (value - self.mean) / self.std_dev
        # Approximate CDF using error function
        percentile = 0.5 * (1 + math.erf(z_score / math.sqrt(2)))
        return round(percentile * 100, 1)
    
    def get_rating(self, value: float) -> str:
        """Get a rating label based on standard deviations"""
        if self.std_dev == 0:
            return "Average"
        z_score = (value - self.mean) / self.std_dev
        if z_score >= 2:
            return "Exceptional"
        elif z_score >= 1:
            return "Above Average"
        elif z_score >= -1:
            return "Average"
        elif z_score >= -2:
            return "Below Average"
        else:
            return "Needs Improvement"


def extract_player_metrics(player_data: Dict, duration_sec: int) -> Dict[str, float]:
    """Extract all relevant metrics from player data"""
    if duration_sec <= 0:
        duration_sec = 1
    
    metrics = {
        # DPS metrics
        'damage_per_sec': player_data.get('dps', 0),
        'down_contrib_per_sec': player_data.get('down_contrib_per_sec', 0),
        
        # Strip metrics
        'strips_per_sec': player_data.get('strips_per_sec', 0),
        'cc_per_sec': player_data.get('cc_per_sec', 0),
        
        # Heal metrics
        'healing_per_sec': player_data.get('healing_per_sec', 0),
        'barrier_per_sec': player_data.get('barrier', 0) / duration_sec if duration_sec > 0 else 0,
        'cleanses_per_sec': player_data.get('cleanses_per_sec', 0),
        'resurrects_per_sec': player_data.get('resurrects', 0) / duration_sec if duration_sec > 0 else 0,
    }
    
    # Boon generation metrics
    boon_gen = player_data.get('boon_gen', {})
    metrics['quickness_gen'] = boon_gen.get('quickness', 0)
    metrics['resistance_gen'] = boon_gen.get('resistance', 0)
    metrics['aegis_gen'] = boon_gen.get('aegis', 0)
    metrics['superspeed_gen'] = boon_gen.get('superspeed', 0)
    metrics['stability_gen'] = boon_gen.get('stability', 0)
    metrics['protection_gen'] = boon_gen.get('protection', 0)
    metrics['vigor_gen'] = boon_gen.get('vigor', 0)
    metrics['might_gen'] = boon_gen.get('might', 0)
    metrics['fury_gen'] = boon_gen.get('fury', 0)
    metrics['regeneration_gen'] = boon_gen.get('regeneration', 0)
    metrics['resolution_gen'] = boon_gen.get('resolution', 0)
    metrics['swiftness_gen'] = boon_gen.get('swiftness', 0)
    metrics['alacrity_gen'] = boon_gen.get('alacrity', 0)
    
    return metrics


def record_player_performance(player_data: Dict, duration_sec: int) -> bool:
    """Record a player's performance metrics for global statistics"""
    try:
        metrics = extract_player_metrics(player_data, duration_sec)
        
        # Store raw sample
        sample = {
            'timestamp': datetime.now().isoformat(),
            'account': player_data.get('account', ''),
            'profession': player_data.get('profession', ''),
            'role': player_data.get('role', 'dps'),
            'duration_sec': duration_sec,
            'metrics': metrics
        }
        raw_samples_table.insert(sample)
        
        # Update global statistics
        _update_global_stats(metrics)
        
        return True
    except Exception as e:
        logger.error(f"Failed to record player performance: {e}")
        return False


def _update_global_stats(new_metrics: Dict[str, float]):
    """Update global statistics with new sample using incremental algorithm"""
    try:
        Stats = Query()
        
        for metric_name, value in new_metrics.items():
            if value == 0:  # Skip zero values to avoid skewing stats
                continue
                
            existing = global_stats_table.search(Stats.metric_name == metric_name)
            
            if existing:
                stats = existing[0]
                n = stats['sample_count']
                old_mean = stats['mean']
                old_m2 = stats.get('m2', 0)  # Sum of squared differences
                
                # Welford's online algorithm for variance
                n += 1
                delta = value - old_mean
                new_mean = old_mean + delta / n
                delta2 = value - new_mean
                new_m2 = old_m2 + delta * delta2
                
                if n > 1:
                    new_variance = new_m2 / (n - 1)
                    new_std = math.sqrt(new_variance)
                else:
                    new_std = 0
                
                # Update min/max
                new_min = min(stats['min_val'], value)
                new_max = max(stats['max_val'], value)
                
                global_stats_table.update({
                    'sample_count': n,
                    'mean': new_mean,
                    'std_dev': new_std,
                    'm2': new_m2,
                    'min_val': new_min,
                    'max_val': new_max,
                    'minus_2_std': new_mean - 2 * new_std,
                    'minus_1_std': new_mean - new_std,
                    'plus_1_std': new_mean + new_std,
                    'plus_2_std': new_mean + 2 * new_std,
                    'last_updated': datetime.now().isoformat()
                }, Stats.metric_name == metric_name)
            else:
                # First sample for this metric
                global_stats_table.insert({
                    'metric_name': metric_name,
                    'sample_count': 1,
                    'mean': value,
                    'std_dev': 0,
                    'm2': 0,
                    'min_val': value,
                    'max_val': value,
                    'minus_2_std': value,
                    'minus_1_std': value,
                    'plus_1_std': value,
                    'plus_2_std': value,
                    'last_updated': datetime.now().isoformat()
                })
                
    except Exception as e:
        logger.error(f"Failed to update global stats: {e}")


def get_global_stats() -> Dict[str, MetricStats]:
    """Get all global statistics"""
    try:
        all_stats = global_stats_table.all()
        result = {}
        
        for stat in all_stats:
            result[stat['metric_name']] = MetricStats(
                metric_name=stat['metric_name'],
                sample_count=stat['sample_count'],
                mean=stat['mean'],
                std_dev=stat['std_dev'],
                min_val=stat['min_val'],
                max_val=stat['max_val'],
                minus_2_std=stat['minus_2_std'],
                minus_1_std=stat['minus_1_std'],
                plus_1_std=stat['plus_1_std'],
                plus_2_std=stat['plus_2_std'],
                last_updated=stat['last_updated']
            )
        
        return result
    except Exception as e:
        logger.error(f"Failed to get global stats: {e}")
        return {}


def get_player_comparison(player_metrics: Dict[str, float], role: str = None) -> Dict[str, Dict]:
    """
    Compare a player's metrics against global statistics.
    Returns comparison data for each relevant metric.
    """
    try:
        global_stats = get_global_stats()
        comparison = {}
        
        # Determine which metrics to compare based on role
        if role:
            role_lower = role.lower()
            if role_lower in ['dps', 'dps_strip']:
                relevant_metrics = list(ROLE_METRICS['dps'].keys()) + list(ROLE_METRICS['strip'].keys())
            elif role_lower in ['healer', 'heal']:
                relevant_metrics = list(ROLE_METRICS['heal'].keys())
            elif role_lower in ['stab']:
                relevant_metrics = list(ROLE_METRICS['stab'].keys())
            elif role_lower in ['boon']:
                relevant_metrics = list(ROLE_METRICS['boon'].keys())
            else:
                relevant_metrics = list(player_metrics.keys())
        else:
            relevant_metrics = list(player_metrics.keys())
        
        for metric_name in relevant_metrics:
            if metric_name not in player_metrics:
                continue
                
            player_value = player_metrics[metric_name]
            
            if metric_name in global_stats:
                stats = global_stats[metric_name]
                comparison[metric_name] = {
                    'player_value': player_value,
                    'mean': stats.mean,
                    'std_dev': stats.std_dev,
                    'percentile': stats.get_percentile(player_value),
                    'rating': stats.get_rating(player_value),
                    'sample_count': stats.sample_count,
                    'boundaries': {
                        'minus_2_std': stats.minus_2_std,
                        'minus_1_std': stats.minus_1_std,
                        'plus_1_std': stats.plus_1_std,
                        'plus_2_std': stats.plus_2_std
                    }
                }
            else:
                # No global data yet
                comparison[metric_name] = {
                    'player_value': player_value,
                    'mean': None,
                    'std_dev': None,
                    'percentile': None,
                    'rating': 'No Data',
                    'sample_count': 0,
                    'boundaries': None
                }
        
        return comparison
    except Exception as e:
        logger.error(f"Failed to get player comparison: {e}")
        return {}


def get_role_comparison_summary(player_metrics: Dict[str, float]) -> Dict[str, Dict]:
    """
    Get a summary comparison for each role category (DPS, Strip, Boon, Stab, Heal).
    Returns average percentile and rating for each category.
    """
    try:
        global_stats = get_global_stats()
        summary = {}
        
        for role_name, metrics in ROLE_METRICS.items():
            percentiles = []
            metric_details = []
            
            for metric_key, metric_label in metrics.items():
                if metric_key not in player_metrics:
                    continue
                    
                player_value = player_metrics[metric_key]
                
                if metric_key in global_stats and player_value > 0:
                    stats = global_stats[metric_key]
                    percentile = stats.get_percentile(player_value)
                    percentiles.append(percentile)
                    metric_details.append({
                        'name': metric_label,
                        'key': metric_key,
                        'value': player_value,
                        'percentile': percentile,
                        'rating': stats.get_rating(player_value),
                        'mean': stats.mean,
                        'std_dev': stats.std_dev
                    })
            
            if percentiles:
                avg_percentile = sum(percentiles) / len(percentiles)
                if avg_percentile >= 84:  # +1 std
                    rating = "Exceptional" if avg_percentile >= 97.5 else "Above Average"
                elif avg_percentile >= 16:  # -1 std
                    rating = "Average"
                else:
                    rating = "Below Average" if avg_percentile >= 2.5 else "Needs Improvement"
                
                summary[role_name] = {
                    'avg_percentile': round(avg_percentile, 1),
                    'rating': rating,
                    'metrics': metric_details
                }
            else:
                summary[role_name] = {
                    'avg_percentile': None,
                    'rating': 'No Data',
                    'metrics': []
                }
        
        return summary
    except Exception as e:
        logger.error(f"Failed to get role comparison summary: {e}")
        return {}


def get_stats_summary() -> Dict[str, Any]:
    """Get a summary of the performance statistics database"""
    try:
        total_samples = len(raw_samples_table.all())
        global_stats = global_stats_table.all()
        
        return {
            'total_samples': total_samples,
            'metrics_tracked': len(global_stats),
            'last_updated': max((s.get('last_updated', '') for s in global_stats), default='Never')
        }
    except Exception as e:
        logger.error(f"Failed to get stats summary: {e}")
        return {'total_samples': 0, 'metrics_tracked': 0, 'last_updated': 'Error'}


def calculate_player_performance_score(player_metrics: Dict[str, float], role: str = None) -> float:
    """
    Calculate a composite performance score for a player based on their metrics.
    Score is normalized to 0-100 scale.
    """
    global_stats = get_global_stats()
    
    # Weight metrics by role
    if role in ['dps', 'dps_strip']:
        weights = {'damage_per_sec': 0.6, 'down_contrib_per_sec': 0.3, 'strips_per_sec': 0.1}
    elif role in ['healer', 'heal']:
        weights = {'healing_per_sec': 0.4, 'cleanses_per_sec': 0.3, 'barrier_per_sec': 0.2, 'regeneration_gen': 0.1}
    elif role == 'stab':
        weights = {'stability_gen': 0.5, 'aegis_gen': 0.3, 'protection_gen': 0.2}
    elif role == 'boon':
        weights = {'quickness_gen': 0.3, 'resistance_gen': 0.2, 'aegis_gen': 0.2, 'stability_gen': 0.15, 'superspeed_gen': 0.15}
    else:
        weights = {'damage_per_sec': 0.5, 'down_contrib_per_sec': 0.3, 'strips_per_sec': 0.2}
    
    total_score = 0
    total_weight = 0
    
    for metric, weight in weights.items():
        if metric in player_metrics and metric in global_stats:
            stats = global_stats[metric]
            percentile = stats.get_percentile(player_metrics[metric])
            total_score += percentile * weight
            total_weight += weight
    
    return total_score / total_weight if total_weight > 0 else 50.0


def find_best_group_compositions(player_performances: List[Dict], group_size: int = 5) -> List[Dict]:
    """
    Find the best group compositions based on individual performance metrics.
    
    Args:
        player_performances: List of dicts with 'account', 'role', 'metrics', 'score'
        group_size: Number of players per group (default 5)
    
    Returns:
        List of best group compositions with their combined scores
    """
    from itertools import combinations
    
    if len(player_performances) < group_size:
        return []
    
    # Calculate ideal role distribution for a group
    ideal_roles = {
        'dps': 2,
        'dps_strip': 1,
        'stab': 1,
        'healer': 1
    }
    
    best_groups = []
    
    # Generate all possible combinations
    all_combos = list(combinations(range(len(player_performances)), group_size))
    
    # Limit to avoid performance issues
    if len(all_combos) > 1000:
        import random
        all_combos = random.sample(all_combos, 1000)
    
    for combo in all_combos:
        group = [player_performances[i] for i in combo]
        
        # Calculate role coverage score
        role_counts = {}
        for p in group:
            role = p.get('role', 'dps')
            role_counts[role] = role_counts.get(role, 0) + 1
        
        role_score = 0
        for role, ideal in ideal_roles.items():
            actual = role_counts.get(role, 0)
            role_score += min(actual, ideal) / ideal * 25  # Max 25 per role = 100 total
        
        # Calculate combined performance score
        perf_score = sum(p.get('score', 50) for p in group) / group_size
        
        # Combined score: 60% performance, 40% role balance
        combined_score = perf_score * 0.6 + role_score * 0.4
        
        best_groups.append({
            'players': [p.get('account', 'Unknown') for p in group],
            'roles': [p.get('role', 'dps') for p in group],
            'performance_score': round(perf_score, 1),
            'role_balance_score': round(role_score, 1),
            'combined_score': round(combined_score, 1)
        })
    
    # Sort by combined score and return top 5
    best_groups.sort(key=lambda x: x['combined_score'], reverse=True)
    return best_groups[:5]


def get_guild_group_comparison(guild_fights: List[Dict], guild_members: List[str] = None) -> Dict[str, Any]:
    """
    Analyze guild fights to find the best performing group compositions.
    
    Args:
        guild_fights: List of fight records with participants
        guild_members: Optional list of guild member account names to filter by
    
    Returns:
        Dict with best groups and performance analysis
    """
    try:
        # Aggregate player performance across all fights
        player_stats = {}
        
        for fight in guild_fights:
            for participant in fight.get('participants', []):
                account = participant.get('account_name', '')
                if not account:
                    continue
                
                # Filter by guild members if provided
                if guild_members and account not in guild_members:
                    continue
                
                if account not in player_stats:
                    player_stats[account] = {
                        'account': account,
                        'fights': 0,
                        'roles': {},
                        'metrics': {
                            'damage_per_sec': [],
                            'strips_per_sec': [],
                            'healing_per_sec': [],
                            'stability_gen': [],
                            'quickness_gen': []
                        }
                    }
                
                player_stats[account]['fights'] += 1
                role = participant.get('role', 'dps')
                player_stats[account]['roles'][role] = player_stats[account]['roles'].get(role, 0) + 1
        
        # Calculate average metrics and determine primary role
        player_performances = []
        for account, stats in player_stats.items():
            if stats['fights'] < 3:  # Minimum 3 fights to be considered
                continue
            
            # Determine primary role
            primary_role = max(stats['roles'].items(), key=lambda x: x[1])[0] if stats['roles'] else 'dps'
            
            # Calculate performance score (simplified without actual metrics)
            # In a real implementation, we'd use actual fight metrics
            score = 50 + (stats['fights'] * 0.5)  # Base score + participation bonus
            score = min(score, 95)  # Cap at 95
            
            player_performances.append({
                'account': account,
                'role': primary_role,
                'fights': stats['fights'],
                'score': score
            })
        
        # Find best group compositions
        best_groups = find_best_group_compositions(player_performances)
        
        return {
            'total_players': len(player_performances),
            'best_groups': best_groups,
            'player_performances': sorted(player_performances, key=lambda x: x['score'], reverse=True)[:10]
        }
    
    except Exception as e:
        logger.error(f"Failed to get guild group comparison: {e}")
        return {'total_players': 0, 'best_groups': [], 'player_performances': []}
