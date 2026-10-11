#!/usr/bin/env bash
# ==============================================================================
# NirmanAI - Automated Setup Script (Linux / macOS / Git Bash)
# ==============================================================================
# Usage:
#   chmod +x setup.sh && ./setup.sh
# ==============================================================================

set -e

echo "============================================================"
echo "  NirmanAI - Automated Project Setup & Initialization       "
echo "============================================================"
echo ""

# 1. Locate Python 3
if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
    PYTHON_CMD="python"
else
    echo "[ERROR] Python 3 is not installed or not in your PATH."
    exit 1
fi

PY_VER=$($PYTHON_CMD -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')")
echo "[OK] Detected Python version: $PY_VER"

# 2. Virtual Environment Setup
VENV_DIR=".venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "[*] Creating virtual environment in '$VENV_DIR'..."
    $PYTHON_CMD -m venv "$VENV_DIR"
    echo "[OK] Virtual environment created."
else
    echo "[OK] Virtual environment already exists at '$VENV_DIR'."
fi

# Detect platform venv python path
if [ -f "$VENV_DIR/bin/python" ]; then
    VENV_PY="$VENV_DIR/bin/python"
elif [ -f "$VENV_DIR/Scripts/python.exe" ]; then
    VENV_PY="$VENV_DIR/Scripts/python.exe"
else
    echo "[ERROR] Could not find Python binary in $VENV_DIR"
    exit 1
fi

# 3. Upgrade pip
echo "[*] Upgrading pip, setuptools, and wheel..."
$VENV_PY -m pip install --upgrade pip setuptools wheel --quiet

# 4. Install dependencies
echo "[*] Installing required dependencies from requirements.txt..."
$VENV_PY -m pip install -r requirements.txt

echo "[*] Installing NirmanAI in editable mode (-e .)..."
$VENV_PY -m pip install -e . --no-deps

# 5. Environment configuration (.env)
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "[WARN] Created '.env' from '.env.example'."
        echo "       Please add your GEMINI_API_KEY into '.env'!"
    fi
else
    echo "[OK] '.env' configuration file is present."
fi

# 6. Ensure output directory exists
mkdir -p output
echo "[OK] Output directory verified at 'output/'."

# 7. Verification Test
echo ""
echo "[*] Running health check verification..."
$VENV_PY -c "import nirman, pydantic, langgraph, typer, rich; from nirman.workflow import NirmanWorkflow; print('[OK] NirmanAI core modules loaded successfully!')"

echo ""
echo "============================================================"
echo "  NirmanAI Setup Complete! Ready to architect systems.      "
echo "============================================================"
echo ""
echo "Quick Start Commands:"
echo "  1. Activate Virtual Environment:"
echo "     source .venv/bin/activate  (or source .venv/Scripts/activate on Windows Git Bash)"
echo ""
echo "  2. Launch Web UI (Interactive Prototype Dashboard):"
echo "     python -m nirman.interfaces.web_ui"
echo "     (Open http://localhost:8000 in your browser)"
echo ""
echo "  3. Run Terminal CLI Synthesizer:"
echo "     python -m nirman.interfaces.cli synthesize \"Design a real-time food delivery system for 20M DAU\""
echo ""
echo "  4. Run End-to-End Agentic Test Suite:"
echo "     python tests/e2e/test_e2e_agentic.py"
echo ""
