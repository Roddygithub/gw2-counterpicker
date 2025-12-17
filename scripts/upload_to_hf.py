#!/usr/bin/env python3
"""
Upload LoRA adapters to Hugging Face for GGUF conversion
"""

from huggingface_hub import HfApi, login
from pathlib import Path
import zipfile

# Configuration
REPO_ID = "Roddy13/qwen25-3b-gw2-lora"  # Change to your username
LORA_PATH = Path("data/qwen25-3b-gw2-lora")

print("=" * 60)
print("📤 Upload LoRA to Hugging Face")
print("=" * 60)

# 1. Login (do this once)
print("\n1️⃣ First, login to Hugging Face:")
print("   - Go to https://huggingface.co/settings/tokens")
print("   - Create a token with 'Write' permission")
print("   - Run: huggingface-cli login")
print("   - Paste your token when prompted")

# 2. Create repo
print("\n2️⃣ Creating repository...")
api = HfApi()

try:
    api.create_repo(
        repo_id=REPO_ID,
        repo_type="model",
        private=False,
        exist_ok=True,
    )
    print(f"✓ Repository created: https://huggingface.co/{REPO_ID}")
except Exception as e:
    print(f"Repo might already exist: {e}")

# 3. Upload files
print("\n3️⃣ Uploading LoRA files...")
api = HfApi()

for file_path in LORA_PATH.glob("*"):
    if file_path.is_file():
        print(f"   Uploading {file_path.name}...")
        api.upload_file(
            path_or_fileobj=str(file_path),
            path_in_repo=file_path.name,
            repo_id=REPO_ID,
            repo_type="model",
        )

print("\n✅ Upload complete!")
print(f"\n📂 Repository: https://huggingface.co/{REPO_ID}")

# 4. Instructions for GGUF conversion
print("\n" + "=" * 60)
print("📋 Next Steps for GGUF Conversion")
print("=" * 60)
print("""
Option A - Use TheBloke's converter (recommended):
1. Go to: https://huggingface.co/spaces/TheBloke/Convert-to-GGUF
2. Enter your repo ID: Roddy13/qwen25-3b-gw2-lora
3. Select quantization: q4_k_m
4. Click "Convert"
5. Download the GGUF file

Option B - Use GGUF-My-Repo:
1. Go to: https://huggingface.co/spaces/ggml-org/gguf-my-repo
2. Enter your repo ID
3. Select quantization options
4. Convert and download

Once you have the GGUF file:
1. Save it to: data/qwen25-3b-gw2.gguf
2. Run: ollama create qwen25-gw2 -f data/Modelfile.qwen
3. Test: ollama run qwen25-gw2
""")
