#!/usr/bin/env python3
"""
Simple conversion from LoRA to GGUF using llama-cpp-python
"""

import os
from pathlib import Path

# Force CPU
os.environ["CUDA_VISIBLE_DEVICES"] = ""

# Paths
LORA_PATH = Path("data/qwen25-3b-gw2-lora")
OUTPUT_PATH = Path("data/qwen25-3b-gw2.gguf")

print("=" * 60)
print("🔄 Converting LoRA to GGUF (CPU only)")
print("=" * 60)

try:
    from llama_cpp import Llama
    from llama_cpp.llama_speculative import LlamaDraftModel
    from huggingface_hub import snapshot_download
    
    print("✓ Dependencies loaded")
    
    # Download base model (if not cached)
    print("\n📥 Ensuring base model is available...")
    model_path = snapshot_download(
        repo_id="Qwen/Qwen2.5-3B-Instruct-GGUF",
        allow_patterns=["*q4_k_m.gguf"],
        cache_dir="data/hf_cache"
    )
    
    # Find the GGUF file
    gguf_files = list(Path(model_path).glob("*q4_k_m.gguf"))
    if not gguf_files:
        print("❌ GGUF file not found")
        exit(1)
    
    base_gguf = gguf_files[0]
    print(f"✓ Base GGUF: {base_gguf}")
    
    # Load base model
    print("\n📥 Loading base model...")
    llm = Llama(
        model_path=str(base_gguf),
        n_ctx=2048,
        n_gpu_layers=0,  # CPU only
        verbose=False
    )
    print("✓ Base model loaded")
    
    # Apply LoRA (if supported)
    print("\n🔀 Applying LoRA adapters...")
    # Note: llama-cpp-python might not support LoRA directly
    # This is a limitation - we need to merge first
    
    print("⚠️ llama-cpp-python doesn't support LoRA directly")
    print("We need to merge the LoRA with the base model first...")
    
except ImportError as e:
    print(f"❌ Missing dependency: {e}")
    print("\n💡 Alternative approach:")
    print("1. Use transformers + peft to merge LoRA")
    print("2. Then use llama.cpp to convert to GGUF")
    
    # Try the merge approach
    print("\n" + "=" * 60)
    print("🔄 Alternative: Merge with transformers first")
    print("=" * 60)
    
    import torch
    torch.set_default_device("cpu")
    
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel
    
    print("📥 Loading base model (CPU)...")
    base_model = AutoModelForCausalLM.from_pretrained(
        "Qwen/Qwen2.5-3B-Instruct",
        torch_dtype=torch.float16,
        device_map="cpu",
        low_cpu_mem_usage=True,
    )
    
    print("📥 Loading LoRA adapters...")
    model = PeftModel.from_pretrained(base_model, str(LORA_PATH))
    
    print("🔀 Merging weights...")
    merged_model = model.merge_and_unload()
    
    print("💾 Saving merged model...")
    merged_dir = Path("data/qwen25-3b-merged")
    merged_dir.mkdir(exist_ok=True)
    merged_model.save_pretrained(str(merged_dir), safe_serialization=True)
    
    tokenizer = AutoTokenizer.from_pretrained(str(LORA_PATH))
    tokenizer.save_pretrained(str(merged_dir))
    
    print("✓ Merge complete!")
    print(f"\nMerged model saved to: {merged_dir}")
    print("\nNext step: Convert to GGUF using llama.cpp")
    print(f"Run: python -m llama_cpp.convert {merged_dir} --outfile {OUTPUT_PATH} --outtype q4_k_m")

except Exception as e:
    print(f"❌ Error: {e}")
    print("\n💡 The issue is that Python 3.14 is not compatible with PyTorch")
    print("Consider using Python 3.11 or Docker with Python 3.11")
