#!/usr/bin/env python3
"""
NirmanAI - Fine-Tuned Model Inference Test Script
=================================================
Runs an immediate test inference using the trained LoRA adapter
to verify that the model outputs the complete NirmanAI System Design Dossier.

Usage:
  python training/test_model.py
  python training/test_model.py --prompt "Design a real-time food delivery backend for 25M users on AWS"
"""

import argparse
import sys
import torch

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig


def parse_args():
    parser = argparse.ArgumentParser(description="Test NirmanAI fine-tuned model")
    parser.add_argument(
        "--adapter_dir",
        type=str,
        default="./nirmanai_adapter",
        help="Path to saved LoRA adapter",
    )
    parser.add_argument(
        "--base_model",
        type=str,
        default="unsloth/Qwen2.5-7B-Instruct-bnb-4bit",
        help="Base model ID",
    )
    parser.add_argument(
        "--prompt",
        type=str,
        default="Design a distributed real-time ride-sharing dispatch system like Uber for 10M active drivers and riders.",
        help="Test prompt",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    print("=" * 80)
    print("                NIRMAN-AI : FINE-TUNED MODEL TEST SUITE")
    print("=" * 80)

    print(f"Loading Base Model: {args.base_model}...")
    tokenizer = AutoTokenizer.from_pretrained(args.adapter_dir, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    if "bnb-4bit" in args.base_model:
        base_model = AutoModelForCausalLM.from_pretrained(
            args.base_model,
            device_map="auto",
            trust_remote_code=True,
        )
    else:
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16,
        )
        base_model = AutoModelForCausalLM.from_pretrained(
            args.base_model,
            quantization_config=bnb_config,
            device_map="auto",
            trust_remote_code=True,
        )

    print(f"Loading Trained LoRA Adapter from: {args.adapter_dir}...")
    model = PeftModel.from_pretrained(base_model, args.adapter_dir)
    model.eval()

    instruction = (
        "You are NirmanAI, an autonomous distributed systems architect. "
        "Analyze the user's requirements and produce a production-grade, highly scalable system architecture dossier "
        "including system overview, capacity planning calculations, visual Mermaid diagram, component breakdown, "
        "architectural trade-offs, and bottleneck mitigation strategies."
    )

    messages = [
        {"role": "system", "content": instruction},
        {"role": "user", "content": args.prompt},
    ]

    prompt_text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(prompt_text, return_tensors="pt").to(model.device)

    print(f"\nPrompt: {args.prompt}\n")
    print("Generating System Architecture Dossier...\n")
    print("-" * 80)

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=1500,
            temperature=0.2,
            top_p=0.9,
            repetition_penalty=1.05,
            do_sample=True,
        )

    # Decode only the generated part
    generated_tokens = outputs[0][len(inputs["input_ids"][0]):]
    result_text = tokenizer.decode(generated_tokens, skip_special_tokens=True)

    print(result_text)
    print("-" * 80)
    print("✅ Model inference successfully verified!")
    print("=" * 80)


if __name__ == "__main__":
    main()
