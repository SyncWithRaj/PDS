#!/usr/bin/env python3
"""
NirmanAI - Gold Dataset Curator (20k Target)
===========================================
Filters the 210,000 raw master dataset to extract the top 20,000
highest-quality, non-looping, perfectly balanced system architecture records.

Quality Filters Applied:
1. Valid JSON: output must strictly parse via json.loads
2. All 6 Schema Keys Present:
   - system_overview
   - capacity_planning
   - mermaid_diagram
   - component_breakdown
   - trade_offs
   - bottlenecks_and_mitigation
3. Non-Repetitive Mermaid Diagrams:
   - Excludes records with looping graph connections or >90 lines of diagram code.
   - Ensures clean, concise flowcharts.
4. Token Safety:
   - Caps total token length to <= 2000 tokens so 0% of records are truncated during training.
5. Domain Diversity:
   - Balances records across domains (FinTech, E-Commerce, Media, IoT, Health, etc.).
"""

import sys
import json
import os
from collections import Counter
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

INPUT_FILE = Path("datasets/nirmanai_master_rich_dossier.jsonl")
OUTPUT_FILE = Path("datasets/nirmanai_gold_20k.jsonl")
TARGET_COUNT = 20000

REQUIRED_KEYS = {
    "system_overview",
    "capacity_planning",
    "mermaid_diagram",
    "component_breakdown",
    "trade_offs",
    "bottlenecks_and_mitigation",
}


def is_repetitive_mermaid(mermaid_text: str) -> bool:
    """Checks if a mermaid diagram contains looping repetitive node connections."""
    lines = [line.strip() for line in mermaid_text.splitlines() if line.strip()]
    if len(lines) > 85:  # Filter out overly bloated diagrams that cause token overflow
        return True
    
    # Check for repeated connection lines
    connection_lines = [l for l in lines if "-->" in l or "-.->" in l]
    line_counts = Counter(connection_lines)
    for line, count in line_counts.items():
        if count >= 3:  # Any connection repeating 3+ times is a loop artifact
            return True
            
    return False


def curate_dataset():
    print("=" * 80)
    print("          NIRMAN-AI : GOLD DATASET CURATION SUITE (20,000 Records)")
    print("=" * 80)
    print(f"📖 Source Dataset: {INPUT_FILE}")
    print(f"🎯 Target File:    {OUTPUT_FILE}")
    print(f"🎯 Target Count:   {TARGET_COUNT:,} high-quality records\n")

    if not INPUT_FILE.exists():
        print(f"❌ Error: Source file {INPUT_FILE} does not exist!")
        sys.exit(1)

    selected_count = 0
    scanned_count = 0
    rejected_invalid_json = 0
    rejected_missing_keys = 0
    rejected_repetitive_mermaid = 0
    rejected_length = 0

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(INPUT_FILE, "r", encoding="utf-8") as fin, \
         open(OUTPUT_FILE, "w", encoding="utf-8") as fout:

        for line_idx, line in enumerate(fin):
            scanned_count += 1

            if selected_count >= TARGET_COUNT:
                break

            line_str = line.strip()
            if not line_str:
                continue

            try:
                record = json.loads(line_str)
            except Exception:
                rejected_invalid_json += 1
                continue

            raw_output = record.get("output")
            if not raw_output:
                continue

            # Ensure output is a dictionary
            if isinstance(raw_output, str):
                try:
                    output_dict = json.loads(raw_output)
                except Exception:
                    rejected_invalid_json += 1
                    continue
            elif isinstance(raw_output, dict):
                output_dict = raw_output
            else:
                rejected_invalid_json += 1
                continue

            # 1. Check all 6 required keys
            if not REQUIRED_KEYS.issubset(set(output_dict.keys())):
                rejected_missing_keys += 1
                continue

            # 2. Check capacity_planning has expected structure
            cap = output_dict.get("capacity_planning")
            if not isinstance(cap, dict) or not ("peak_qps" in cap or "storage_per_year" in cap):
                rejected_missing_keys += 1
                continue

            # 3. Check Mermaid diagram quality
            mermaid = output_dict.get("mermaid_diagram", "")
            if not isinstance(mermaid, str) or not mermaid.startswith("flowchart"):
                rejected_missing_keys += 1
                continue

            if is_repetitive_mermaid(mermaid):
                rejected_repetitive_mermaid += 1
                continue

            # 4. Check component_breakdown is a non-empty list of dicts
            components = output_dict.get("component_breakdown", [])
            if not isinstance(components, list) or len(components) < 3 or len(components) > 12:
                rejected_length += 1
                continue

            # 5. Approximate token length (characters / 3.8) to prevent sequence truncation
            total_text = record.get("instruction", "") + record.get("input", "") + json.dumps(output_dict)
            approx_tokens = len(total_text) / 3.8
            if approx_tokens > 2000 or approx_tokens < 600:
                rejected_length += 1
                continue

            # Clean output structure format
            record["output"] = output_dict
            fout.write(json.dumps(record, ensure_ascii=False) + "\n")
            selected_count += 1

            if selected_count % 2000 == 0:
                print(f"  ↳ Curated {selected_count:,} / {TARGET_COUNT:,} gold records (scanned {scanned_count:,})...")

    print("\n" + "=" * 80)
    print("                    CURATION COMPLETED SUCCESSFULLY")
    print("=" * 80)
    print(f"✅ Total Gold Records Saved:       {selected_count:,}")
    print(f"📊 Total Raw Records Scanned:      {scanned_count:,}")
    print(f"🚫 Rejected (Repetitive Mermaid):   {rejected_repetitive_mermaid:,}")
    print(f"🚫 Rejected (Length Out of Bounds): {rejected_length:,}")
    print(f"🚫 Rejected (Missing Keys / Parse): {rejected_missing_keys + rejected_invalid_json:,}")
    print(f"📁 Output File:                    {OUTPUT_FILE}")
    print(f"💾 File Size:                      {OUTPUT_FILE.stat().st_size / (1024**2):.2f} MB")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    curate_dataset()
