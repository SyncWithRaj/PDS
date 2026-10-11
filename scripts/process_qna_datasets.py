"""
NirmanAI - QnA Dataset Processor
==================================
Extracts instruction/input/output records from:
  1. system-design-interview  (./system-design-interview/**/*.md)
  2. architecture-decision-record  (./architecture-decision-record/**/*.md)
  3. system-design-primer (./system-design-primer/README.md)

Outputs: datasets/qna_combined.jsonl
"""

import os
import glob
import json
import re
import hashlib
from collections import defaultdict

# ─── Constants ────────────────────────────────────────────────────────────────
MIN_WORDS          = 20          # minimum words for SDI and ADR
PRIMER_MIN_WORDS   = 15          # minimum words for primer
SDI_DIR            = r"C:\Users\DELL\Desktop\NirmanAI\system-design-interview"
ADR_DIR            = r"C:\Users\DELL\Desktop\NirmanAI\architecture-decision-record"
PRIMER_FILE        = r"C:\Users\DELL\Desktop\NirmanAI\system-design-primer\README.md"
OUTPUT_FILE        = r"C:\Users\DELL\Desktop\NirmanAI\datasets\qna_combined.jsonl"

ADR_SECTIONS = [
    "context", "background", "decision", "considerations",
    "consequences", "status", "rationale", "alternatives",
    "pros and cons", "ownership", "review", "notes",
]

SKIP_FILES = {"license.md", "code_of_conduct.md", "agents.md",
              "contributing.md", "changelog.md"}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def clean_markdown(text: str) -> str:
    """Strip HTML, badges, image links, frontmatter, tracker noise."""
    text = re.sub(r"^---[\s\S]*?---\n", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\+\+\+[\s\S]*?\+\+\+\n", "", text, flags=re.MULTILINE)
    text = re.sub(r"\[!\[.*?\]\(.*?\)\]\(.*?\)", "", text)
    text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\[[ xX]\]", "", text)
    text = re.sub(r"^[-*_]{3,}\s*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def word_count(text: str) -> int:
    return len(text.split())


def md5(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def make_record(instruction, input_text, output_text, source):
    return {
        "instruction": instruction,
        "input": input_text.strip(),
        "output": output_text.strip(),
        "source": source,
    }


# ─── System Design Primer extractor ───────────────────────────────────────────

def process_primer_file(file_path: str) -> list[dict]:
    records = []
    if not os.path.exists(file_path):
        return records

    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        raw = f.read()

    content = clean_markdown(raw)

    heading_pattern = re.compile(r"(?m)^(#{2,3})\s+(.+?)$")
    matches = list(heading_pattern.finditer(content))

    if matches:
        for i, m in enumerate(matches):
            heading = m.group(2).strip()

            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
            body = content[start:end].strip()

            if word_count(body) >= PRIMER_MIN_WORDS:
                records.append(make_record(
                    instruction="Explain the following system design principle or component.",
                    input_text=heading,
                    output_text=body,
                    source="system_design_primer",
                ))

    return records


# ─── System Design Interview extractor ────────────────────────────────────────

def process_sdi_file(file_path: str) -> list[dict]:
    records = []
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        raw = f.read()
    content = clean_markdown(raw)

    heading_pattern = re.compile(r"(?m)^(#{1,3})\s+(.+?)$")
    matches = list(heading_pattern.finditer(content))

    if matches:
        for i, m in enumerate(matches):
            heading = m.group(2).strip()
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
            body = content[start:end].strip()
            if word_count(body) >= MIN_WORDS:
                records.append(make_record(
                    instruction="Provide a detailed system design explanation for the following architecture topic.",
                    input_text=heading,
                    output_text=body,
                    source="system_design_interview",
                ))

    paragraphs = [p.strip() for p in re.split(r"\n\n+", content) if p.strip()]
    for para in paragraphs:
        lines = para.splitlines()
        if all(ln.startswith(("*", "-", "+", "#", ">")) for ln in lines if ln.strip()):
            continue
        if word_count(para) < MIN_WORDS:
            continue
        first_sentence = re.split(r"(?<=[.!?])\s", para, maxsplit=1)[0].strip()
        if len(first_sentence) < 10:
            continue
        records.append(make_record(
            instruction="Explain the following system design concept in detail.",
            input_text=first_sentence,
            output_text=para,
            source="system_design_interview",
        ))

    if not records and word_count(content) >= MIN_WORDS:
        file_name = os.path.splitext(os.path.basename(file_path))[0].replace("-", " ").title()
        records.append(make_record(
            instruction="Provide a comprehensive system design overview for the following topic.",
            input_text=file_name,
            output_text=content,
            source="system_design_interview",
        ))

    return records


# ─── Architecture Decision Record extractor ───────────────────────────────────

def process_adr_file(file_path: str) -> list[dict]:
    records = []
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        raw = f.read()
    content = clean_markdown(raw)

    title_m = re.search(r"^#\s+(.+)", content, re.MULTILINE)
    title = title_m.group(1).strip() if title_m else \
        os.path.splitext(os.path.basename(file_path))[0].replace("-", " ").title()

    section_pattern = re.compile(
        r"(?m)^#{1,3}\s+(" + "|".join(ADR_SECTIONS) + r")\s*$",
        re.IGNORECASE,
    )
    section_matches = list(section_pattern.finditer(content))

    captured_sections = {}
    if section_matches:
        for i, m in enumerate(section_matches):
            sec_name = m.group(1).strip().lower()
            start = m.end()
            end = section_matches[i + 1].start() if i + 1 < len(section_matches) else len(content)
            body = content[start:end].strip()
            if body:
                captured_sections[sec_name] = body

    if captured_sections:
        output_parts = []
        for sec in ADR_SECTIONS:
            if sec in captured_sections:
                output_parts.append(f"{sec.title()}:\n{captured_sections[sec]}")

        combined_output = "\n\n".join(output_parts)
        if word_count(combined_output) >= MIN_WORDS:
            records.append(make_record(
                instruction="Analyze the architectural context and provide a structured decision record with rationale and consequences.",
                input_text=f"Architectural decision regarding: {title}",
                output_text=combined_output,
                source="architecture_decision_record",
            ))

        for sec_name, body in captured_sections.items():
            if word_count(body) >= MIN_WORDS:
                records.append(make_record(
                    instruction=f"Explain the '{sec_name}' section of the following architecture decision.",
                    input_text=f"{title} — {sec_name.title()}",
                    output_text=body,
                    source="architecture_decision_record",
                ))

    if not captured_sections and word_count(content) >= MIN_WORDS:
        records.append(make_record(
            instruction="Analyze this architecture decision record and extract the key design rationale.",
            input_text=f"Architecture Decision Record: {title}",
            output_text=content,
            source="architecture_decision_record",
        ))

    return records


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    new_records: list[dict] = []

    # 1. Process Primer
    print(f"Processing Primer file: {PRIMER_FILE}")
    new_records.extend(process_primer_file(PRIMER_FILE))

    # ── Load Existing Records to ensure we append and dedup ──
    seen_hashes: set[str] = set()
    counts: dict[str, int] = defaultdict(int)
    
    # We will rewrite the whole file with existing + new deduplicated records.
    # If the file exists, load it first.
    existing_records = []
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        record = json.loads(line)
                        h = md5(record["input"] + record["output"])
                        if h not in seen_hashes:
                            seen_hashes.add(h)
                            existing_records.append(record)
                            counts[record.get("source", "unknown")] += 1
                    except json.JSONDecodeError:
                        pass
        print(f"Loaded {len(existing_records)} existing records from {OUTPUT_FILE}")

    # Process SDI and ADR if they are not already fully in there?
    # Actually, the user asked to append these primer records. 
    # But just in case, let's process SDI and ADR too and just deduplicate everything, 
    # which has the same effect as appending new ones, but guarantees consistency.
    sdi_files = glob.glob(os.path.join(SDI_DIR, "**", "*.md"), recursive=True)
    for fp in sdi_files:
        if os.path.basename(fp).lower() not in SKIP_FILES:
            new_records.extend(process_sdi_file(fp))

    adr_files = glob.glob(os.path.join(ADR_DIR, "**", "*.md"), recursive=True)
    for fp in adr_files:
        if os.path.basename(fp).lower() not in SKIP_FILES:
            new_records.extend(process_adr_file(fp))

    # Deduplicate new records against existing
    appended_records = []
    for r in new_records:
        h = md5(r["input"] + r["output"])
        if h not in seen_hashes:
            seen_hashes.add(h)
            appended_records.append(r)
            counts[r["source"]] += 1

    # Append to file
    if appended_records:
        os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
        with open(OUTPUT_FILE, "a", encoding="utf-8") as out:
            for r in appended_records:
                out.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"Appended {len(appended_records)} new records.")
    else:
        print("No new records to append (all duplicates).")

    # ── Summary ──
    print(f"\nDataset updated → {OUTPUT_FILE}")
    print("─" * 40)
    print("Total Records per source:")
    total = 0
    for src, cnt in sorted(counts.items()):
        print(f"  {src}: {cnt:,}")
        total += cnt
    print("─" * 40)
    print(f"  OVERALL TOTAL: {total:,} records")


if __name__ == "__main__":
    main()
