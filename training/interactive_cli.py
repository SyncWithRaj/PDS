#!/usr/bin/env python3
"""
NirmanAI - Interactive Model Tester CLI (Live Streaming Enabled)
==============================================================
Interactively test the fine-tuned NirmanAI model with real-time,
word-by-word streaming directly from your GPU, followed by an
automated JSON format and schema verification.

Usage:
  .venv\Scripts\python.exe training/interactive_cli.py
"""

import sys
import json
import torch

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer, TextStreamer
import json_repair

ADAPTER_DIR = "./nirmanai_adapter"
BASE_MODEL = "unsloth/Qwen2.5-7B-Instruct-bnb-4bit"


def load_nirman_model():
    print("=" * 80)
    print("         NIRMAN-AI : LIVE STREAMING INTERACTIVE TEST SUITE")
    print("=" * 80)
    print(f"Loading Base Model: {BASE_MODEL}...")

    tokenizer = AutoTokenizer.from_pretrained(ADAPTER_DIR, trust_remote_code=True)
    base_model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        device_map="auto",
        trust_remote_code=True,
    )

    print(f"Loading LoRA Adapter from: {ADAPTER_DIR}...")
    model = PeftModel.from_pretrained(base_model, ADAPTER_DIR)
    model.eval()
    print("✅ Model loaded successfully into RTX A2000 GPU!\n")
    return model, tokenizer


def run_inference_stream(model, tokenizer, prompt_text, max_tokens=2500):
    instruction = (
        "You are NirmanAI, an autonomous distributed systems architect. "
        "Analyze the user's requirements and produce a production-grade, highly scalable system architecture dossier "
        "including system overview, capacity planning calculations, visual Mermaid diagram, component breakdown, "
        "architectural trade-offs, and bottleneck mitigation strategies."
    )

    messages = [
        {"role": "system", "content": instruction},
        {"role": "user", "content": prompt_text},
    ]

    chat_prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(chat_prompt, return_tensors="pt").to(model.device)

    # Initialize live real-time token streamer
    streamer = TextStreamer(tokenizer, skip_prompt=True, skip_special_tokens=True)

    print("\n" + "=" * 80)
    print("          ⚡ LIVE MODEL OUTPUT STREAM (Word-by-word on GPU)")
    print("=" * 80 + "\n")

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            streamer=streamer,
            max_new_tokens=max_tokens,
            temperature=0.25,
            top_p=0.9,
            repetition_penalty=1.06,
            do_sample=True,
            eos_token_id=tokenizer.eos_token_id,
        )

    generated_tokens = outputs[0][len(inputs["input_ids"][0]):]
    raw_text = tokenizer.decode(generated_tokens, skip_special_tokens=True).strip()
    return raw_text


def process_prompt(model, tokenizer, prompt):
    raw_output = run_inference_stream(model, tokenizer, prompt)

    print("\n" + "=" * 80)
    print("--- 🔍 JSON FORMAT VERIFICATION ---")
    print("=" * 80)
    try:
        clean_text = raw_output
        if "```json" in clean_text:
            clean_text = clean_text.split("```json")[1].split("```")[0].strip()
        elif "```" in clean_text:
            clean_text = clean_text.split("```")[1].split("```")[0].strip()

        # Try standard parsing with strict=False (allows unescaped newlines in Mermaid)
        try:
            parsed = json.loads(clean_text, strict=False)
            parser_used = "json.loads(strict=False)"
        except Exception:
            parsed = json_repair.loads(clean_text)
            parser_used = "json_repair (auto-repaired unescaped quotes/syntax)"

        if isinstance(parsed, dict):
            print(f"✅ VALID JSON: YES! Successfully parsed via {parser_used}")
            print(f"📋 Keys detected in JSON ({len(parsed)} keys):")
            for k, v in parsed.items():
                if isinstance(v, list):
                    print(f"  • {k}: [list with {len(v)} items]")
                elif isinstance(v, dict):
                    print(f"  • {k}: [nested dictionary with {len(v)} sub-keys: {list(v.keys())}]")
                else:
                    summary = str(v).replace('\n', ' ')
                    if len(summary) > 75:
                        summary = summary[:75] + "..."
                    print(f"  • {k}: {summary}")

            if "mermaid_diagram" in parsed:
                print("\n🎨 Mermaid Diagram found in output!")
                lines = parsed["mermaid_diagram"].split("\n")
                print(f"   ↳ {len(lines)} lines of Mermaid syntax generated.")
        else:
            print(f"⚠️  Parsed object is {type(parsed).__name__}, not a dictionary.")

    except Exception as err:
        print(f"❌ VALID JSON: NO ({type(err).__name__}: {err})")
        print("Note: The model might have reached the max token limit before closing all brackets.")
    print("=" * 80)


def main():
    model, tokenizer = load_nirman_model()

    print("-" * 80)
    print("Type your system design scenario below (or type 'quit' / 'exit' to stop).")
    print("Example: Design a real-time chat application like WhatsApp for 100M daily users")
    print("-" * 80 + "\n")

    if len(sys.argv) > 1:
        user_prompt = " ".join(sys.argv[1:])
        process_prompt(model, tokenizer, user_prompt)
        return

    while True:
        try:
            user_prompt = input("\n👉 Enter System Design Prompt: ").strip()
            if not user_prompt:
                continue
            if user_prompt.lower() in ["quit", "exit", "q"]:
                print("Exiting test suite. Goodbye!")
                break

            process_prompt(model, tokenizer, user_prompt)

        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            break


if __name__ == "__main__":
    main()
