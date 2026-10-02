"""
NirmanAI - E2E Test: Full Agentic Pipeline
===========================================
Tests the complete agentic pipeline end-to-end:
  Enhancer (ReAct) → Analyzer (ReAct) → Estimator (ReAct) →
  Generator (ReAct) → Expert Panel (3 experts) → Synthesizer
"""

import sys
import os
import logging
import time

# Setup
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ.setdefault("GENERATOR_ENGINE", "gemini")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger("e2e_test")

if __name__ == "__main__":
    start_time = time.time()
    logger.info("=" * 70)
    logger.info("🚀 NirmanAI FULL AGENTIC E2E TEST")
    logger.info("=" * 70)

    from nirman.workflow.graph import NirmanWorkflow

    # Test prompt
    prompt = "Build me a LegalTrace app — an AI-powered legal case research and document management platform"

    logger.info(f"Prompt: {prompt}")
    logger.info("-" * 70)

    workflow = NirmanWorkflow(output_dir="output/e2e_agentic_test")
    result = workflow.run(prompt, max_iterations=1)

    elapsed = time.time() - start_time

    logger.info("=" * 70)
    logger.info(f"⏱️ Total pipeline time: {elapsed:.1f}s ({elapsed/60:.1f} min)")

    if result.get("error"):
        logger.error(f"❌ Pipeline error: {result['error']}")
    else:
        logger.info("✅ Pipeline completed successfully!")

    # Print summary
    if result.get("spec"):
        spec = result["spec"]
        logger.info(f"  Domain: {spec.domain.value}")
        logger.info(f"  DAU: {spec.target_dau:,}")
        logger.info(f"  FRs: {len(spec.functional_requirements)}")
        logger.info(f"  NFRs: {len(spec.non_functional_requirements)}")

    if result.get("architecture"):
        arch = result["architecture"]
        logger.info(f"  Components: {len(arch.components)}")
        logger.info(f"  Connections: {len(arch.connections)}")
        logger.info(f"  Trade-offs: {len(arch.trade_offs)}")

    if result.get("scorecard"):
        sc = result["scorecard"]
        logger.info(f"  Critic Score: {sc.overall_score}/100")

    if result.get("expert_verdict"):
        ev = result["expert_verdict"]
        logger.info(f"  Expert Panel Score: {ev['consensus_score']}/100")
        logger.info(f"  Patches Applied: {len(ev.get('patches', []))}")

    if result.get("saved_files"):
        for fmt, path in result["saved_files"].items():
            logger.info(f"  📄 {fmt.upper()}: {path}")

    logger.info("=" * 70)
