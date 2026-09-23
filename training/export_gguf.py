#!/usr/bin/env python3
"""
NirmanAI - GGUF & Merged Model Exporter
======================================
Merges the fine-tuned LoRA adapter into the base model and exports it
to 4-bit GGUF format for ultra-fast local inference on CPU/RAM via Ollama.

Usage:
  python training/export_gguf.py
  python training/export_gguf.py --quantization q4_k_m --output_file nirmanai-7b.gguf
"""

import argparse
import os
import sys
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description="Export NirmanAI model to GGUF format")
    parser.add_argument(
        "--adapter_dir",
        type=str,
        default="./nirmanai_adapter",
        help="Path to trained LoRA adapter directory",
    )
    parser.add_argument(
        "--output_name",
        type=str,
        default="nirmanai-7b-q4_k_m.gguf",
        help="Target GGUF file name",
    )
    parser.add_argument(
        "--quantization",
        type=str,
        default="q4_k_m",
        help="GGUF quantization level (q4_k_m, q5_k_m, q8_0)",
    )
    return parser.parse_args()


def export():
    args = parse_args()
    print("=" * 80)
    print("                 NIRMAN-AI : GGUF MODEL EXPORTER")
    print("=" * 80)

    adapter_path = Path(args.adapter_dir)
    if not adapter_path.exists():
        print(f"❌ Error: Adapter directory not found at: {adapter_path}")
        print("Please train the model first using 'python training/train_nirmanai.py'.")
        sys.exit(1)

    # Check for Unsloth GGUF export (Fastest)
    try:
        from unsloth import FastLanguageModel
        print("Using Unsloth native GGUF exporter...")
        model, tokenizer = FastLanguageModel.from_pretrained(
            model_name=str(adapter_path),
            max_seq_length=2048,
        )
        print(f"Converting and saving to GGUF ({args.quantization})...")
        model.save_pretrained_gguf(
            "nirmanai_gguf",
            tokenizer,
            quantization_method=args.quantization,
        )
        print(f"\n✅ Successfully exported GGUF model to 'nirmanai_gguf/' directory!")
        print("=" * 80)
        return
    except Exception as e:
        print(f"ℹ️  Unsloth GGUF export skipped ({e}). Using Hugging Face merge approach...")

    # Fallback: Merge LoRA weights into 16-bit model
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    merged_dir = "./nirmanai_merged_16bit"
    print(f"Merging LoRA adapter with base model into '{merged_dir}'...")

    tokenizer = AutoTokenizer.from_pretrained(str(adapter_path), trust_remote_code=True)
    base_model = AutoModelForCausalLM.from_pretrained(
        "Qwen/Qwen2.5-7B-Instruct",
        torch_dtype=torch.float16,
        device_map="auto",
        trust_remote_code=True,
    )

    model = PeftModel.from_pretrained(base_model, str(adapter_path))
    merged_model = model.merge_and_unload()

    print(f"Saving merged 16-bit model to {merged_dir}...")
    merged_model.save_pretrained(merged_dir)
    tokenizer.save_pretrained(merged_dir)
    print("✅ 16-bit model merged and saved!")
    print("\nTo convert to GGUF format with llama.cpp:")
    print(f"  python3 llama.cpp/convert_hf_to_gguf.py {merged_dir} --outfile {args.output_name} --outtype {args.quantization}")
    print("=" * 80)


if __name__ == "__main__":
    export()
