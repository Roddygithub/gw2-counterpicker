# Fine-tuning Mistral 7B for GW2 WvW

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
