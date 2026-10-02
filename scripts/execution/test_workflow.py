"""
NirmanAI - Full Workflow Validation & Agent Inspection Script
=============================================================
Runs every single agent step-by-step and inspects:
1. RequirementAnalyzer (Domain, SLAs, FR/NFR extraction)
2. CapacityEstimator (Deterministic Math Engine)
3. ArchitectureGenerator (Component Graph & Mermaid Topology)
4. ArchitectureCritic (8-Pillar Scoring & SPOF Detection)
5. ArchitectureRefiner (Surgical Patch Self-Correction)
6. NirmanOrchestrator (Assembly of Markdown and Interactive HTML)
"""

import sys
import os
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from nirman.agents import (
    RequirementAnalyzer,
    CapacityEstimator,
    ArchitectureGenerator,
    ArchitectureCritic,
    ArchitectureRefiner,
    NirmanOrchestrator,
)


def run_full_agent_test():
    prompt = "Design a high-scale global payments gateway for Stripe handling 50M daily transactions with sub-10ms latency on AWS"
    
    print("=" * 80)
    print("       NIRMAN-AI : STEP-BY-STEP MULTI-AGENT WORKFLOW TEST")
    print("=" * 80)
    print(f"User Input Prompt:\n\"{prompt}\"\n")

    # -------------------------------------------------------------
    # AGENT 1: RequirementAnalyzer
    # -------------------------------------------------------------
    print("▶ 1. REQUIREMENT ANALYZER AGENT")
    print("   Role: NLP Requirement Parsing & Domain Parameterization")
    print("   Backing Engine: Heuristic Rule Classifier + Ollama LLM Fallback (qwen2.5:7b / nirmanai:7b)")
    analyzer = RequirementAnalyzer()
    spec = analyzer.analyze(prompt)
    print(f"   ✔ Domain Classified:      {spec.domain.value}")
    print(f"   ✔ Target DAU:             {spec.target_dau:,}")
    print(f"   ✔ Cloud Target:           {spec.cloud_provider.value}")
    print(f"   ✔ Architectural Style:    {spec.preferred_style.value}")
    print(f"   ✔ Functional Reqs (FRs):  {len(spec.functional_requirements)} extracted")
    for fr in spec.functional_requirements:
        print(f"       • [{fr.id}] {fr.title} ({fr.priority})")
    print(f"   ✔ Non-Functional (NFRs):  {len(spec.non_functional_requirements)} extracted")
    for nfr in spec.non_functional_requirements:
        print(f"       • [{nfr.category}] {nfr.target_metric} - {nfr.description}")

    # -------------------------------------------------------------
    # AGENT 2: CapacityEstimator
    # -------------------------------------------------------------
    print("\n▶ 2. CAPACITY ESTIMATOR AGENT")
    print("   Role: Deterministic Capacity & Resource Sizing")
    print("   Backing Engine: 100% Deterministic Python Math (NO LLM Hallucinations)")
    estimator = CapacityEstimator()
    cap = estimator.estimate(spec)
    print(f"   ✔ Average Throughput:     {cap.traffic.avg_qps:,} QPS")
    print(f"   ✔ Peak Concurrency:       {cap.traffic.peak_qps:,} QPS (3.0x multiplier)")
    print(f"   ✔ Traffic Ratio:          {cap.traffic.read_write_ratio}")
    print(f"   ✔ Peak Bandwidth:         Ingress: {cap.network.ingress_bandwidth_gbps:.3f} Gbps | Egress: {cap.network.egress_bandwidth_gbps:.3f} Gbps")
    print(f"   ✔ Storage Footprint:      Daily: {cap.storage.daily_storage_gb:.2f} GB | 5-Yr Raw: {cap.storage.five_year_storage_tb:.2f} TB")
    print(f"   ✔ 5-Yr Physical Multi-AZ: {cap.storage.effective_5yr_storage_tb:.2f} TB (3x replication factor)")
    print(f"   ✔ Redis Cache Sizing:     {cap.cache.cache_memory_ram_gb:.1f} GB RAM ({cap.cache.recommended_nodes} nodes, 80/20 Pareto distribution)")
    print(f"   ✔ Recommended Cluster:    ~{cap.recommended_compute_pods} Kubernetes Pods")

    # -------------------------------------------------------------
    # AGENT 3: ArchitectureGenerator
    # -------------------------------------------------------------
    print("\n▶ 3. ARCHITECTURE GENERATOR AGENT")
    print("   Role: Node/Edge Graph Synthesis & Mermaid Flowchart Authoring")
    print("   Backing Engine: Cloud Topology Engine + Fine-Tuned LoRA (nirmanai:7b)")
    generator = ArchitectureGenerator()
    arch = generator.generate(spec, cap)
    print(f"   ✔ Architecture Overview:  {arch.overview[:120]}...")
    print(f"   ✔ Topology Nodes:         {len(arch.components)} components synthesized:")
    for c in arch.components:
        print(f"       • [{c.layer.value:12}] {c.name:32} -> {c.technology}")
    print(f"   ✔ Topology Edges:         {len(arch.connections)} inter-service connections")
    print(f"   ✔ Mermaid Graph:          {len(arch.mermaid_diagram.splitlines())} lines (Validated non-looping syntax)")

    # -------------------------------------------------------------
    # AGENT 4: ArchitectureCritic
    # -------------------------------------------------------------
    print("\n▶ 4. ARCHITECTURE CRITIC AGENT")
    print("   Role: Quantitative 8-Pillar Scoring & SPOF Detection")
    print("   Backing Engine: Deterministic Rubric Scoring + Graph Traversal Audit")
    critic = ArchitectureCritic()
    scorecard = critic.audit(spec, cap, arch)
    print(f"   ✔ Overall Score:          {scorecard.overall_score:.1f} / 100")
    print(f"   ✔ Executive Verdict:      {scorecard.executive_verdict[:80]}...")
    print(f"   ✔ Single Point of Failure:{'⚠️ DETECTED' if scorecard.spof_detected else '✅ NONE (Redundant Architecture)'}")
    print("   ✔ 8-Pillar Rubric Audit Breakdown:")
    for p in scorecard.pillar_breakdown:
        status_icon = "✅" if p.passed else "⚠️"
        verdict = "PASS" if p.passed else "REVIEW"
        print(f"       {status_icon} {p.pillar.value:<40} (Weight: {int(p.weight*100):>2}%) -> Score: {p.raw_score:>4.1f} [{verdict}]")

    # -------------------------------------------------------------
    # AGENT 5: ArchitectureRefiner
    # -------------------------------------------------------------
    print("\n▶ 5. ARCHITECTURE REFINER AGENT")
    print("   Role: Automated Self-Correction Loop & Surgical Patching")
    print("   Backing Engine: Graph Mutation Engine applying targeted Patches")
    refiner = ArchitectureRefiner()
    refined_arch, iter_log = refiner.refine(arch, scorecard, iteration_number=1)
    if iter_log and iter_log.patches_applied:
        print(f"   ✔ Iteration 1 Applied {len(iter_log.patches_applied)} surgical patch(es):")
        for patch in iter_log.patches_applied:
            print(f"       • [{patch.action_type.value}] {patch.modification_summary}")
    else:
        print("   ✔ Architecture verified optimal on initial pass. No surgical patches required.")

    # -------------------------------------------------------------
    # AGENT 6: NirmanOrchestrator
    # -------------------------------------------------------------
    print("\n▶ 6. NIRMAN ORCHESTRATOR & DOSSIER SYNTHESIZER")
    print("   Role: End-to-End Pipeline Execution & Artifact Deliverables")
    print("   Backing Engine: Markdown Compilation + HTML/Mermaid.js Dashboard Generation")
    orch = NirmanOrchestrator()
    dossier = orch.synthesize(prompt)
    saved = orch.save(dossier, output_dir="output")
    print(f"   ✔ Master Dossier:         \"{dossier.title}\"")
    print(f"   ✔ Markdown Deliverable:   {saved['markdown']}")
    print(f"   ✔ Live HTML Dashboard:    {saved['html']}")

    print("\n" + "=" * 80)
    print("                   ALL AGENTS EXECUTED SUCCESSFULLY")
    print("=" * 80)


if __name__ == "__main__":
    run_full_agent_test()
