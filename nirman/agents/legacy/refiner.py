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

from nirman.schemas.pipeline.generator import SystemArchitecture
from nirman.schemas.legacy.critic import CriticScorecard, DeficiencyFinding
from nirman.schemas.legacy.refiner import (
    SurgicalPatch,
    PatchActionType,
    RefinementIteration,
)
from nirman.agents.core.gemini_client import GeminiClient

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
    """Real LLM Agent that surgically refactors architectures to satisfy the Critic.
    
    Agent Capabilities:
    - Error handling with structured retries (up to 3 attempts)
    - Output validation (checks refined arch has components/diagram)
    - Safe fallback to original architecture on complete failure
    - Self-correction (feeds validation errors back for re-generation)
    """

    MAX_RETRIES = 3

    def __init__(self, gemini_client: Optional[GeminiClient] = None):
        self.client = gemini_client or GeminiClient()

    def _validate_refinement(self, output: RefinementOutput, original: SystemArchitecture) -> list[str]:
        """Self-validation: checks that refinement didn't break the architecture."""
        issues = []
        refined = output.refined_architecture
        if len(refined.components) < 3:
            issues.append(f"Refined arch has only {len(refined.components)} components (minimum 3)")
        if not refined.mermaid_diagram or not refined.mermaid_diagram.strip():
            issues.append("Refined mermaid_diagram is empty")
        if not refined.overview or len(refined.overview) < 20:
            issues.append("Refined overview is missing or too short")
        if len(refined.components) < len(original.components) * 0.5:
            issues.append(
                f"Refined arch lost too many components: {len(refined.components)} vs "
                f"original {len(original.components)} (suspecting context drift)"
            )
        if not output.patches_applied:
            issues.append("No surgical patches were applied")
        return issues

    def refine(
        self,
        arch: SystemArchitecture,
        scorecard: CriticScorecard,
        iteration_number: int = 1,
    ) -> Tuple[SystemArchitecture, Optional[RefinementIteration]]:
        """Invokes Gemini LLM with retry, validation, and safe fallback.
        
        Agent loop:
        1. Check if refinement is needed (skip if already accepted)
        2. Build refinement prompt from deficiency log
        3. Call LLM for surgical patches
        4. Validate output (components, diagram, no context drift)
        5. Retry on failure; fall back to original arch on total failure
        """
        if scorecard.is_accepted and not scorecard.deficiency_log and not scorecard.spof_detected:
            logger.info("✅ Architecture already accepted, skipping refinement.")
            return arch, None

        deficiencies_text = "\n".join([
            f"- [{d.id}] ({d.pillar.value} - {d.severity.value}): {d.flaw_description}\n"
            f"  Target: {d.component_target} | Failure Mode: {d.failure_mode}\n"
            f"  Prescribed Remediation: {d.prescribed_patch}"
            for d in scorecard.deficiency_log
        ])

        base_user_prompt = f"""Refine the following system architecture to resolve all deficiencies identified by the Critic:

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

IMPORTANT: Your refined_architecture MUST retain all existing components that are working well. Only ADD or MODIFY components to fix the deficiencies. Do NOT remove components unless they are explicitly part of a deficiency.

Apply targeted surgical patches to remediate every deficiency, eliminate all SPOFs, and output the refined SystemArchitecture with an updated Mermaid flowchart."""

        user_prompt = base_user_prompt
        last_error = None

        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                logger.info(f"🔧 Refiner attempt {attempt}/{self.MAX_RETRIES} (iteration {iteration_number})...")

                output: RefinementOutput = self.client.generate_structured(
                    system_prompt=REFINER_SYSTEM_PROMPT,
                    user_prompt=user_prompt,
                    schema=RefinementOutput,
                )

                # Self-validation
                issues = self._validate_refinement(output, arch)
                if issues:
                    issues_str = "; ".join(issues)
                    logger.warning(f"⚠️ Refiner output validation failed (attempt {attempt}): {issues_str}")
                    if attempt < self.MAX_RETRIES:
                        user_prompt = (
                            f"Your previous refinement had these issues: {issues_str}\n\n"
                            f"Please fix these problems and re-refine.\n\n{base_user_prompt}"
                        )
                        continue
                    else:
                        logger.warning("⚠️ Max retries reached. Using last output despite validation issues.")

                iteration = RefinementIteration(
                    iteration_number=iteration_number,
                    starting_score=scorecard.overall_score,
                    patches_applied=output.patches_applied,
                    resolved_deficiencies=output.resolved_deficiencies,
                    refinement_summary=output.refinement_summary,
                )

                logger.info(
                    f"✅ Refiner completed (attempt {attempt}). "
                    f"Patches: {len(output.patches_applied)}, "
                    f"Resolved: {len(output.resolved_deficiencies)}"
                )
                return output.refined_architecture, iteration

            except Exception as e:
                last_error = e
                logger.error(f"❌ Refiner attempt {attempt} failed: {e}")
                if attempt < self.MAX_RETRIES:
                    user_prompt = (
                        f"The previous attempt failed with error: {str(e)}\n\n"
                        f"Please try again.\n\n{base_user_prompt}"
                    )
                    continue

        # Safe fallback: return original architecture rather than crashing the pipeline
        logger.error(
            f"⚠️ Refiner failed after {self.MAX_RETRIES} attempts. "
            f"Returning ORIGINAL architecture to prevent pipeline crash. Last error: {last_error}"
        )
        return arch, None


# Alias for backward compatibility
ArchitectureRefiner = ArchitectureRefinerAgent

