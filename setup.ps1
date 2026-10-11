# ==============================================================================
# NirmanAI - Automated Setup Script (Windows PowerShell)
# ==============================================================================
# Usage:
#   .\setup.ps1
# ==============================================================================

$ErrorActionPreference = "Stop"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  NirmanAI - Automated Project Setup & Initialization       " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Locate Python executable
$PythonCmd = $null
if (Get-Command "python" -ErrorAction SilentlyContinue) {
    $PythonCmd = "python"
} elseif (Get-Command "py" -ErrorAction SilentlyContinue) {
    $PythonCmd = "py"
}

if (-not $PythonCmd) {
    Write-Host "[ERROR] Python is not installed or not in your PATH." -ForegroundColor Red
    Write-Host "Please install Python 3.11+ from https://python.org" -ForegroundColor Yellow
    exit 1
}

$PyVersion = & $PythonCmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')"
Write-Host "[OK] Detected Python version: $PyVersion" -ForegroundColor Green

# 2. Virtual Environment Setup
$VenvDir = ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
    Write-Host "[*] Creating virtual environment in '$VenvDir'..." -ForegroundColor Yellow
    & $PythonCmd -m venv $VenvDir
    Write-Host "[OK] Virtual environment created." -ForegroundColor Green
} else {
    Write-Host "[OK] Virtual environment exists at '$VenvDir'." -ForegroundColor Green
}

# 3. Upgrade pip and build tools
Write-Host "[*] Upgrading pip, setuptools, and wheel..." -ForegroundColor Yellow
& $VenvPython -m pip install --upgrade pip setuptools wheel --quiet

# 4. Install dependencies
Write-Host "[*] Installing required dependencies from requirements.txt..." -ForegroundColor Yellow
& $VenvPython -m pip install -r requirements.txt

Write-Host "[*] Installing NirmanAI package in editable mode (-e .)..." -ForegroundColor Yellow
& $VenvPython -m pip install -e . --no-deps

# 5. Environment configuration (.env)
if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Host "[WARN] Created '.env' from '.env.example'." -ForegroundColor Yellow
        Write-Host "       Please add your GEMINI_API_KEY into '.env'!" -ForegroundColor Yellow
    }
} else {
    Write-Host "[OK] '.env' configuration file is present." -ForegroundColor Green
}

# 6. Ensure output directory exists
if (-not (Test-Path "output")) {
    New-Item -ItemType Directory -Path "output" -Force | Out-Null
    Write-Host "[OK] Created output directory at 'output/'." -ForegroundColor Green
}

# 7. Verification Test
Write-Host ""
Write-Host "[*] Running health check verification..." -ForegroundColor Yellow
& $VenvPython -c "import nirman, pydantic, langgraph, typer, rich; from nirman.workflow import NirmanWorkflow; print('[OK] NirmanAI core modules loaded successfully!')"

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  NirmanAI Setup Complete! Ready to architect systems.      " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Quick Start Commands:" -ForegroundColor White
Write-Host "  1. Activate Virtual Environment:" -ForegroundColor Gray
Write-Host "     .\.venv\Scripts\Activate.ps1" -ForegroundColor Cyan
Write-Host ""
Write-Host "  2. Launch Web UI (Interactive Prototype Dashboard):" -ForegroundColor Gray
Write-Host "     python -m nirman.interfaces.web_ui" -ForegroundColor Cyan
Write-Host "     (Open http://localhost:8000 in your browser)" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  3. Run Terminal CLI Synthesizer:" -ForegroundColor Gray
Write-Host "     python -m nirman.interfaces.cli synthesize `"Design a real-time food delivery system for 20M DAU`"" -ForegroundColor Cyan
Write-Host ""
Write-Host "  4. Run End-to-End Agentic Test Suite:" -ForegroundColor Gray
Write-Host "     python tests/e2e/test_e2e_agentic.py" -ForegroundColor Cyan
Write-Host ""
