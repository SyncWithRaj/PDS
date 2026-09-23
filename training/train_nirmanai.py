#!/usr/bin/env python3
"""
NirmanAI - Master Model Fine-Tuning Script
===========================================
Fine-tunes Qwen 2.5 7B Instruct (or Llama 3.1 8B) on the NirmanAI System Design
Dossier Dataset using 4-bit QLoRA.

Features:
  - Auto-detects Unsloth (for 4x faster training) with fallback to standard Hugging Face PEFT + TRL.
  - ChatML / Qwen instruction prompt formatting.
  - Gradient checkpointing and 8-bit Paged AdamW to guarantee Zero Out-Of-Memory (OOM).
  - Automatically saves the trained LoRA adapter.

Usage:
  python training/train_nirmanai.py
  python training/train_nirmanai.py --epochs 1 --batch_size 4 --lora_rank 16
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import torch


def parse_args():
    parser = argparse.ArgumentParser(description="NirmanAI QLoRA Fine-Tuning Script")
    parser.add_argument(
        "--base_model",
        type=str,
        default="Qwen/Qwen2.5-7B-Instruct",
        help="Base model to fine-tune (Qwen/Qwen2.5-7B-Instruct or unsloth/Qwen2.5-7B-Instruct-bnb-4bit)",
    )
    parser.add_argument(
        "--dataset_path",
        type=str,
        default="datasets/nirmanai_master_rich_dossier.jsonl",
        help="Path to training dataset JSONL file (or comma-separated list of JSONL files)",
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="./nirmanai_adapter",
        help="Output directory for fine-tuned LoRA adapter",
    )
    parser.add_argument("--epochs", type=int, default=1, help="Number of training epochs")
    parser.add_argument("--batch_size", type=int, default=4, help="Per device batch size")
    parser.add_argument("--grad_accum", type=int, default=4, help="Gradient accumulation steps")
    parser.add_argument("--lr", type=float, default=2e-4, help="Learning rate")
    parser.add_argument("--lora_rank", type=int, default=16, help="LoRA Rank (r)")
    parser.add_argument("--lora_alpha", type=int, default=32, help="LoRA Alpha (alpha)")
    parser.add_argument("--max_seq_length", type=int, default=2048, help="Max sequence length in tokens")
    parser.add_argument("--save_steps", type=int, default=500, help="Save checkpoint every N steps")
    parser.add_argument("--max_samples", type=int, default=None, help="Optional max training samples limit")
    return parser.parse_args()


def print_system_info():
    print("=" * 80)
    print("                   NIRMAN-AI : QLoRA FINE-TUNING SUITE")
    print("=" * 80)
    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        print(f"🔥 GPU Detected:  {gpu_name} ({vram_gb:.1f} GB VRAM)")
        print(f"🚀 CUDA Version:  {torch.version.cuda}")
    else:
        print("⚠️  WARNING: No NVIDIA GPU detected! Training on CPU is not recommended.")
    print("=" * 80 + "\n")


def format_prompts(batch, tokenizer):
    """Formats raw record into standard Qwen / ChatML instruction format.
    Handles both Rich Dossier schemas (instruction=system, input=user) and
    Alpaca / Q&A schemas (instruction=user query, input='').
    """
    texts = []
    default_system = (
        "You are NirmanAI, an autonomous distributed software architect. "
        "You synthesize production-grade system design dossiers, analyze architectural trade-offs, "
        "and provide rigorous, scalable solutions."
    )

    instructions = batch.get("instruction", [])
    inputs = batch.get("input", [""] * len(instructions))
    outputs = batch.get("output", [""] * len(instructions))

    for instruction, user_input, output in zip(instructions, inputs, outputs):
        output_str = json.dumps(output, indent=2) if isinstance(output, (dict, list)) else str(output)
        inst_str = (instruction or "").strip()
        inp_str = (user_input or "").strip()

        if inp_str:
            # Case 1: System persona in instruction, user problem in input
            if "NirmanAI" in inst_str or len(inst_str) > 100:
                system_msg = inst_str
                user_msg = inp_str
            else:
                system_msg = default_system
                user_msg = f"{inst_str}\n\nContext / Constraints:\n{inp_str}"
        else:
            # Case 2: Q&A / Architecture reasoning (question in instruction, input empty)
            system_msg = default_system
            user_msg = inst_str

        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
            {"role": "assistant", "content": output_str},
        ]

        formatted_text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
        texts.append(formatted_text)
    return {"text": texts}


def load_all_datasets(dataset_paths_str: str, max_samples: int = None):
    """Loads and concatenates one or more JSONL dataset files."""
    from datasets import load_dataset, concatenate_datasets

    paths = [p.strip() for p in dataset_paths_str.split(",") if p.strip()]
    loaded_splits = []

    for p in paths:
        path_obj = Path(p)
        if not path_obj.exists():
            print(f"❌ Error: Dataset file not found at: {path_obj}")
            sys.exit(1)
        print(f"📂 Loading dataset from: {path_obj}...")
        ds = load_dataset("json", data_files=str(path_obj), split="train")
        print(f"   ↳ Loaded {len(ds):,} records.")
        loaded_splits.append(ds)

    if len(loaded_splits) == 1:
        combined = loaded_splits[0]
    else:
        combined = concatenate_datasets(loaded_splits)
        # Shuffle combined dataset so different sources interleave nicely
        combined = combined.shuffle(seed=42)

    if max_samples and max_samples < len(combined):
        print(f"✂️  Capping dataset to {max_samples:,} records as requested.")
        combined = combined.select(range(max_samples))

    print(f"✅ Total training dataset ready: {len(combined):,} records.")
    return combined


def train():
    args = parse_args()
    print_system_info()

    dataset = load_all_datasets(args.dataset_path, args.max_samples)

    # Try Unsloth first
    unsloth_available = False
    try:
        from unsloth import FastLanguageModel
        unsloth_available = True
        print("\n🚀 Using Unsloth FastLanguageModel engine (4x faster, optimal VRAM)!")
    except ImportError:
        print("\nℹ️  Unsloth not found. Using standard Hugging Face PEFT + TRL engine.")

    if unsloth_available:
        # 1. Unsloth Engine
        model, tokenizer = FastLanguageModel.from_pretrained(
            model_name=args.base_model,
            max_seq_length=args.max_seq_length,
            load_in_4bit=True,
            dtype=torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16,
        )

        model = FastLanguageModel.get_peft_model(
            model,
            r=args.lora_rank,
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
            lora_alpha=args.lora_alpha,
            lora_dropout=0,
            bias="none",
            use_gradient_checkpointing="unsloth",
            random_state=42,
        )
    else:
        # 2. Standard Hugging Face Engine
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
        from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16,
            bnb_4bit_use_double_quant=True,
        )

        tokenizer = AutoTokenizer.from_pretrained(args.base_model, trust_remote_code=True)
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

        model = AutoModelForCausalLM.from_pretrained(
            args.base_model,
            quantization_config=bnb_config,
            device_map="auto",
            trust_remote_code=True,
        )
        model = prepare_model_for_kbit_training(model)

        peft_config = LoraConfig(
            r=args.lora_rank,
            lora_alpha=args.lora_alpha,
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
            lora_dropout=0.05,
            bias="none",
            task_type="CAUSAL_LM",
        )
        model = get_peft_model(model, peft_config)

    print("\nFormatting training records with ChatML template...")
    formatted_dataset = dataset.map(
        lambda batch: format_prompts(batch, tokenizer),
        batched=True,
        remove_columns=dataset.column_names,
    )

    # Set up SFTTrainer
    from trl import SFTTrainer
    from transformers import TrainingArguments

    training_args = TrainingArguments(
        output_dir=args.output_dir,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.lr,
        lr_scheduler_type="cosine",
        warmup_ratio=0.03,
        num_train_epochs=args.epochs,
        logging_steps=10,
        save_strategy="steps",
        save_steps=args.save_steps,
        save_total_limit=2,
        fp16=not torch.cuda.is_bf16_supported(),
        bf16=torch.cuda.is_bf16_supported(),
        optim="paged_adamw_8bit",
        report_to="none",
    )

    try:
        trainer = SFTTrainer(
            model=model,
            tokenizer=tokenizer,
            train_dataset=formatted_dataset,
            dataset_text_field="text",
            max_seq_length=args.max_seq_length,
            dataset_num_proc=4,
            packing=False,
            args=training_args,
        )
    except TypeError:
        # Compatibility with newest trl versions where tokenizer is renamed to processing_class
        trainer = SFTTrainer(
            model=model,
            processing_class=tokenizer,
            train_dataset=formatted_dataset,
            dataset_text_field="text",
            max_seq_length=args.max_seq_length,
            dataset_num_proc=4,
            packing=False,
            args=training_args,
        )

    print("\n" + "=" * 80)
    print("                    STARTING QLoRA TRAINING")
    print("=" * 80)
    print(f" • Base Model:             {args.base_model}")
    print(f" • Records to Train:       {len(formatted_dataset):,}")
    print(f" • Epochs:                 {args.epochs}")
    print(f" • Effective Batch Size:   {args.batch_size * args.grad_accum}")
    print(f" • LoRA Rank / Alpha:      r={args.lora_rank}, alpha={args.lora_alpha}")
    print(f" • Output Directory:       {args.output_dir}")
    print("=" * 80 + "\n")

    start_time = time.time()
    trainer.train()
    elapsed = time.time() - start_time

    print("\n" + "=" * 80)
    print("                     TRAINING COMPLETED!")
    print("=" * 80)
    print(f" • Time Elapsed:           {elapsed / 60:.2f} minutes")
    print(f" • Saving LoRA Adapter to: {args.output_dir}...")
    model.save_pretrained(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)
    print("✅ Adapter and Tokenizer successfully saved!")
    print("=" * 80)
    print("\nNext Step: Run 'python training/export_gguf.py' to convert into an Ollama-compatible GGUF model!")


if __name__ == "__main__":
    train()
