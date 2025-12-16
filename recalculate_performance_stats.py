#!/usr/bin/env python3
"""
Script to recalculate performance statistics from existing fight data.
This will populate the performance_stats.json database with global metrics.
FAST VERSION - processes in batches without individual DB writes.
"""

import sys
import math
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from tinydb import TinyDB

# Direct DB access for speed (bypass services)
PERF_DB_PATH = Path(__file__).parent / "data" / "performance_stats.json"
FIGHTS_DB_PATH = Path(__file__).parent / "data" / "fights.db"


def calculate_stats_fast(max_fights=300):
    """Fast calculation of performance stats using direct DB access"""
    
    print("Loading fights database...")
    fights_db = TinyDB(str(FIGHTS_DB_PATH))
    fights_table = fights_db.table('fights')
    
    all_fights = fights_table.all()
    print(f"Found {len(all_fights)} fights total")
    
    # Sort by timestamp and limit
    all_fights.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    fights_to_process = all_fights[:max_fights]
    
    print(f"Processing {len(fights_to_process)} most recent fights...")
    
    # Collect all metrics in memory first
    metrics_data = {}  # {metric_name: [values]}
    
    processed = 0
    for i, fight in enumerate(fights_to_process):
        if i % 50 == 0:
            print(f"  Progress: {i}/{len(fights_to_process)} fights...")
        
        duration_sec = fight.get('duration_sec', 0)
        if duration_sec < 30:
            continue
        
        for build in fight.get('ally_builds', []):
            # Extract metrics
            dps = build.get('dps', 0)
            if dps > 0:
                metrics_data.setdefault('damage_per_sec', []).append(dps)
            
            down_contrib = build.get('down_contrib', 0) / duration_sec if duration_sec > 0 else 0
            if down_contrib > 0:
                metrics_data.setdefault('down_contrib_per_sec', []).append(down_contrib)
            
            strips = build.get('boon_strips', 0) / duration_sec if duration_sec > 0 else 0
            if strips > 0:
                metrics_data.setdefault('strips_per_sec', []).append(strips)
            
            healing = build.get('healing', 0) / duration_sec if duration_sec > 0 else 0
            if healing > 0:
                metrics_data.setdefault('healing_per_sec', []).append(healing)
            
            cleanses = build.get('cleanses', 0) / duration_sec if duration_sec > 0 else 0
            if cleanses > 0:
                metrics_data.setdefault('cleanses_per_sec', []).append(cleanses)
            
            # Boon generation
            boon_gen = build.get('boon_gen', {})
            for boon, value in boon_gen.items():
                if value > 0:
                    metrics_data.setdefault(f'{boon}_gen', []).append(value)
            
            processed += 1
    
    print(f"\nCalculating statistics for {len(metrics_data)} metrics...")
    
    # Calculate stats for each metric
    global_stats = {}
    for metric_name, values in metrics_data.items():
        if not values:
            continue
        
        n = len(values)
        mean = sum(values) / n
        
        # Calculate std dev
        if n > 1:
            variance = sum((x - mean) ** 2 for x in values) / (n - 1)
            std_dev = math.sqrt(variance)
        else:
            std_dev = 0
        
        global_stats[metric_name] = {
            'metric_name': metric_name,
            'sample_count': n,
            'mean': mean,
            'std_dev': std_dev,
            'min_val': min(values),
            'max_val': max(values),
            'minus_2_std': mean - 2 * std_dev,
            'minus_1_std': mean - std_dev,
            'plus_1_std': mean + std_dev,
            'plus_2_std': mean + 2 * std_dev,
            'm2': 0,  # Not needed for batch calculation
            'last_updated': datetime.now().isoformat()
        }
    
    # Write to performance DB
    print("Writing to performance database...")
    perf_db = TinyDB(str(PERF_DB_PATH))
    
    # Clear and rewrite global_stats table
    global_stats_table = perf_db.table('global_stats')
    global_stats_table.truncate()
    for stat in global_stats.values():
        global_stats_table.insert(stat)
    
    # Write sample count to raw_samples (just a count, not all samples)
    raw_samples_table = perf_db.table('raw_samples')
    raw_samples_table.truncate()
    raw_samples_table.insert({
        'total_processed': processed,
        'last_updated': datetime.now().isoformat()
    })
    
    perf_db.close()
    fights_db.close()
    
    return processed, len(global_stats)


def main():
    print("=" * 60)
    print("FAST Performance Statistics Recalculation")
    print("=" * 60)
    
    processed, metrics_count = calculate_stats_fast(max_fights=300)
    
    print(f"\n✅ Done!")
    print(f"  - Processed: {processed} player performances")
    print(f"  - Metrics calculated: {metrics_count}")


if __name__ == "__main__":
    main()
