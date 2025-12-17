#!/usr/bin/env python3
"""
Merge LoRA adapters with base model and convert to GGUF using Python 3.11
"""

import os
import sys
from pathlib import Path

# Use Python 3.11 from pyenv
PYTHON311 = "/home/roddy/.pyenv/versions/3.11.10/bin/python"
PIP311 = "/home/roddy/.pyenv/versions/3.11.10/bin/pip"

# Paths
LORA_PATH = Path("data/qwen25-3b-gw2-lora")
MERGED_DIR = Path("data/qwen25-3b-merged")
GGUF_OUTPUT = Path("data/qwen25-3b-gw2.gguf")

print("=" * 60)
print("🔄 Using Python 3.11 for LoRA to GGUF conversion")
print("=" * 60)

# Step 1: Install dependencies in Python 3.11
print("\n1️⃣ Installing PyTorch and dependencies...")
install_cmd = f"{PIP311} install torch --index-url https://download.pytorch.org/whl/cpu"
print(f"Running: {install_cmd}")
os.system(install_cmd)

install_deps = f"{PIP311} install transformers peft accelerate huggingface_hub"
print(f"Running: {install_deps}")
os.system(install_deps)

# Step 2: Merge LoRA with base model
print("\n2️⃣ Merging LoRA adapters with base model...")
merge_script = f"""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = ''
import torch
torch.set_default_device('cpu')
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

print('Loading base model...')
base_model = AutoModelForCausalLM.from_pretrained(
    'Qwen/Qwen2.5-3B-Instruct',
    torch_dtype=torch.float16,
    device_map='cpu',
    low_cpu_mem_usage=True,
)

print('Loading LoRA adapters...')
model = PeftModel.from_pretrained(base_model, '{LORA_PATH}')

print('Merging weights...')
merged_model = model.merge_and_unload()

print('Saving merged model...')
merged_model.save_pretrained('{MERGED_DIR}', safe_serialization=True)

tokenizer = AutoTokenizer.from_pretrained('{LORA_PATH}')
tokenizer.save_pretrained('{MERGED_DIR}')

print('✓ Merge complete!')
"""

# Write merge script to temp file
with open("temp_merge.py", "w") as f:
    f.write(merge_script)

# Run merge with Python 3.11
os.system(f"{PYTHON311} temp_merge.py")

# Clean up temp file
os.remove("temp_merge.py")

# Step 3: Install llama.cpp and convert
print("\n3️⃣ Installing llama.cpp and converting to GGUF...")
install_llamacpp = f"{PIP311} install llama-cpp-python"
print(f"Running: {install_llamacpp}")
os.system(install_llamacpp)

# Convert to GGUF
convert_script = f"""
from llama_cpp.convert_hf_to_gguf import main
import sys
sys.argv = ['convert', '{MERGED_DIR}', '--outfile', '{GGUF_OUTPUT}', '--outtype', 'q4_k_m']
main()
print('✓ GGUF conversion complete!')
print(f'GGUF file saved to: {GGUF_OUTPUT}')
"""

with open("temp_convert.py", "w") as f:
    f.write(convert_script)

os.system(f"{PYTHON311} temp_convert.py")
os.remove("temp_convert.py")

# Check results
if GGUF_OUTPUT.exists():
    size_mb = GGUF_OUTPUT.stat().st_size / (1024 * 1024)
    print(f"\n✅ SUCCESS! GGUF file created: {size_mb:.1f} MB")
    print(f"\nNext steps:")
    print(f"1. ollama create qwen25-gw2 -f data/Modelfile.qwen")
    print(f"2. ollama run qwen25-gw2")
else:
    print(f"\n❌ GGUF file not found at {GGUF_OUTPUT}")
