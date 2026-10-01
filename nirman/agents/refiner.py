"""
NirmanAI - Architecture Refiner Agent (Gemini LLM)
==================================================
Real LLM reasoning agent acting as System Resilience & Refactoring Specialist:
- Ingests candidate SystemArchitecture and Critic's deficiency_log
- Reasons through surgical mutations to resolve bottlenecks and Single Points of Failure
- Generates categorized SurgicalPatches
- Mutates the component graph and produces updated, valid Mermaid.js flowchart code
"""

import os
import json
import logging
from typing import Optional, List, Tuple
from pydantic import BaseModel, Field

from nirman.schemas.generator import SystemArchitecture
from nirman.schemas.critic import CriticScorecard, DeficiencyFinding
from nirman.schemas.refiner import (
    SurgicalPatch,
    PatchActionType,
    RefinementIteration,
)
from nirman.agents.gemini_client import GeminiClient

logger = logging.getLogger("nirman.refiner")


class RefinementOutput(BaseModel):
    """LLM output model for the Architecture Refiner agent."""
    patches_applied: List[SurgicalPatch] = Field(..., description="Targeted surgical patches applied")
    resolved_deficiencies: List[str] = Field(..., description="IDs of defects addressed (e.g. ['DEF-REL-01'])")
    refinement_summary: str = Field(..., description="Narrative summary of mutations applied")
    refined_architecture: SystemArchitecture = Field(..., description="Updated complete SystemArchitecture with repaired components and Mermaid code")


REFINER_SYSTEM_PROMPT = """You are the System Resilience and Remediation Specialist of NirmanAI.
Your role is to analyze a candidate SystemArchitecture and the Critic's deficiency_log, then surgically refactor the architecture to resolve all identified flaws, single points of failure, and SLA risks.

For each defect in the deficiency log:
1. Determine the appropriate remediation action (e.g. MULTI_AZ_FAILOVER, INTRODUCE_CACHE, DECOUPLE_ASYNC, ADD_API_GATEWAY).
2. Create a SurgicalPatch describing the modification and expected rubric pillar impact.
3. Update the SystemArchitecture:
   - Add missing components (e.g. Redis Cluster, Read Replicas, Kafka Bus, API Gateway).
   - Update component redundancy and scaling parameters.
   - Update inter-service connection edges.
   - Re-write the complete Mermaid.js flowchart to visually incorporate the improvements (ensure valid `flowchart TD` syntax and no loops)."""


class ArchitectureRefinerAgent:
    """Real LLM Agent that surgically refactors architectures to satisfy the Critic."""

    def __init__(self, gemini_client: Optional[GeminiClient] = None):
        self.client = gemini_client or GeminiClient()

    def refine(
        self,
        arch: SystemArchitecture,
        scorecard: CriticScorecard,
        iteration_number: int = 1,
    ) -> Tuple[SystemArchitecture, Optional[RefinementIteration]]:
        """Invokes Gemini LLM to apply surgical patches based on Critic deficiencies."""
        if scorecard.is_accepted and not scorecard.deficiency_log and not scorecard.spof_detected:
            return arch, None

        deficiencies_text = "\n".join([
            f"- [{d.id}] ({d.pillar.value} - {d.severity.value}): {d.flaw_description}\n"
            f"  Target: {d.component_target} | Failure Mode: {d.failure_mode}\n"
            f"  Prescribed Remediation: {d.prescribed_patch}"
            for d in scorecard.deficiency_log
        ])

        user_prompt = f"""Refine the following system architecture to resolve all deficiencies identified by the Critic:

System: {arch.system_name} ({arch.domain} on {arch.cloud})
Current Overall Score: {scorecard.overall_score} / 100
Single Points of Failure Detected: {scorecard.spof_detected}

Deficiencies Identified by Critic:
{deficiencies_text if deficiencies_text else "- General resilience and high availability improvements needed to achieve a score >= 85."}

Current System Overview:
{arch.overview}

Current Components:
{chr(10).join([f"- [{c.layer.value}] {c.name} ({c.technology})" for c in arch.components])}

Current Mermaid Diagram:
```mermaid
{arch.mermaid_diagram}
```

Apply targeted surgical patches to remediate every deficiency, eliminate all SPOFs, and output the refined SystemArchitecture with an updated Mermaid flowchart."""

        output: RefinementOutput = self.client.generate_structured(
            system_prompt=REFINER_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            schema=RefinementOutput,
        )

        iteration = RefinementIteration(
            iteration_number=iteration_number,
            starting_score=scorecard.overall_score,
            patches_applied=output.patches_applied,
            resolved_deficiencies=output.resolved_deficiencies,
            refinement_summary=output.refinement_summary,
        )

        return output.refined_architecture, iteration


# Alias for backward compatibility
ArchitectureRefiner = ArchitectureRefinerAgent
