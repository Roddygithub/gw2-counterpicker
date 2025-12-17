#!/usr/bin/env python3
"""
GW2 Counter-Picker - Préparation automatique du fine-tuning

Ce script:
1. Vérifie s'il y a assez de nouveaux combats depuis le dernier fine-tuning
2. Régénère les datasets pour Qwen et Mistral
3. Met à jour les données API GW2 si nécessaire
4. Commit et push sur GitHub (accessible depuis Colab)

Usage:
    python scripts/prepare_finetune_update.py [--force]
    
Options:
    --force     Force la régénération même si pas assez de nouveaux combats

Automatisation (cron):
    # Vérifier chaque semaine si un nouveau fine-tuning est nécessaire
    0 3 * * 0 cd /path/to/gw2-counterpicker && python scripts/prepare_finetune_update.py
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Configuration
MIN_NEW_FIGHTS = 200  # Minimum de nouveaux combats pour déclencher un fine-tuning
DATA_DIR = Path("data")
FINETUNE_STATE_FILE = DATA_DIR / "finetune_state.json"


def load_finetune_state() -> dict:
    """Charger l'état du dernier fine-tuning"""
    if FINETUNE_STATE_FILE.exists():
        with open(FINETUNE_STATE_FILE, 'r') as f:
            return json.load(f)
    return {
        "last_finetune_date": None,
        "last_fight_count": 0,
        "version": 0
    }


def save_finetune_state(state: dict):
    """Sauvegarder l'état du fine-tuning"""
    with open(FINETUNE_STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def get_current_fight_count() -> int:
    """Compter le nombre de combats dans la base"""
    from tinydb import TinyDB
    
    fights_db = DATA_DIR / "fights.db"
    if not fights_db.exists():
        return 0
    
    db = TinyDB(str(fights_db))
    fights_table = db.table('fights')
    return len(fights_table.all())


def run_script(script_path: str, description: str) -> bool:
    """Exécuter un script Python"""
    print(f"\n{'='*60}")
    print(f"📦 {description}")
    print('='*60)
    
    result = subprocess.run(
        [sys.executable, script_path],
        capture_output=False
    )
    
    if result.returncode != 0:
        print(f"❌ Erreur lors de l'exécution de {script_path}")
        return False
    return True


def git_commit_and_push(message: str) -> bool:
    """Commit et push les changements sur GitHub"""
    print(f"\n{'='*60}")
    print("📤 Commit et push sur GitHub")
    print('='*60)
    
    try:
        # Add all changes
        subprocess.run(["git", "add", "-A"], check=True)
        
        # Check if there are changes to commit
        result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            capture_output=True
        )
        
        if result.returncode == 0:
            print("ℹ️  Pas de changements à commiter")
            return True
        
        # Commit
        subprocess.run(
            ["git", "commit", "-m", message],
            check=True
        )
        
        # Push
        subprocess.run(
            ["git", "push", "origin", "main"],
            check=True
        )
        
        print("✓ Changements pushés sur GitHub")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Erreur Git: {e}")
        return False


def main():
    print("="*60)
    print("🎮 GW2 Counter-Picker - Préparation Fine-tuning")
    print("="*60)
    
    force = "--force" in sys.argv
    
    # Charger l'état précédent
    state = load_finetune_state()
    current_fights = get_current_fight_count()
    new_fights = current_fights - state["last_fight_count"]
    
    print(f"\n📊 Statistiques:")
    print(f"   - Combats actuels: {current_fights}")
    print(f"   - Combats au dernier fine-tuning: {state['last_fight_count']}")
    print(f"   - Nouveaux combats: {new_fights}")
    print(f"   - Seuil minimum: {MIN_NEW_FIGHTS}")
    
    if state["last_finetune_date"]:
        print(f"   - Dernier fine-tuning: {state['last_finetune_date']}")
    
    # Vérifier si on doit faire un fine-tuning
    if not force and new_fights < MIN_NEW_FIGHTS:
        print(f"\n⏸️  Pas assez de nouveaux combats ({new_fights} < {MIN_NEW_FIGHTS})")
        print("   Utilisez --force pour forcer la régénération")
        return
    
    print(f"\n✓ {new_fights} nouveaux combats détectés - Régénération des datasets...")
    
    # 1. Mettre à jour les données API GW2
    if not run_script("scripts/fetch_gw2_api_data.py", "Mise à jour des données API GW2"):
        print("⚠️  Erreur API GW2, continuation avec les données existantes...")
    
    # 2. Régénérer les datasets
    if not run_script("scripts/generate_finetune_dataset.py", "Génération des datasets"):
        print("❌ Erreur lors de la génération des datasets")
        return
    
    # 3. Mettre à jour l'état
    new_version = state["version"] + 1
    state = {
        "last_finetune_date": datetime.now().isoformat(),
        "last_fight_count": current_fights,
        "version": new_version,
        "new_fights_since_last": new_fights
    }
    save_finetune_state(state)
    
    # 4. Commit et push
    commit_message = f"Update fine-tuning datasets v{new_version} (+{new_fights} fights)"
    if not git_commit_and_push(commit_message):
        print("⚠️  Erreur Git, mais les datasets sont prêts localement")
    
    # 5. Résumé
    print("\n" + "="*60)
    print("✅ PRÉPARATION TERMINÉE")
    print("="*60)
    print(f"""
📋 Prochaines étapes:

1. Ouvrir Google Colab:
   https://colab.research.google.com

2. Uploader le notebook:
   - Pour Qwen (serveur): notebooks/finetune_qwen_gw2.ipynb
   - Pour Mistral (local): notebooks/finetune_mistral_gw2.ipynb

3. Exécuter toutes les cellules (Runtime → Run all)

4. Le dataset sera téléchargé automatiquement depuis GitHub
   ou uploadé manuellement depuis:
   - data/finetune_dataset_qwen.jsonl
   - data/finetune_dataset_mistral.jsonl

📊 Version du dataset: v{new_version}
📈 Combats inclus: {current_fights}
🆕 Nouveaux combats: {new_fights}
""")


if __name__ == "__main__":
    main()
