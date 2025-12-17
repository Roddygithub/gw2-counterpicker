#!/usr/bin/env python3
"""
Merge LoRA adapters with base model using CPU only
Then convert to GGUF using llama.cpp
"""

import os
import sys
from pathlib import Path

# Paths
SCRIPT_DIR = Path(__file__).parent.parent
LORA_PATH = SCRIPT_DIR / "data" / "qwen25-3b-gw2-lora"
OUTPUT_DIR = SCRIPT_DIR / "data" / "qwen25-3b-gw2-merged"
GGUF_OUTPUT = SCRIPT_DIR / "data" / "qwen25-3b-gw2.gguf"
BASE_MODEL = "Qwen/Qwen2.5-3B-Instruct"

def main():
    print("=" * 60)
    print("🔄 Merging LoRA adapters with base model (CPU)")
    print("=" * 60)
    
    if not LORA_PATH.exists():
        print(f"❌ LoRA path not found: {LORA_PATH}")
        sys.exit(1)
    
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    print(f"📁 LoRA path: {LORA_PATH}")
    print(f"📁 Output dir: {OUTPUT_DIR}")
    print(f"🤖 Base model: {BASE_MODEL}")
    
    # Force CPU
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    
    import torch
    torch.set_default_device("cpu")
    
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel
    
    print("\n📥 Loading base model (CPU, this may take a while)...")
    base_model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        torch_dtype=torch.float16,
        device_map="cpu",
        low_cpu_mem_usage=True,
    )
    print("✓ Base model loaded")
    
    print("\n📥 Loading LoRA adapters...")
    model = PeftModel.from_pretrained(base_model, str(LORA_PATH))
    print("✓ LoRA adapters loaded")
    
    print("\n🔀 Merging weights...")
    merged_model = model.merge_and_unload()
    print("✓ Weights merged")
    
    print(f"\n💾 Saving merged model to {OUTPUT_DIR}...")
    merged_model.save_pretrained(str(OUTPUT_DIR), safe_serialization=True)
    
    tokenizer = AutoTokenizer.from_pretrained(str(LORA_PATH))
    tokenizer.save_pretrained(str(OUTPUT_DIR))
    print("✓ Merged model saved")
    
    print("\n" + "=" * 60)
    print("✅ MERGE COMPLETE")
    print("=" * 60)
    print(f"\nMerged model saved to: {OUTPUT_DIR}")
    print("\nNext step: Convert to GGUF using llama.cpp:")
    print(f"  python -m llama_cpp.server.convert {OUTPUT_DIR} --outfile {GGUF_OUTPUT} --outtype q4_k_m")

if __name__ == "__main__":
    main()
