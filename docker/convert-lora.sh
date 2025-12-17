#!/bin/bash

# Convert LoRA adapters to GGUF using Docker container

echo "=== LoRA to GGUF Converter ==="
echo "Python version: $(python --version)"

# Paths inside container
LORA_PATH="/workspace/input/qwen25-3b-gw2-lora"
OUTPUT_DIR="/workspace/output"
GGUF_OUTPUT="/workspace/output/qwen25-3b-gw2.gguf"

# Create directories
mkdir -p "$OUTPUT_DIR"

# Check LoRA files
if [ ! -d "$LORA_PATH" ]; then
    echo "❌ LoRA path not found: $LORA_PATH"
    echo "Please mount the LoRA directory to /workspace/input"
    exit 1
fi

echo "✓ LoRA path: $LORA_PATH"
echo "✓ Output dir: $OUTPUT_DIR"

# Force CPU only
export CUDA_VISIBLE_DEVICES=""

# Step 1: Merge LoRA with base model
echo ""
echo "📥 Loading base model (CPU)..."
python3 << 'EOF'
import os
os.environ["CUDA_VISIBLE_DEVICES"] = ""
import torch
torch.set_default_device("cpu")

from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

print("Loading base model Qwen/Qwen2.5-3B-Instruct...")
base_model = AutoModelForCausalLM.from_pretrained(
    "Qwen/Qwen2.5-3B-Instruct",
    torch_dtype=torch.float16,
    device_map="cpu",
    low_cpu_mem_usage=True,
)

print("Loading LoRA adapters...")
model = PeftModel.from_pretrained(base_model, "/workspace/input/qwen25-3b-gw2-lora")

print("Merging weights...")
merged_model = model.merge_and_unload()

print("Saving merged model...")
merged_model.save_pretrained("/workspace/output", safe_serialization=True)

tokenizer = AutoTokenizer.from_pretrained("/workspace/input/qwen25-3b-gw2-lora")
tokenizer.save_pretrained("/workspace/output")

print("✓ Merge complete!")
EOF

if [ $? -ne 0 ]; then
    echo "❌ Merge failed"
    exit 1
fi

# Step 2: Convert to GGUF
echo ""
echo "📦 Converting to GGUF (q4_k_m)..."
/workspace/llama.cpp/convert_hf_to_gguf.py \
    --model-dir /workspace/output \
    --outfile /workspace/output/qwen25-3b-gw2-q4_k_m.gguf \
    --outtype q4_k_m

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ SUCCESS!"
    echo "GGUF file created: /workspace/output/qwen25-3b-gw2-q4_k_m.gguf"
    ls -lh /workspace/output/*.gguf
else
    echo "❌ GGUF conversion failed"
    exit 1
fi
