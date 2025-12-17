#!/usr/bin/env python3
"""
Generate fine-tuning datasets for Qwen2.5:3b and Mistral 7B from historical fight data.

This script creates training examples in the format:
- Input: Enemy composition + context
- Output: CONTER/FOCUS/TACTIQUE format

The dataset can be used with:
- Unsloth (recommended, fastest)
- Axolotl
- Hugging Face Transformers

Requirements:
- Python 3.10+
- tinydb

Usage:
    python scripts/generate_finetune_dataset.py [--model qwen|mistral|both]

Output:
    data/finetune_dataset_qwen.jsonl   (for Qwen2.5:3b)
    data/finetune_dataset_mistral.jsonl (for Mistral 7B)
"""

import json
import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tinydb import TinyDB

# Configuration
FIGHTS_DB_PATH = Path("data/fights.db")
WVW_SPECS_PATH = Path("data/gw2_wvw_specs.json")
OUTPUT_PATH_QWEN = Path("data/finetune_dataset_qwen.jsonl")
OUTPUT_PATH_MISTRAL = Path("data/finetune_dataset_mistral.jsonl")
MIN_EXAMPLES_PER_CONTEXT = 50  # Minimum examples per context type

# Load WvW spec data from API (if available)
WVW_SPEC_DATA = {}
if WVW_SPECS_PATH.exists():
    with open(WVW_SPECS_PATH, 'r', encoding='utf-8') as f:
        WVW_SPEC_DATA = json.load(f)

# Valid GW2 elite specs (including Visions of Eternity)
VALID_SPECS = {
    # Guardian - HoT/PoF/EoD/VoE
    "Dragonhunter", "Firebrand", "Willbender", "Luminary",
    # Warrior - HoT/PoF/EoD/VoE
    "Berserker", "Spellbreaker", "Bladesworn", "Paragon",
    # Engineer - HoT/PoF/EoD/VoE
    "Scrapper", "Holosmith", "Mechanist", "Amalgam",
    # Ranger - HoT/PoF/EoD/VoE
    "Druid", "Soulbeast", "Untamed", "Galeshot",
    # Thief - HoT/PoF/EoD/VoE
    "Daredevil", "Deadeye", "Specter", "Antiquary",
    # Elementalist - HoT/PoF/EoD/VoE
    "Tempest", "Weaver", "Catalyst", "Evoker",
    # Mesmer - HoT/PoF/EoD/VoE
    "Chronomancer", "Mirage", "Virtuoso", "Troubadour",
    # Necromancer - HoT/PoF/EoD/VoE
    "Reaper", "Scourge", "Harbinger", "Ritualist",
    # Revenant - HoT/PoF/EoD/VoE
    "Herald", "Renegade", "Vindicator", "Conduit"
}

# Role priorities for FOCUS targeting
ROLE_PRIORITY = {
    "heal": 1,      # Healers first
    "stab": 2,      # Stability providers
    "boon": 3,      # Boon supports
    "strip": 4,     # Boon strippers
    "dps": 5        # DPS last
}

# Spec to role mapping
SPEC_ROLES = {
    # Core specs
    "Firebrand": "stab", "Druid": "heal", "Tempest": "heal", "Scrapper": "heal",
    "Herald": "boon", "Chronomancer": "boon", "Renegade": "boon",
    "Spellbreaker": "strip", "Reaper": "strip", "Scourge": "strip",
    "Willbender": "dps", "Dragonhunter": "dps", "Berserker": "dps",
    "Bladesworn": "dps", "Vindicator": "dps", "Holosmith": "dps",
    "Mechanist": "dps", "Soulbeast": "dps", "Untamed": "dps",
    "Daredevil": "dps", "Deadeye": "dps", "Specter": "dps",
    "Weaver": "dps", "Catalyst": "dps", "Mirage": "dps",
    "Virtuoso": "dps", "Harbinger": "dps",
    # Visions of Eternity specs
    "Luminary": "heal",      # Guardian - Radiant Forge support
    "Paragon": "stab",       # Warrior - Chants/Commands support
    "Amalgam": "dps",        # Engineer - Morphs DPS
    "Galeshot": "dps",       # Ranger - Cyclone Bow DPS
    "Antiquary": "dps",      # Thief - Skritt Swipe DPS
    "Evoker": "dps",         # Elementalist - Familiars DPS
    "Troubadour": "boon",    # Mesmer - Instruments support
    "Ritualist": "strip",    # Necromancer - Spirits corrupt
    "Conduit": "boon"        # Revenant - Legendary Entity support
}

# Counter recommendations based on meta knowledge
COUNTER_MATRIX = {
    # Core specs
    "Firebrand": ["Spellbreaker", "Scourge"],  # Strip aegis/stab
    "Scrapper": ["Reaper", "Harbinger"],        # Power burst through barrier
    "Scourge": ["Spellbreaker", "Willbender"],  # Fast push, don't let shades stack
    "Herald": ["Spellbreaker", "Scourge"],      # Strip boons
    "Druid": ["Deadeye", "Willbender"],         # Burst healer
    "Tempest": ["Spellbreaker", "Deadeye"],     # Interrupt/burst
    "Virtuoso": ["Willbender", "Daredevil"],    # Gap close before clones
    "Reaper": ["Scrapper", "Firebrand"],        # Sustain through shroud
    "Soulbeast": ["Scrapper", "Firebrand"],     # Sustain
    "Weaver": ["Spellbreaker", "Deadeye"],      # Interrupt/burst
    # Visions of Eternity counters
    "Luminary": ["Spellbreaker", "Ritualist"],  # Strip radiant boons
    "Paragon": ["Scourge", "Ritualist"],        # Corrupt stability/echoes
    "Amalgam": ["Spellbreaker", "Antiquary"],   # Interrupt morphs
    "Galeshot": ["Deadeye", "Antiquary"],       # Burst before squalls
    "Antiquary": ["Scrapper", "Paragon"],       # Sustain through backfire
    "Evoker": ["Spellbreaker", "Antiquary"],    # Interrupt familiars
    "Troubadour": ["Spellbreaker", "Ritualist"], # Strip performance boons
    "Ritualist": ["Willbender", "Antiquary"],   # Burst spirits down
    "Conduit": ["Scrapper", "Paragon"]          # Sustain through resonance
}

# Tactical advice per context
TACTICS = {
    "zerg": [
        "Strip aegis before push, focus healers",
        "Coordinated burst on tag call",
        "Push fast, don't let enemy stack",
        "Bomb on enemy backline",
        "CC chain then burst",
        "Focus stability providers first",
        "Split enemy blob with wells",
    ],
    "guild_raid": [
        "Strip aegis then coordinated burst",
        "Focus call on healers",
        "Burst windows on commander call",
        "Pressure backline constantly",
        "CC chain into spike damage",
        "Rotate cooldowns efficiently",
    ],
    "roam": [
        "Burst healer first, kite if needed",
        "Gap close fast, don't let them kite",
        "Focus squishy targets",
        "Disengage if outnumbered",
        "Reveal thieves before engaging",
        "Don't chase into enemy territory",
    ]
}


def format_enemy_comp(enemy_comp: dict) -> str:
    """Format enemy composition as string"""
    parts = []
    for spec, count in sorted(enemy_comp.items(), key=lambda x: -x[1]):
        if count > 1:
            parts.append(f"{count} {spec}")
        else:
            parts.append(spec)
    return " + ".join(parts)


def get_counter_specs(enemy_comp: dict, context: str) -> list:
    """Generate counter specs based on enemy composition"""
    counters = defaultdict(int)
    
    for spec, count in enemy_comp.items():
        if spec in COUNTER_MATRIX:
            for counter in COUNTER_MATRIX[spec]:
                counters[counter] += count
    
    # Sort by effectiveness
    sorted_counters = sorted(counters.items(), key=lambda x: -x[1])
    
    # Adjust counts based on context
    result = []
    if context == "roam":
        # Small group - 2-3 specs
        for spec, _ in sorted_counters[:2]:
            result.append(f"1x {spec}")
    elif context == "guild_raid":
        # Medium group - 4-6 specs
        for spec, weight in sorted_counters[:4]:
            count = min(2, max(1, weight // 2))
            result.append(f"{count}x {spec}")
    else:  # zerg
        # Large group - 5-8 specs
        for spec, weight in sorted_counters[:5]:
            count = min(3, max(1, weight // 2))
            result.append(f"{count}x {spec}")
    
    # Add default if empty
    if not result:
        if context == "roam":
            result = ["1x Willbender", "1x Deadeye"]
        elif context == "guild_raid":
            result = ["2x Spellbreaker", "2x Scourge", "1x Firebrand"]
        else:
            result = ["3x Spellbreaker", "3x Scourge", "2x Firebrand", "2x Scrapper"]
    
    return result


def get_focus_targets(enemy_comp: dict) -> list:
    """Get priority targets based on enemy composition"""
    targets = []
    for spec in enemy_comp.keys():
        role = SPEC_ROLES.get(spec, "dps")
        priority = ROLE_PRIORITY.get(role, 5)
        targets.append((spec, priority))
    
    # Sort by priority (lower = higher priority)
    sorted_targets = sorted(targets, key=lambda x: x[1])
    return [t[0] for t in sorted_targets[:3]]


def get_spec_context(spec_name: str) -> str:
    """Get WvW context for a spec from API data"""
    if spec_name not in WVW_SPEC_DATA:
        return ""
    
    data = WVW_SPEC_DATA[spec_name]
    roles = ", ".join(data.get("role_tags", []))
    desc = data.get("wvw_description", "")
    countered_by = data.get("counters", {}).get("countered_by", [])
    weak_to = data.get("counters", {}).get("weak_to", [])
    
    context_parts = [f"{spec_name} ({data.get('profession', '')})"]
    if roles:
        context_parts.append(f"Role: {roles}")
    if desc:
        context_parts.append(desc)
    if countered_by:
        context_parts.append(f"Countered by: {', '.join(countered_by)}")
    if weak_to:
        context_parts.append(f"Weak to: {', '.join(weak_to)}")
    
    return " | ".join(context_parts)


def build_enemy_context(enemy_comp: dict) -> str:
    """Build enriched context block for enemy composition"""
    if not WVW_SPEC_DATA:
        return ""
    
    context_lines = []
    for spec in enemy_comp.keys():
        if spec in WVW_SPEC_DATA:
            data = WVW_SPEC_DATA[spec]
            roles = ", ".join(data.get("role_tags", [])[:3])  # Top 3 roles
            weak_to = data.get("counters", {}).get("weak_to", [])[:2]  # Top 2 weaknesses
            
            line = f"- {spec}: {roles}"
            if weak_to:
                line += f" (weak to: {', '.join(weak_to)})"
            context_lines.append(line)
    
    if context_lines:
        return "\n".join(context_lines)
    return ""


def generate_example(enemy_comp: dict, context: str, outcome: str = None, model_format: str = "qwen") -> dict:
    """Generate a single training example for fine-tuning
    
    Args:
        enemy_comp: Enemy composition dict
        context: Fight context (zerg, guild_raid, roam)
        outcome: Fight outcome (victory, defeat)
        model_format: "qwen" for Qwen2.5:3b or "mistral" for Mistral 7B
    """
    import random
    
    valid_specs_str = ", ".join(sorted(VALID_SPECS))
    enemy_str = format_enemy_comp(enemy_comp)
    enemy_context = build_enemy_context(enemy_comp)
    
    context_names = {
        "zerg": "ZERG (25+ players)",
        "guild_raid": "GUILD RAID (10-25 players)",
        "roam": "ROAMING (1-10 players)"
    }
    mode = context_names.get(context, context_names['zerg'])
    
    # Build enriched prompt with API data
    base_content = f"""Guild Wars 2 WvW counter-picker.

VALID SPECS: {valid_specs_str}

Mode: {mode}
Enemy composition: {enemy_str}"""

    # Add enriched context if available
    if enemy_context:
        base_content += f"""

[ENEMY ANALYSIS]
{enemy_context}"""

    base_content += """

Respond EXACTLY in this format:
CONTER: Nx Spec, Nx Spec
FOCUS: Target1 > Target2
TACTIQUE: One tactical advice"""

    # Format prompt based on model
    if model_format == "mistral":
        prompt = f"[INST] {base_content} [/INST]"
    else:
        prompt = base_content

    # Output response - use counter data from API if available
    counter_specs = get_counter_specs(enemy_comp, context)
    focus_targets = get_focus_targets(enemy_comp)
    tactic = get_smart_tactic(enemy_comp, context)
    
    response = f"""CONTER: {", ".join(counter_specs)}
FOCUS: {" > ".join(focus_targets)}
TACTIQUE: {tactic}"""

    return {
        "instruction": prompt,
        "output": response,
        "context": context,
        "enemy_comp": enemy_comp,
        "outcome": outcome
    }


def get_smart_tactic(enemy_comp: dict, context: str) -> str:
    """Generate a smart tactic based on enemy composition and API data"""
    import random
    
    # Analyze enemy composition for specific tactics
    has_stability = any(spec in enemy_comp for spec in ["Firebrand", "Herald"])
    has_boons = any(spec in enemy_comp for spec in ["Firebrand", "Scrapper", "Chronomancer", "Tempest"])
    has_condi = any(spec in enemy_comp for spec in ["Scourge", "Mirage", "Harbinger", "Weaver"])
    has_burst = any(spec in enemy_comp for spec in ["Soulbeast", "Deadeye", "Virtuoso", "Bladesworn"])
    has_support = any(spec in enemy_comp for spec in ["Firebrand", "Scrapper", "Druid", "Tempest", "Mechanist"])
    
    # Context-specific smart tactics
    smart_tactics = []
    
    if has_stability and has_boons:
        smart_tactics.extend([
            "Strip stability with Spellbreaker bubble before CC push",
            "Wait for Tome of Courage cooldown then engage",
            "Focus boon strip on Firebrands first"
        ])
    
    if has_condi:
        smart_tactics.extend([
            "Stack cleanses and resistance before engaging",
            "Burst down Scourges before they stack conditions",
            "Avoid clumping to reduce shade pressure"
        ])
    
    if has_burst:
        smart_tactics.extend([
            "Spread to avoid cleave damage",
            "Save defensive cooldowns for burst windows",
            "Focus burst specs before they can reset"
        ])
    
    if has_support:
        smart_tactics.extend([
            "Focus healers first to reduce sustain",
            "Split supports from DPS with positioning",
            "Interrupt key heal skills"
        ])
    
    # Fallback to generic tactics
    if not smart_tactics:
        smart_tactics = TACTICS.get(context, TACTICS["zerg"])
    
    return random.choice(smart_tactics)


def load_fights() -> list:
    """Load fights from database"""
    if not FIGHTS_DB_PATH.exists():
        print(f"Error: {FIGHTS_DB_PATH} not found")
        return []
    
    db = TinyDB(str(FIGHTS_DB_PATH))
    fights_table = db.table('fights')
    return fights_table.all()


def main():
    print("=" * 60)
    print("GW2 WvW Fine-tuning Dataset Generator")
    print("=" * 60)
    
    # Load fights
    fights = load_fights()
    print(f"\nLoaded {len(fights)} fights from database")
    
    if not fights:
        print("No fights found. Generating synthetic examples...")
        fights = []
    
    # Group fights by context
    fights_by_context = defaultdict(list)
    for fight in fights:
        context = fight.get('context', 'zerg')
        if context not in ['zerg', 'guild_raid', 'roam']:
            context = 'zerg'
        fights_by_context[context].append(fight)
    
    print(f"\nFights by context:")
    for ctx, ctx_fights in fights_by_context.items():
        print(f"  - {ctx}: {len(ctx_fights)}")
    
    # Generate datasets for both models
    import random
    
    for model_format in ["qwen", "mistral"]:
        print(f"\n--- Generating dataset for {model_format.upper()} ---")
        examples = []
        
        # From real fights
        for fight in fights:
            enemy_comp = fight.get('enemy_composition', {})
            if not enemy_comp:
                continue
            
            # Filter to valid specs only
            enemy_comp = {k: v for k, v in enemy_comp.items() if k in VALID_SPECS}
            if not enemy_comp:
                continue
            
            context = fight.get('context', 'zerg')
            if context not in ['zerg', 'guild_raid', 'roam']:
                context = 'zerg'
            
            outcome = fight.get('outcome', 'unknown')
            
            example = generate_example(enemy_comp, context, outcome, model_format)
            examples.append(example)
        
        print(f"Generated {len(examples)} examples from real fights")
        
        # Add synthetic examples to balance contexts
        for context in ['zerg', 'guild_raid', 'roam']:
            current_count = len([e for e in examples if e['context'] == context])
            needed = max(0, MIN_EXAMPLES_PER_CONTEXT - current_count)
            
            if needed > 0:
                print(f"Adding {needed} synthetic examples for {context}")
                
                for _ in range(needed):
                    num_specs = random.randint(3, 8) if context != 'roam' else random.randint(2, 5)
                    specs = random.sample(list(VALID_SPECS), min(num_specs, len(VALID_SPECS)))
                    enemy_comp = {}
                    for spec in specs:
                        enemy_comp[spec] = random.randint(1, 3) if context != 'roam' else 1
                    
                    example = generate_example(enemy_comp, context, model_format=model_format)
                    examples.append(example)
        
        print(f"Total examples: {len(examples)}")
        
        # Shuffle examples
        random.shuffle(examples)
        
        # Save to JSONL format
        output_path = OUTPUT_PATH_QWEN if model_format == "qwen" else OUTPUT_PATH_MISTRAL
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            for example in examples:
                record = {
                    "instruction": example["instruction"],
                    "output": example["output"]
                }
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        
        print(f"✓ Dataset saved to {output_path}")
    
    # Show sample
    print("\n" + "=" * 60)
    print("Sample example:")
    print("=" * 60)
    sample = examples[0]
    print(f"\n[INSTRUCTION]\n{sample['instruction']}")
    print(f"\n[OUTPUT]\n{sample['output']}")
    
    # Create fine-tuning instructions
    instructions_path = Path("docs/FINETUNE_INSTRUCTIONS.md")
    instructions_path.parent.mkdir(parents=True, exist_ok=True)
    
    instructions = """# Fine-tuning Mistral 7B for GW2 WvW

## Overview

This guide explains how to fine-tune Mistral 7B on the GW2 WvW dataset using open-source tools.

## Requirements

- **Hardware**: GPU with 16GB+ VRAM (or use cloud: RunPod, Vast.ai, Google Colab Pro)
- **Software**: Python 3.10+, PyTorch 2.0+

## Option 1: Unsloth (Recommended - Fastest)

Unsloth is 2x faster and uses 60% less memory than standard fine-tuning.

```bash
# Install
pip install unsloth

# Fine-tune (example notebook)
# See: https://github.com/unslothai/unsloth
```

```python
from unsloth import FastLanguageModel

# Load base model
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="mistralai/Mistral-7B-Instruct-v0.3",
    max_seq_length=2048,
    load_in_4bit=True,  # Use 4-bit quantization
)

# Add LoRA adapters
model = FastLanguageModel.get_peft_model(
    model,
    r=16,
    lora_alpha=16,
    lora_dropout=0,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
)

# Load dataset
from datasets import load_dataset
dataset = load_dataset("json", data_files="data/finetune_dataset.jsonl")

# Train
from trl import SFTTrainer
trainer = SFTTrainer(
    model=model,
    train_dataset=dataset["train"],
    dataset_text_field="instruction",
    max_seq_length=2048,
)
trainer.train()

# Save
model.save_pretrained_gguf("gw2-mistral-7b", tokenizer)
```

## Option 2: Axolotl

```bash
# Install
pip install axolotl

# Create config
cat > config.yaml << EOF
base_model: mistralai/Mistral-7B-Instruct-v0.3
datasets:
  - path: data/finetune_dataset.jsonl
    type: instruction
lora:
  r: 16
  alpha: 16
training:
  epochs: 3
  batch_size: 4
  learning_rate: 2e-4
EOF

# Train
accelerate launch -m axolotl.cli.train config.yaml
```

## Option 3: Google Colab (Free GPU)

1. Upload `data/finetune_dataset.jsonl` to Google Drive
2. Use this Colab notebook: https://colab.research.google.com/drive/1...
3. Run the Unsloth training code above

## After Fine-tuning

1. Convert to GGUF format for Ollama:
```bash
python llama.cpp/convert.py gw2-mistral-7b --outtype q4_k_m
```

2. Create Ollama model:
```bash
ollama create gw2-mistral -f Modelfile
```

3. Update `counter_ai.py`:
```python
MODEL_NAME = "gw2-mistral"
```

## Expected Results

- Training time: ~1-2 hours on RTX 3090
- Model size: ~4GB (quantized)
- Response quality: Much better format adherence
- Response time: Same as base Mistral 7B

## Resources

- Unsloth: https://github.com/unslothai/unsloth
- Axolotl: https://github.com/OpenAccess-AI-Collective/axolotl
- Ollama: https://ollama.ai
"""
    
    with open(instructions_path, 'w', encoding='utf-8') as f:
        f.write(instructions)
    
    print(f"\n✓ Fine-tuning instructions saved to {instructions_path}")


if __name__ == "__main__":
    main()
