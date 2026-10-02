"""
NirmanAI - Architecture Critic Agent (Gemini LLM)
=================================================
Real LLM reasoning agent acting as Senior Principal Staff Architecture Auditor & Chaos Engineer:
- Rigorously stress-tests candidate architectures against the 8-Pillar Rubric
- Detects Single Points of Failure (SPOFs) and cascading failure modes
- Formulates actionable deficiency findings for the Refinement Agent
- Awards calibrated 0-100 pillar scores and composite weighted verdict
"""

import os
import json
import logging
from typing import Optional, List
from pydantic import BaseModel, Field

from nirman.schemas.pipeline.analyzer import RequirementSpec
from nirman.schemas.pipeline.estimator import CapacityMetrics
from nirman.schemas.pipeline.generator import SystemArchitecture
from nirman.schemas.legacy.critic import (
    CriticScorecard,
    EvaluationPillar,
    VulnerabilitySeverity,
    DeficiencyFinding,
    PillarScore,
)
from nirman.agents.core.gemini_client import GeminiClient

logger = logging.getLogger("nirman.critic")

CRITIC_SYSTEM_PROMPT = """You are the Senior Principal Staff Architecture Auditor and Chaos Engineer of NirmanAI.
Your role is to ruthlessly stress-test the proposed candidate SystemArchitecture against the 8-Pillar Rubric from the NirmanAI specification.

The 8 Evaluation Pillars and Weights are:
1. Scalability & Throughput (15%): Database sharding, HPA, stateless compute, connection pooling under peak traffic.
2. Latency & Performance SLAs (15%): Async decoupling, CDN caching, cache-aside Redis, sub-10ms read guarantees.
3. Reliability & Fault Tolerance (15%): Single Points of Failure (SPOFs), Multi-AZ failovers, circuit breakers, dead-letter queues.
4. Data Consistency & Integrity (15%): CAP theorem adherence, SAGA patterns, ACID boundaries, replication lag mitigations.
5. Security & Zero Trust (10%): mTLS service mesh, JWT/OIDC authentication at API Gateway, AES-256 at-rest, TLS 1.3 in-transit.
6. Cost & Resource Efficiency (10%): Rightsized clusters, hot/warm/cold storage tiering, avoiding over-engineering.
7. ML & Data Pipeline Rigor (10%): Real-time feature consistency, dynamic batching, model drift monitoring (when ML is present).
8. Requirement Alignment (10%): Verifying every explicit user feature, SLA, and cloud constraint is satisfied.

For each pillar:
- Score from 0 to 100 (where >= 80 is passing).
- Calculate weighted_score = raw_score * weight.
- Provide concrete engineering audit notes.

Scan for Single Points of Failure (SPOF):
- If any component is a single point of failure (e.g. database without Multi-AZ replica, single gateway without redundancy), set spof_detected = True and log an entry in deficiency_log.

Executive Verdict:
- If overall_score >= 85 and spof_detected is False: is_accepted = True.
- Otherwise: is_accepted = False (requires refinement)."""


class ArchitectureCriticAgent:
    """Real LLM Agent that audits the architecture against the 8-pillar rubric.
    
    Agent Capabilities:
    - Error handling with structured retries (up to 3 attempts)
    - Deterministic score recalculation (overrides LLM's arithmetic with correct weighted sum)
    - is_accepted consistency validation (enforces score >= 85 && no SPOF rule)
    - Self-correction (feeds errors back to LLM for re-generation)
    """

    MAX_RETRIES = 3

    # Canonical pillar weights for deterministic recalculation
    PILLAR_WEIGHTS = {
        EvaluationPillar.SCALABILITY: 0.15,
        EvaluationPillar.LATENCY: 0.15,
        EvaluationPillar.RELIABILITY: 0.15,
        EvaluationPillar.CONSISTENCY: 0.15,
        EvaluationPillar.SECURITY: 0.10,
        EvaluationPillar.COST: 0.10,
        EvaluationPillar.ML_RIGOR: 0.10,
        EvaluationPillar.ALIGNMENT: 0.10,
    }

    def __init__(self, gemini_client: Optional[GeminiClient] = None):
        self.client = gemini_client or GeminiClient()

    def _recalculate_scores(self, scorecard: CriticScorecard) -> CriticScorecard:
        """Deterministic score recalculation — overrides LLM's arithmetic with correct values.
        
        This ensures mathematical consistency:
        - weighted_score = raw_score * weight (enforced per pillar)
        - overall_score = sum(weighted_scores) (enforced globally)
        - is_accepted = (overall_score >= 85) AND (not spof_detected)
        """
        recalculated_total = 0.0
        for ps in scorecard.pillar_breakdown:
            # Enforce canonical weight
            canonical_weight = self.PILLAR_WEIGHTS.get(ps.pillar, ps.weight)
            ps.weight = canonical_weight
            # Recalculate weighted score deterministically
            correct_weighted = round(ps.raw_score * canonical_weight, 2)
            if abs(ps.weighted_score - correct_weighted) > 0.5:
                logger.info(
                    f"🔧 Corrected {ps.pillar.name} weighted_score: "
                    f"LLM said {ps.weighted_score}, correct is {correct_weighted}"
                )
            ps.weighted_score = correct_weighted
            ps.passed = ps.raw_score >= 80
            recalculated_total += correct_weighted

        recalculated_total = round(recalculated_total, 2)
        if abs(scorecard.overall_score - recalculated_total) > 5:
            logger.warning(
                f"⚠️ Overriding LLM overall_score: {scorecard.overall_score} → {recalculated_total} "
                f"(diff: {abs(scorecard.overall_score - recalculated_total):.1f})"
            )
        scorecard.overall_score = recalculated_total

        # Enforce acceptance rule consistency
        correct_accepted = (recalculated_total >= 85.0) and (not scorecard.spof_detected)
        if scorecard.is_accepted != correct_accepted:
            logger.info(
                f"🔧 Corrected is_accepted: LLM said {scorecard.is_accepted}, "
                f"correct is {correct_accepted} (score={recalculated_total}, spof={scorecard.spof_detected})"
            )
            scorecard.is_accepted = correct_accepted

        return scorecard

    def _validate_scorecard(self, scorecard: CriticScorecard) -> list[str]:
        """Self-validation: checks scorecard for completeness."""
        issues = []
        if len(scorecard.pillar_breakdown) < 4:
            issues.append(f"Expected at least 4 pillar scores, got {len(scorecard.pillar_breakdown)}")
        if not scorecard.executive_verdict or len(scorecard.executive_verdict) < 10:
            issues.append("executive_verdict is missing or too short")
        if scorecard.overall_score < 0 or scorecard.overall_score > 100:
            issues.append(f"overall_score {scorecard.overall_score} out of valid range [0, 100]")
        return issues

    def audit(
        self,
        spec: RequirementSpec,
        capacity: CapacityMetrics,
        arch: SystemArchitecture,
    ) -> CriticScorecard:
        """Invokes Gemini LLM with retry, deterministic score correction, and self-validation.
        
        Agent loop:
        1. Build audit prompt from architecture
        2. Call LLM for 8-pillar evaluation
        3. Deterministically recalculate scores (override LLM arithmetic)
        4. Validate scorecard completeness
        5. Retry on failure with self-correction
        """
        components_summary = "\n".join([
            f"- [{c.layer.value}] {c.name} ({c.technology}): {c.purpose} (Redundancy: {c.redundancy})"
            for c in arch.components
        ])

        connections_summary = "\n".join([
            f"- {conn.source_id} -> {conn.target_id} via {conn.protocol.value} ({'Sync' if conn.is_synchronous else 'Async'}): {conn.description}"
            for conn in arch.connections
        ])

        base_user_prompt = f"""Audit and stress-test the following candidate system architecture:

Target System: {arch.system_name} ({arch.domain} on {arch.cloud})
Target Scale: {capacity.traffic.dau:,} DAU | Peak Throughput: {capacity.traffic.peak_qps:,} QPS
5-Year Storage Target: {capacity.storage.effective_5yr_storage_tb:.1f} TB
Required Redis Cache RAM: {capacity.cache.cache_memory_ram_gb:.0f} GB

System Overview:
{arch.overview}

Components in Design:
{components_summary}

Inter-Service Connections:
{connections_summary}

Mermaid Flowchart:
```mermaid
{arch.mermaid_diagram}
```

Audit this design against all 8 pillars, detect any single points of failure, log deficiencies, and calculate the composite scorecard."""

        user_prompt = base_user_prompt
        last_error = None

        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                logger.info(f"🔍 Critic audit attempt {attempt}/{self.MAX_RETRIES}...")
                
                scorecard: CriticScorecard = self.client.generate_structured(
                    system_prompt=CRITIC_SYSTEM_PROMPT,
                    user_prompt=user_prompt,
                    schema=CriticScorecard,
                )

                # Deterministic score recalculation — NEVER trust LLM arithmetic
                scorecard = self._recalculate_scores(scorecard)

                # Self-validation
                issues = self._validate_scorecard(scorecard)
                if issues:
                    issues_str = "; ".join(issues)
                    logger.warning(f"⚠️ Critic scorecard validation failed (attempt {attempt}): {issues_str}")
                    if attempt < self.MAX_RETRIES:
                        user_prompt = (
                            f"Your previous audit had these issues: {issues_str}\n\n"
                            f"Please fix these problems and re-audit.\n\n{base_user_prompt}"
                        )
                        continue
                    else:
                        logger.warning("⚠️ Max retries reached. Using last scorecard despite validation issues.")

                logger.info(
                    f"✅ Critic audit completed (attempt {attempt}). "
                    f"Score: {scorecard.overall_score}/100, "
                    f"Accepted: {scorecard.is_accepted}, "
                    f"SPOF: {scorecard.spof_detected}, "
                    f"Deficiencies: {len(scorecard.deficiency_log)}"
                )
                return scorecard

            except Exception as e:
                last_error = e
                logger.error(f"❌ Critic attempt {attempt} failed: {e}")
                if attempt < self.MAX_RETRIES:
                    user_prompt = (
                        f"The previous attempt failed with error: {str(e)}\n\n"
                        f"Please try again.\n\n{base_user_prompt}"
                    )
                    continue

        raise RuntimeError(
            f"ArchitectureCriticAgent failed after {self.MAX_RETRIES} attempts. Last error: {last_error}"
        )


# Alias for backward compatibility
ArchitectureCritic = ArchitectureCriticAgent

