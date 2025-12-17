#!/usr/bin/env python3
"""
Convert LoRA adapters to GGUF format for Ollama
"""

import os
import sys
import subprocess
from pathlib import Path

# Paths - use absolute paths
SCRIPT_DIR = Path(__file__).parent.parent
LORA_PATH = SCRIPT_DIR / "data" / "qwen25-3b-gw2-lora"
OUTPUT_DIR = SCRIPT_DIR / "data" / "qwen25-3b-gw2-gguf"
BASE_MODEL = "Qwen/Qwen2.5-3B-Instruct"

def main():
    print("=" * 60)
    print("🔄 Converting LoRA adapters to GGUF")
    print("=" * 60)
    
    if not LORA_PATH.exists():
        print(f"❌ LoRA path not found: {LORA_PATH}")
        sys.exit(1)
    
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    print(f"📁 LoRA path: {LORA_PATH}")
    print(f"📁 Output dir: {OUTPUT_DIR}")
    print(f"🤖 Base model: {BASE_MODEL}")
    
    try:
        from unsloth import FastLanguageModel
        import torch
        
        print("\n📥 Loading base model + LoRA adapters...")
        model, tokenizer = FastLanguageModel.from_pretrained(
            model_name=str(LORA_PATH),
            max_seq_length=2048,
            dtype=None,
            load_in_4bit=True,
        )
        
        print("✓ Model loaded")
        
        print("\n📦 Exporting to GGUF (q4_k_m quantization)...")
        model.save_pretrained_gguf(
            str(OUTPUT_DIR),
            tokenizer,
            quantization_method="q4_k_m",
        )
        
        print(f"\n✓ GGUF exported to: {OUTPUT_DIR}")
        
        # List output files
        print("\n📁 Output files:")
        for f in OUTPUT_DIR.iterdir():
            size_mb = f.stat().st_size / (1024 * 1024)
            print(f"   - {f.name}: {size_mb:.1f} MB")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\n💡 Alternative: Using llama.cpp for conversion")
        
        # Try llama.cpp method
        try:
            # First merge LoRA with base model
            print("\n📥 Merging LoRA with base model using PEFT...")
            from peft import PeftModel
            from transformers import AutoModelForCausalLM, AutoTokenizer
            
            print("Loading base model...")
            base_model = AutoModelForCausalLM.from_pretrained(
                BASE_MODEL,
                torch_dtype=torch.float16,
                device_map="auto",
            )
            
            print("Loading LoRA adapters...")
            model = PeftModel.from_pretrained(base_model, str(LORA_PATH))
            
            print("Merging weights...")
            merged_model = model.merge_and_unload()
            
            merged_path = OUTPUT_DIR / "merged"
            merged_path.mkdir(exist_ok=True)
            
            print(f"Saving merged model to {merged_path}...")
            merged_model.save_pretrained(str(merged_path))
            
            tokenizer = AutoTokenizer.from_pretrained(str(LORA_PATH))
            tokenizer.save_pretrained(str(merged_path))
            
            print("✓ Merged model saved")
            print("\nTo convert to GGUF, run:")
            print(f"  python -m llama_cpp.convert {merged_path} --outtype q4_k_m")
            
        except Exception as e2:
            print(f"❌ PEFT merge also failed: {e2}")
            sys.exit(1)

if __name__ == "__main__":
    main()
