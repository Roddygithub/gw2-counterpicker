FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    wget \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /workspace

# Install Python dependencies
RUN pip install --no-cache-dir torch transformers peft accelerate huggingface_hub

# Clone llama.cpp for GGUF conversion
RUN git clone https://github.com/ggerganov/llama.cpp.git /workspace/llama.cpp

# Install llama.cpp Python requirements
RUN pip install --no-cache-dir -r /workspace/llama.cpp/requirements.txt

# Make convert script
RUN make -C /workspace/llama.cpp

# Copy conversion script
COPY convert-lora.sh /workspace/convert-lora.sh
RUN chmod +x /workspace/convert-lora.sh

ENTRYPOINT ["/workspace/convert-lora.sh"]
