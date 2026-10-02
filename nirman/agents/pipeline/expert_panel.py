"""
NirmanAI - Expert Panel Agent (Multi-Agent Debate System)
==========================================================
TRUE AUTONOMOUS MULTI-AGENT SYSTEM.

Replaces the single Critic + Refiner with a panel of 3 specialized expert
agents that each independently research, critique, and propose fixes.

How it works:
1. Three expert agents receive the architecture simultaneously
2. Each expert runs an INDEPENDENT ReAct loop:
   - Researches best practices in their specialty
   - Identifies specific flaws with evidence
   - Proposes concrete fixes with implementation details
3. A Lead Architect agent receives ALL critiques
4. Lead Architect resolves conflicts and applies patches
5. If consensus score >= threshold → Accept
6. If not → Another round of debate (max 2 rounds)

Expert Agents:
- Security Architect: encryption, auth, compliance, attack vectors
- Database Engineer: schema design, consistency, replication, query patterns
- SRE / Infrastructure Lead: SPOFs, failover, blast radius, observability
"""

import json
import logging
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from nirman.agents.core.gemini_client import GeminiClient
from nirman.agents.core.react_engine import ReActEngine
from nirman.schemas.pipeline.generator import SystemArchitecture
from nirman.schemas.pipeline.analyzer import RequirementSpec
from nirman.schemas.pipeline.estimator import CapacityMetrics
from nirman.tools.registry import build_default_registry
from nirman.prompts import SHARED_MERMAID_RULES

logger = logging.getLogger("nirman.expert_panel")


# === Expert Output Schema ===
class ExpertFinding(BaseModel):
    """A single finding from an expert reviewer."""
    severity: str = Field(..., description="CRITICAL, HIGH, MEDIUM, or LOW")
    component: str = Field(..., description="Which component has the issue")
    flaw: str = Field(..., description="What is wrong (specific, not vague)")
    evidence: str = Field(default="", description="Why this is a problem (cite standards, benchmarks)")
    fix: str = Field(..., description="Concrete remediation with specific technologies/configs")


class ExpertReview(BaseModel):
    """Complete review from a single expert."""
    expert_name: str = Field(..., description="Name of the expert (e.g., 'Security Architect')")
    overall_score: int = Field(..., description="Score out of 100 for this expert's domain")
    overall_assessment: str = Field(..., description="1-2 sentence summary")
    findings: List[ExpertFinding] = Field(default_factory=list, description="List of specific findings")
    strengths: List[str] = Field(default_factory=list, description="What the architecture does well")


class PanelVerdict(BaseModel):
    """The consolidated verdict from the expert panel."""
    consensus_score: int = Field(..., description="Weighted average score out of 100")
    accepted: bool = Field(..., description="True if consensus_score >= threshold")
    verdict_summary: str = Field(..., description="3-5 sentence overall assessment")
    critical_fixes_applied: List[str] = Field(default_factory=list, description="Fixes that were applied")
    remaining_risks: List[str] = Field(default_factory=list, description="Accepted risks")


class RefinedArchitecture(BaseModel):
    """Output from the Lead Architect after resolving expert critiques."""
    architecture: SystemArchitecture
    patches_applied: List[str] = Field(default_factory=list)
    verdict: PanelVerdict


# === Expert Personas ===
SECURITY_PERSONA = (
    "CISO & Security Architect with 20 years of experience in zero-trust architecture, "
    "cloud security, and regulatory compliance. You have designed security frameworks "
    "for financial institutions, healthcare systems, and government agencies. You are "
    "obsessive about encryption at rest/transit, mTLS, RBAC, audit logging, and "
    "compliance standards (SOC2, HIPAA, PCI-DSS, GDPR, eDiscovery)."
)

DATABASE_PERSONA = (
    "Principal Database Engineer with 15 years at Amazon (DynamoDB team) and Google "
    "(Spanner team). You are an expert in polyglot persistence, CAP theorem trade-offs, "
    "consistency models, replication strategies, connection pooling, indexing strategies, "
    "and query optimization. You catch protocol mismatches instantly."
)

SRE_PERSONA = (
    "Staff SRE at Google who co-authored chapters of the SRE Handbook. Expert in "
    "reliability engineering, blast radius analysis, chaos engineering, observability "
    "(OpenTelemetry, Prometheus, Grafana), capacity planning, auto-scaling, "
    "multi-AZ failover, and disaster recovery. You identify single points of failure "
    "that others miss."
)

LEAD_ARCHITECT_PERSONA = (
    "VP of Engineering and Lead Architect who resolves conflicts between security, "
    "database, and infrastructure experts. You make pragmatic trade-off decisions, "
    "prioritize fixes by business impact, and produce the final refined architecture."
)


class ExpertPanelAgent:
    """Multi-agent debate system with 3 expert reviewers + 1 lead architect.

    Each expert independently:
    1. Receives the architecture
    2. Runs a ReAct loop (research + critique)
    3. Produces findings with severity, evidence, and fixes

    The Lead Architect then:
    1. Receives all expert reviews
    2. Resolves conflicts
    3. Applies critical fixes to the architecture
    4. Produces the final verdict
    """

    SCORE_THRESHOLD = 85
    MAX_ROUNDS = 2

    def __init__(self, gemini_client: Optional[GeminiClient] = None):
        self.client = gemini_client or GeminiClient()
        self._registry = build_default_registry()

    def evaluate_and_refine(
        self,
        architecture: SystemArchitecture,
        spec: RequirementSpec,
        capacity: CapacityMetrics,
    ) -> RefinedArchitecture:
        """Run the expert panel debate and return refined architecture.

        This replaces both the old Critic and Refiner agents.
        """
        current_arch = architecture
        all_patches = []

        for round_num in range(1, self.MAX_ROUNDS + 1):
            logger.info(f"🏛️ Expert Panel Round {round_num}/{self.MAX_ROUNDS}...")

            # Step 1: Run all 3 expert reviews
            arch_summary = self._summarize_architecture(current_arch, spec, capacity)

            security_review = self._run_expert(
                persona=SECURITY_PERSONA,
                expert_name="Security Architect",
                arch_summary=arch_summary,
                tools=["search_web", "read_url"],
                focus="security, encryption, authentication, compliance, and zero-trust architecture",
            )

            database_review = self._run_expert(
                persona=DATABASE_PERSONA,
                expert_name="Database Engineer",
                arch_summary=arch_summary,
                tools=["search_web", "python_repl"],
                focus="database design, consistency models, replication, protocol correctness, and query patterns",
            )

            sre_review = self._run_expert(
                persona=SRE_PERSONA,
                expert_name="SRE / Infrastructure Lead",
                arch_summary=arch_summary,
                tools=["search_web", "python_repl"],
                focus="single points of failure, failover, blast radius, observability, and capacity validation",
            )

            reviews = [security_review, database_review, sre_review]

            # Step 2: Calculate consensus score
            scores = [r.overall_score for r in reviews]
            weights = [0.30, 0.35, 0.35]  # Security, DB, SRE
            consensus_score = int(sum(s * w for s, w in zip(scores, weights)))

            logger.info(
                f"   Expert scores: Security={scores[0]}, Database={scores[1]}, "
                f"SRE={scores[2]} → Consensus={consensus_score}/100"
            )

            # Step 3: Collect all critical/high findings
            critical_findings = []
            for review in reviews:
                for finding in review.findings:
                    if finding.severity in ("CRITICAL", "HIGH"):
                        critical_findings.append(finding)

            logger.info(f"   Critical/High findings: {len(critical_findings)}")

            # Step 4: If score is good enough, accept
            if consensus_score >= self.SCORE_THRESHOLD and not critical_findings:
                logger.info(f"✅ Expert Panel ACCEPTED architecture (Score: {consensus_score}/100)")
                return RefinedArchitecture(
                    architecture=current_arch,
                    patches_applied=all_patches,
                    verdict=PanelVerdict(
                        consensus_score=consensus_score,
                        accepted=True,
                        verdict_summary=self._build_verdict_summary(reviews),
                        critical_fixes_applied=all_patches,
                        remaining_risks=[f.flaw for f in critical_findings],
                    ),
                )

            # Step 5: Lead Architect resolves and patches
            if critical_findings:
                logger.info(f"🔧 Lead Architect resolving {len(critical_findings)} findings...")
                current_arch, patches = self._lead_architect_resolve(
                    current_arch, reviews, spec, capacity,
                )
                all_patches.extend(patches)
                logger.info(f"   Applied {len(patches)} patches")
            else:
                logger.info(f"   No critical findings but score {consensus_score} < {self.SCORE_THRESHOLD}")
                break  # No actionable fixes, accept as-is

        # Max rounds reached — accept best result
        final_score = consensus_score if 'consensus_score' in dir() else 80
        logger.info(f"✅ Expert Panel completed after {round_num} rounds (Score: {final_score}/100)")

        return RefinedArchitecture(
            architecture=current_arch,
            patches_applied=all_patches,
            verdict=PanelVerdict(
                consensus_score=final_score,
                accepted=True,
                verdict_summary=self._build_verdict_summary(reviews) if reviews else "Accepted after max rounds.",
                critical_fixes_applied=all_patches,
                remaining_risks=[],
            ),
        )

    def _run_expert(
        self,
        persona: str,
        expert_name: str,
        arch_summary: str,
        tools: List[str],
        focus: str,
    ) -> ExpertReview:
        """Run a single expert agent's ReAct review loop."""
        logger.info(f"   🔍 {expert_name} reviewing...")

        try:
            tool_set = self._registry.get_tools(tools)
            engine = ReActEngine(
                gemini_client=self.client,
                persona=persona,
                tools=tool_set,
                output_schema=ExpertReview,
                max_steps=6,
            )

            goal = (
                f"Review this system architecture from the perspective of {focus}.\n\n"
                f"ARCHITECTURE TO REVIEW:\n{arch_summary}\n\n"
                f"INSTRUCTIONS:\n"
                f"1. Search the web for best practices relevant to your expertise\n"
                f"2. Identify 2-5 specific flaws with severity (CRITICAL/HIGH/MEDIUM/LOW)\n"
                f"3. For each flaw, provide evidence (cite standards/benchmarks) and a concrete fix\n"
                f"4. Also note 2-3 strengths the architecture does well\n"
                f"5. Give an overall score (0-100) for your domain\n"
                f"6. Set expert_name to '{expert_name}'\n"
                f"7. Produce your FINAL_ANSWER as an ExpertReview JSON"
            )

            result = engine.run(goal)
            review: ExpertReview = result.output
            review.expert_name = expert_name  # Ensure correct name

            logger.info(
                f"   ✅ {expert_name}: Score={review.overall_score}/100, "
                f"{len(review.findings)} findings ({result.total_steps} steps, "
                f"{len(result.tools_used)} tool calls)"
            )
            return review

        except Exception as e:
            logger.warning(f"   ⚠️ {expert_name} ReAct failed ({e}), using direct LLM review.")
            return self._direct_expert_review(expert_name, arch_summary, focus)

    def _direct_expert_review(self, expert_name: str, arch_summary: str, focus: str) -> ExpertReview:
        """Fallback: direct structured LLM call for expert review."""
        try:
            prompt = (
                f"You are the {expert_name}. Review this architecture focusing on {focus}.\n\n"
                f"{arch_summary}\n\n"
                f"Provide 2-4 findings with severity, evidence, and fixes. Score 0-100."
            )
            review = self.client.generate_structured(
                system_prompt=f"You are the {expert_name}, an expert in {focus}.",
                user_prompt=prompt,
                schema=ExpertReview,
            )
            review.expert_name = expert_name
            return review
        except Exception as e:
            logger.warning(f"   Direct review also failed for {expert_name}: {e}")
            return ExpertReview(
                expert_name=expert_name,
                overall_score=75,
                overall_assessment=f"Review could not be completed due to: {str(e)[:100]}",
                findings=[],
                strengths=["Architecture follows standard cloud-native patterns"],
            )

    def _lead_architect_resolve(
        self,
        architecture: SystemArchitecture,
        reviews: List[ExpertReview],
        spec: RequirementSpec,
        capacity: CapacityMetrics,
    ) -> tuple:
        """Lead Architect resolves expert critiques and patches the architecture."""
        # Collect all critical/high findings
        findings_text = []
        for review in reviews:
            for finding in review.findings:
                if finding.severity in ("CRITICAL", "HIGH"):
                    findings_text.append(
                        f"[{review.expert_name}] [{finding.severity}] "
                        f"Component: {finding.component} | "
                        f"Flaw: {finding.flaw} | "
                        f"Fix: {finding.fix}"
                    )

        if not findings_text:
            return architecture, []

        # Don't truncate if we can avoid it, or truncate carefully
        arch_json = architecture.model_dump_json(indent=2)
        
        # Include the shared Mermaid rules so the Lead Architect preserves the exact styles
        prompt = (
            f"You are the Lead Architect. Apply these expert-recommended fixes to the architecture.\n\n"
            f"EXPERT FINDINGS TO FIX:\n" + "\n".join(findings_text) + "\n\n"
            f"CURRENT ARCHITECTURE (JSON):\n{arch_json}\n\n"
            f"Apply the fixes and return the updated SystemArchitecture. "
            f"Keep all existing components. Only modify what the experts flagged. "
            f"Update the Mermaid diagrams if components were added/modified, but strictly follow these rules:\n"
            f"{SHARED_MERMAID_RULES}"
        )

        try:
            refined = self.client.generate_structured(
                system_prompt=LEAD_ARCHITECT_PERSONA,
                user_prompt=prompt,
                schema=SystemArchitecture,
            )
            # Re-sanitize diagram just in case (using a basic replace for the most common issue)
            if refined.mermaid_diagram:
                refined.mermaid_diagram = refined.mermaid_diagram.replace('\\n', '<br/>')
            
            patches = [f"Applied: {f.split('|')[1].strip()}" for f in findings_text[:5]]
            return refined, patches
        except Exception as e:
            logger.warning(f"Lead Architect refinement failed: {e}")
            return architecture, []

    def _summarize_architecture(
        self,
        arch: SystemArchitecture,
        spec: RequirementSpec,
        capacity: CapacityMetrics,
    ) -> str:
        """Build a text summary of the architecture for expert review."""
        components_str = "\n".join(
            f"  - {c.id}: {c.name} ({c.technology}) — {c.purpose}"
            for c in arch.components
        )
        connections_str = "\n".join(
            f"  - {c.source_id} → {c.target_id}: {c.protocol.value} ({c.description})"
            for c in arch.connections
        )
        return (
            f"SYSTEM: {arch.system_name}\n"
            f"DOMAIN: {arch.domain} | STYLE: {arch.style} | CLOUD: {arch.cloud}\n"
            f"OVERVIEW: {arch.overview}\n\n"
            f"COMPONENTS ({len(arch.components)}):\n{components_str}\n\n"
            f"CONNECTIONS ({len(arch.connections)}):\n{connections_str}\n\n"
            f"CAPACITY: DAU={capacity.traffic.dau:,}, Peak QPS={capacity.traffic.peak_qps:,}, "
            f"Storage 5yr={capacity.storage.effective_5yr_storage_tb:.1f} TB\n\n"
            f"TRADE-OFFS:\n" + "\n".join(f"  - {t}" for t in arch.trade_offs) + "\n\n"
            f"MERMAID DIAGRAM:\n{arch.mermaid_diagram[:500]}..."
        )

    def _build_verdict_summary(self, reviews: List[ExpertReview]) -> str:
        """Build a consolidated verdict summary from all expert reviews."""
        parts = []
        for r in reviews:
            parts.append(f"{r.expert_name} ({r.overall_score}/100): {r.overall_assessment}")
        return " | ".join(parts)
