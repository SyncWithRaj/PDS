# NirmanAI — College GPU Training Execution Guide

This guide contains the step-by-step instructions to fine-tune the NirmanAI model on your college GPU workstation (RTX 3090, RTX 4090, A100, V100, or any modern NVIDIA GPU).

---

## Prerequisites (College GPU PC)
* Operating System: Linux (Ubuntu 20.04/22.04 recommended) or Windows with WSL2
* NVIDIA Driver installed (`nvidia-smi` works)
* Python 3.10 or 3.11 installed
* At least 16GB VRAM (24GB VRAM recommended for fast training)

---

## Step 1: Copy Folder to College PC & Setup Environment

1. Plug in your pen drive and copy the `PDS` project folder to the college PC Desktop:
   ```bash
   cd ~/Desktop/PDS
   ```

2. Create a clean virtual environment on the college PC:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Install the training dependencies:
   ```bash
   pip install --upgrade pip
   pip install -r training/requirements_training.txt
   ```

4. *(Highly Recommended for 4x Faster Training)* Install Unsloth:
   ```bash
   pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"
   ```

5. Verify GPU is recognized by PyTorch:
   ```bash
   python3 -c "import torch; print('GPU Available:', torch.cuda.is_available(), '| GPU Name:', torch.cuda.get_device_name(0))"
   ```

---

## Step 2: Launch Fine-Tuning

Run the master training script:

```bash
python training/train_nirmanai.py
```

### Custom Training Options:
* **Train on Master Rich Dossiers (Default):**
  ```bash
  python training/train_nirmanai.py --dataset_path datasets/nirmanai_master_rich_dossier.jsonl
  ```
* **Train on BOTH Datasets (Dossiers + Architectural Reasoning & Q&A):**
  ```bash
  python training/train_nirmanai.py --dataset_path datasets/nirmanai_master_rich_dossier.jsonl,datasets/Software_Architecture_Final.jsonl
  ```
* **Fast Capped Run (e.g. 50k samples for quick training in 1-2 hours):**
  ```bash
  python training/train_nirmanai.py --max_samples 50000
  ```
* **To adjust batch size (if 24GB VRAM):**
  ```bash
  python training/train_nirmanai.py --batch_size 8 --grad_accum 2
  ```
* **To train for 2 epochs:**
  ```bash
  python training/train_nirmanai.py --epochs 2
  ```

---

## Step 3: Verify & Test the Trained Model

Once training finishes, the fine-tuned LoRA adapter will be saved to `./nirmanai_adapter`.

Run a test inference to verify that the model generates the complete NirmanAI System Design Dossier:

```bash
python training/test_model.py --prompt "Design a real-time food delivery backend like DoorDash for 25 million users with live GPS tracking on AWS"
```

You will see the model output the full JSON with:
* `system_overview`
* `capacity_planning` (DAU, Peak QPS, Storage)
* `mermaid_diagram`
* `component_breakdown`
* `trade_offs`
* `bottlenecks_and_mitigation`

---

## Step 4: Export to GGUF Format for Ollama

To run this model on your laptop completely offline with low RAM usage, convert it to a 4-bit GGUF file:

```bash
python training/export_gguf.py --quantization q4_k_m
```

This will produce: `nirmanai_gguf/nirmanai-7b-q4_k_m.gguf` (~4.5 GB).

---

## Step 5: Transfer to Laptop & Run in Ollama

1. Copy the single `nirmanai-7b-q4_k_m.gguf` file to your pen drive and bring it to your laptop.
2. On your laptop, register the model in Ollama:
   ```bash
   ollama create nirmanai -f training/Modelfile
   ```
3. Test your model in the terminal (100% offline):
   ```bash
   ollama run nirmanai "Design a scalable ride-sharing platform like Uber"
   ```

Now your fine-tuned domain model is live and ready to power NirmanAI's multi-agent engine!
