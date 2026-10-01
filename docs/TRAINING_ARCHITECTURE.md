# NirmanAI — Distributed Systems Architecture Fine-Tuning Suite

Welcome to the **NirmanAI Training Suite**. This directory contains the complete end-to-end pipeline to fine-tune open-source Large Language Models (LLMs) into domain-expert **Principal Distributed Software Architects**.

---

## 📋 Directory Contents & Training Scripts

| File | Purpose | Execution Environment |
| :--- | :--- | :--- |
| [`train_nirmanai.py`](file:///home/raj-ribadiya/Desktop/PDS/training/train_nirmanai.py) | Master 4-bit QLoRA training engine with multi-dataset support & ChatML formatting. | GPU Workstation (16GB+ VRAM) |
| [`test_model.py`](file:///home/raj-ribadiya/Desktop/PDS/training/test_model.py) | Immediate inference verification script for the fine-tuned LoRA adapter. | GPU Workstation |
| [`export_gguf.py`](file:///home/raj-ribadiya/Desktop/PDS/training/export_gguf.py) | Merges LoRA adapter into 16-bit weights and exports to 4-bit GGUF (`q4_k_m`). | GPU / CPU |
| [`run_training.sh`](file:///home/raj-ribadiya/Desktop/PDS/training/run_training.sh) | Automated 1-click execution script (GPU check, venv setup, dependencies, training). | Linux / WSL2 GPU Workstation |
| [`requirements_training.txt`](file:///home/raj-ribadiya/Desktop/PDS/training/requirements_training.txt) | Exact PyTorch, CUDA, Hugging Face, PEFT, and TRL dependencies. | Python 3.10 / 3.11 |
| [`Modelfile`](file:///home/raj-ribadiya/Desktop/PDS/training/Modelfile) | Ready-to-use Ollama registration template for local CPU/RAM inference. | Local Laptop (Ollama) |
| [`RUN_TRAINING_GUIDE.md`](file:///home/raj-ribadiya/Desktop/PDS/training/RUN_TRAINING_GUIDE.md) | Quick operational cheatsheet for the college GPU PC. | Reference Guide |

---

## 🧠 Training Architecture & Strategy

### 1. Base Model Selection
* **Default Model**: `Qwen/Qwen2.5-7B-Instruct`
  * *Why Qwen 2.5 7B?* Highest benchmark performance in structured JSON output, code generation, reasoning, and context window (up to 32k/128k tokens).
* **Alternative Model**: `meta-llama/Meta-Llama-3.1-8B-Instruct`
  * Configurable via `--base_model` flag.

### 2. Parameter-Efficient Fine-Tuning (4-Bit QLoRA)
* **Quantization**: 4-bit NormalFloat (NF4) via `bitsandbytes` with double quantization.
* **Compute Dtype**: `bfloat16` (Ampere/Ada GPUs like RTX 3090, RTX 4090, A100) or `float16`.
* **LoRA Target Modules**: All linear attention and MLP projections:
  * `q_proj`, `k_proj`, `v_proj`, `o_proj`, `gate_proj`, `up_proj`, `down_proj`
* **LoRA Hyperparameters**:
  * LoRA Rank ($r$): `16`
  * LoRA Alpha ($\alpha$): `32` (Scaling factor = 2.0)
  * LoRA Dropout: `0.0` (with Unsloth) or `0.05`
* **Optimizer**: `paged_adamw_8bit` (Prevents VRAM spikes by paging optimizer states to CPU memory if needed).
* **Gradient Checkpointing**: Enabled (Reduces memory footprint by 60%+).

---

## 📊 Supported Datasets & Formats

The training script automatically detects and standardizes multiple dataset schemas into **ChatML / Qwen instruction format**:

### A. Rich System Design Dossiers (`datasets/nirmanai_master_rich_dossier.jsonl`)
* **Size**: 210,058 records (~1.43 GB)
* **Output Format**: Structured JSON with 6 essential architectural sections:
  1. `system_overview`: High-level architectural narrative and component topology.
  2. `capacity_planning`: Deterministic math for DAU, Peak QPS, Storage/yr, and Cache RAM.
  3. `mermaid_diagram`: Full production-grade Mermaid code (C4 & flowchart).
  4. `component_breakdown`: Detailed inventory of microservices, storage engines, and rationales.
  5. `trade_offs`: Explicit architectural trade-off evaluations (e.g. Consistency vs Latency).
  6. `bottlenecks_and_mitigation`: Failure mode audit & concrete mitigation tactics.

### B. Software Architecture Q&A & Theory (`datasets/Software_Architecture_Final.jsonl`)
* **Size**: 448,100 records (~782 MB)
* **Output Format**: Deep theoretical explanations, NFRs, patterns (CQRS, Event Sourcing, Hexagonal), and security threat models.

### C. Multi-Dataset Blended Training
To train an all-around architect that excels at both **System Dossier Synthesis** AND **In-Depth Architectural Reasoning**, pass both files separated by a comma:
```bash
python training/train_nirmanai.py --dataset_path datasets/nirmanai_master_rich_dossier.jsonl,datasets/Software_Architecture_Final.jsonl
```

---

## 🚀 Step-by-Step Execution Guide (College GPU PC)

### Step 1: Clone Repository & Create Virtual Environment
```bash
cd ~/Desktop
git clone https://github.com/SyncWithRaj/PDS.git
cd PDS

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r training/requirements_training.txt
```

*(Optional - 4x Faster Training)* Install Unsloth:
```bash
pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"
```

### Step 2: Verify GPU Detection
```bash
python3 -c "import torch; print('CUDA Available:', torch.cuda.is_available(), '| Device:', torch.cuda.get_device_name(0))"
```

### Step 3: Launch Training

**Option A: 1-Click Automated Script**
```bash
bash training/run_training.sh
```

**Option B: Train on Master System Design Dossiers (Default)**
```bash
python training/train_nirmanai.py
```

**Option C: Train on Both Datasets (Dossiers + Q&A Theory)**
```bash
python training/train_nirmanai.py --dataset_path datasets/nirmanai_master_rich_dossier.jsonl,datasets/Software_Architecture_Final.jsonl
```

**Option D: Fast Capped Run (e.g., 50k samples in 1-2 hours)**
```bash
python training/train_nirmanai.py --max_samples 50000 --batch_size 8 --grad_accum 2
```

---

## 🧪 Step 4: Verification & Testing

Verify that the fine-tuned LoRA adapter (`./nirmanai_adapter`) generates proper dossiers:

```bash
python training/test_model.py --prompt "Design an Enterprise Event-Driven FinTech payment settlement system on AWS with 100k+ TPS and Zero-Trust."
```

---

## 📦 Step 5: Export GGUF & Run on Laptop via Ollama

### On College GPU Workstation:
Convert the LoRA adapter into a single 4-bit GGUF binary:
```bash
python training/export_gguf.py --quantization q4_k_m
```
This produces `nirmanai_gguf/nirmanai-7b-q4_k_m.gguf` (~4.5 GB). Copy this file and `training/Modelfile` to your pen drive.

### On Your Local Laptop:
1. Ensure Ollama is installed (`ollama --version`).
2. Copy `nirmanai-7b-q4_k_m.gguf` into your project directory.
3. Register the model with Ollama:
   ```bash
   ollama create nirmanai -f training/Modelfile
   ```
4. Test running locally on your CPU/RAM:
   ```bash
   ollama run nirmanai "Design a real-time messaging architecture for 10M active users."
   ```

---

## 🛠️ Troubleshooting & Tips

* **CUDA Out Of Memory (OOM)**:
  * Reduce batch size: `--batch_size 2 --grad_accum 8`
  * Ensure gradient checkpointing is enabled (default in `train_nirmanai.py`).
* **Unsloth Installation Issues**:
  * Unsloth is optional. If installation encounters issues on the college PC, the script automatically falls back to standard Hugging Face PEFT + TRL without errors.
* **Arrow / Disk Space Limits**:
  * Training uses memory-mapped Arrow tables. Ensure at least 15 GB of free disk space on the college PC.
