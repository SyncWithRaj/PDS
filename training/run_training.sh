#!/usr/bin/env bash
# NirmanAI - Automated Training Launcher for College GPU Workstation
# =================================================================

set -e

echo "================================================================================"
echo "                   NIRMAN-AI : GPU TRAINING LAUNCHER"
echo "================================================================================"

# 1. Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: python3 is not installed or not in PATH."
    exit 1
fi

echo "🐍 Python version: $(python3 --version)"

# 2. Check NVIDIA GPU
if command -v nvidia-smi &> /dev/null; then
    echo "🔥 NVIDIA GPU Detected:"
    nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader
else
    echo "⚠️ Warning: nvidia-smi not found. Ensure NVIDIA drivers are properly installed."
fi

# 3. Virtual Environment Setup
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$ROOT_DIR"

if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment (.venv)..."
    python3 -m venv .venv
fi

echo "⚡ Activating virtual environment..."
source .venv/bin/activate

# 4. Install dependencies
echo "📥 Checking / Installing training dependencies..."
pip install --upgrade pip --quiet
pip install -r "$SCRIPT_DIR/requirements_training.txt" --quiet

# Check for Unsloth
python3 -c "import unsloth" 2>/dev/null && echo "🚀 Unsloth fast engine is available!" || echo "ℹ️ Unsloth not installed. Using standard Hugging Face PEFT + TRL engine."

# 5. Launch Training
echo ""
echo "🚀 Launching NirmanAI Master Training Script..."
echo "================================================================================"
python3 "$SCRIPT_DIR/train_nirmanai.py" "$@"

echo ""
echo "================================================================================"
echo "✅ Training execution finished!"
echo "Next step: Run 'python3 training/export_gguf.py' to generate GGUF for Ollama."
echo "================================================================================"
