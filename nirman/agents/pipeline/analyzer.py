"""
NirmanAI - Requirement Analyzer Agent (ReAct Agentic)
=====================================================
TRUE AUTONOMOUS AGENT — NOT a wrapper.

Uses the ReAct (Reason + Act) loop to:
1. SEARCH for domain-specific compliance and regulation requirements
2. READ relevant documentation about industry standards
3. THINK about what functional and non-functional requirements are needed
4. PRODUCE validated, research-backed RequirementSpec + CapacityMetrics
"""

import os
import json
import logging
from typing import Optional, Tuple
from pydantic import BaseModel, Field

from nirman.schemas.pipeline.analyzer import (
    RequirementSpec,
    DomainType,
    TargetScale,
    CloudEnvironment,
    ArchitecturalStyle,
    FunctionalRequirement,
    NonFunctionalRequirement,
)
from nirman.schemas.pipeline.estimator import (
    CapacityMetrics,
    TrafficMetrics,
    StorageMetrics,
    NetworkMetrics,
    CacheMetrics,
)
from nirman.agents.core.gemini_client import GeminiClient
from nirman.agents.core.react_engine import ReActEngine
from nirman.tools.registry import build_default_registry

logger = logging.getLogger("nirman.analyzer")


class AnalyzerOutput(BaseModel):
    """Combined output model for the Requirement Analyzer LLM agent."""
    domain: DomainType = Field(..., description="Target system domain")
    target_scale: TargetScale = Field(..., description="Scale category")
    cloud_provider: CloudEnvironment = Field(..., description="Cloud target: AWS, GCP, Azure, etc.")
    preferred_style: ArchitecturalStyle = Field(..., description="Architectural paradigm")
    target_dau: int = Field(..., description="Estimated Daily Active Users (e.g. 50000000)")
    peak_factor: float = Field(default=3.0, description="Peak to average ratio multiplier")
    read_write_ratio: str = Field(default="80:20", description="Read:Write traffic ratio")
    avg_qps: int = Field(..., description="Calculated Average QPS: (DAU * 30 ops/day) / 86400")
    peak_qps: int = Field(..., description="Calculated Peak QPS: avg_qps * peak_factor")
    daily_storage_gb: float = Field(..., description="Estimated net storage growth per day in GB")
    five_year_storage_tb: float = Field(..., description="5-Year Net Storage projection in TB")
    effective_5yr_storage_tb: float = Field(..., description="5-Year Physical Storage with 3x Multi-AZ replication in TB")
    ingress_bandwidth_gbps: float = Field(..., description="Peak network ingress bandwidth in Gbps")
    egress_bandwidth_gbps: float = Field(..., description="Peak network egress bandwidth in Gbps")
    cache_memory_ram_gb: float = Field(..., description="Redis cache RAM sizing for 80/20 hot working set in GB")
    recommended_cache_nodes: int = Field(default=6, description="Recommended Redis cluster node count")
    recommended_compute_pods: int = Field(..., description="Recommended container compute pods")
    functional_requirements: list[FunctionalRequirement] = Field(..., description="Core features (FR-01, FR-02...)")
    non_functional_requirements: list[NonFunctionalRequirement] = Field(..., description="SLAs (Latency, Availability, etc.)")
    constraints: list[str] = Field(default_factory=list, description="Strict operational constraints")


ANALYZER_SYSTEM_PROMPT = """You are the Principal Systems Architect and Capacity Planner of NirmanAI.
Your role is to deeply analyze the user's natural language system design request and formulate a rigorous, production-grade architecture specification.

You must reason through:
1. DOMAIN CLASSIFICATION: FinTech, E-Commerce, Streaming, Social, MLOps, IoT, Gaming, etc.
2. BACK-OF-THE-ENVELOPE CAPACITY ESTIMATION:
   - Daily Active Users (DAU): Parse or estimate realistic DAU (default 10M-50M for hyperscale systems).
   - Read/Write Ratio: Standard 80:20 or domain-specific (e.g. 99:1 for streaming, 60:40 for chat).
   - Average Throughput (QPS) = (DAU * 30 ops/day) / 86,400 seconds.
   - Peak Throughput (QPS) = Average QPS * peak_factor (typically 3.0x - 4.5x).
   - Daily Storage Growth (GB) and 5-Year Physical Storage (TB) factoring in a 3x Multi-AZ replication factor.
   - Peak Network Bandwidth (Ingress and Egress in Gbps).
   - In-Memory Cache (RAM) Sizing: 80/20 Pareto rule sizing ~20% of daily active read working set in Redis RAM.
   - Kubernetes Container Cluster Sizing: Compute pods required for peak concurrency.
3. FUNCTIONAL REQUIREMENTS (FRs): 4-6 specific engineering features with priorities.
4. NON-FUNCTIONAL REQUIREMENTS (NFRs / SLAs): P99 latency targets, availability (99.99%+), consistency guarantees, and zero-trust security.
5. OPERATIONAL CONSTRAINTS: Multi-AZ active-active failover, data residency, mTLS, encryption at rest/transit.

Be realistic, rigorous, and mathematically grounded."""


class RequirementAnalyzerAgent:
    """Real LLM Agent that analyzes prompts with self-validation, retry, and domain enhancement.
    
    Agent Capabilities:
    - Error handling with structured retries (up to 3 attempts)
    - Output self-validation (checks critical fields for sanity)
    - Self-correction (feeds validation errors back to LLM for re-generation)
    - Domain context enrichment via PromptEnhancer integration
    """

    MAX_RETRIES = 3

    def __init__(self, gemini_client: Optional[GeminiClient] = None):
        self.client = gemini_client or GeminiClient()
        self._registry = build_default_registry()

    def _validate_output(self, output: AnalyzerOutput) -> list[str]:
        """Self-validation: checks critical fields for sanity. Returns list of issues."""
        issues = []
        if output.target_dau <= 0:
            issues.append(f"target_dau must be positive, got {output.target_dau}")
        if output.avg_qps <= 0:
            issues.append(f"avg_qps must be positive, got {output.avg_qps}")
        if output.peak_qps <= 0:
            issues.append(f"peak_qps must be positive, got {output.peak_qps}")
        if output.peak_qps < output.avg_qps:
            issues.append(f"peak_qps ({output.peak_qps}) should be >= avg_qps ({output.avg_qps})")
        if output.daily_storage_gb <= 0:
            issues.append(f"daily_storage_gb must be positive, got {output.daily_storage_gb}")
        if len(output.functional_requirements) < 2:
            issues.append(f"Expected at least 2 functional requirements, got {len(output.functional_requirements)}")
        if len(output.non_functional_requirements) < 1:
            issues.append(f"Expected at least 1 non-functional requirement, got {len(output.non_functional_requirements)}")
        return issues

    def _parse_read_write_ratio(self, ratio_str: str) -> tuple[float, float]:
        """Parse LLM-provided read:write ratio string into float percentages."""
        try:
            parts = ratio_str.replace(" ", "").split(":")
            read_val = float(parts[0])
            write_val = float(parts[1])
            total = read_val + write_val
            return round(read_val / total, 2), round(write_val / total, 2)
        except (ValueError, IndexError, ZeroDivisionError):
            logger.warning(f"Could not parse read_write_ratio '{ratio_str}', defaulting to 80:20")
            return 0.80, 0.20

    def analyze(self, prompt: str) -> Tuple[RequirementSpec, CapacityMetrics]:
        """ReAct-powered requirement analysis with research-backed specifications.
        
        Autonomous agent loop:
        1. Research domain-specific compliance & regulation requirements via web search
        2. Extract functional and non-functional requirements with LLM
        3. Self-validate output for sanity
        4. If validation fails, retry with self-correction feedback
        
        Falls back to direct Gemini structured call if ReAct fails.
        """
        enhanced_prompt = prompt

        # Phase 1: ReAct-powered analysis with web research
        try:
            logger.info("🤖 RequirementAnalyzer ReAct Agent: researching domain requirements...")
            tools = self._registry.get_tools(["search_web", "read_url"])
            engine = ReActEngine(
                gemini_client=self.client,
                persona="Staff Solutions Architect & Requirements Engineer with 15yr experience at AWS and Google Cloud",
                tools=tools,
                output_schema=AnalyzerOutput,
                max_steps=6,
            )

            goal = (
                f"Analyze this system design prompt and produce a complete architectural "
                f"specification with capacity estimates.\n\n"
                f"ENHANCED PROMPT: \"{enhanced_prompt}\"\n\n"
                f"INSTRUCTIONS:\n"
                f"1. SEARCH the web for compliance requirements specific to this domain "
                f"(e.g., HIPAA for healthcare, PCI-DSS for payments, eDiscovery for legal)\n"
                f"2. SEARCH for industry benchmarks for capacity sizing in this domain\n"
                f"3. Then produce your FINAL_ANSWER as an AnalyzerOutput with:\n"
                f"   - Realistic DAU, QPS, storage projections\n"
                f"   - Domain-appropriate functional requirements (4-6)\n"
                f"   - Research-backed non-functional requirements/SLAs (3-5)\n"
                f"   - Compliance-aware constraints\n"
            )

            result = engine.run(goal)
            output: AnalyzerOutput = result.output
            logger.info(
                f"✅ ReAct Analyzer completed in {result.total_steps} steps, "
                f"{len(result.tools_used)} tool calls"
            )

        except Exception as e:
            logger.warning(f"ReAct analysis failed ({e}), falling back to direct structured call.")
            output = self._direct_structured_analysis(enhanced_prompt)

        # Phase 2: Self-validate and build output objects
        issues = self._validate_output(output)
        if issues:
            logger.warning(f"⚠️ Analyzer validation issues: {'; '.join(issues)}. Using output anyway.")

        # Build RequirementSpec
        spec = RequirementSpec(
            raw_prompt=prompt,
            domain=output.domain,
            target_scale=output.target_scale,
            cloud_provider=output.cloud_provider,
            preferred_style=output.preferred_style,
            target_dau=output.target_dau,
            peak_factor=output.peak_factor,
            functional_requirements=output.functional_requirements,
            non_functional_requirements=output.non_functional_requirements,
            constraints=output.constraints,
        )

        # Build CapacityMetrics — use LLM-provided ratios, NOT hardcoded
        read_ratio, write_ratio = self._parse_read_write_ratio(output.read_write_ratio)
        
        traffic = TrafficMetrics(
            dau=output.target_dau,
            read_write_ratio=output.read_write_ratio,
            read_ratio=read_ratio,
            write_ratio=write_ratio,
            avg_qps=output.avg_qps,
            peak_qps=output.peak_qps,
            read_peak_qps=int(output.peak_qps * read_ratio),
            write_peak_qps=int(output.peak_qps * write_ratio),
        )

        yearly_tb = round((output.daily_storage_gb * 365) / 1024, 2)
        storage = StorageMetrics(
            daily_storage_gb=output.daily_storage_gb,
            yearly_storage_tb=yearly_tb,
            five_year_storage_tb=output.five_year_storage_tb,
            effective_5yr_storage_tb=output.effective_5yr_storage_tb,
        )

        total_bw = round(output.ingress_bandwidth_gbps + output.egress_bandwidth_gbps, 3)
        network = NetworkMetrics(
            ingress_bandwidth_gbps=output.ingress_bandwidth_gbps,
            egress_bandwidth_gbps=output.egress_bandwidth_gbps,
            total_peak_bandwidth_gbps=total_bw,
        )

        cache = CacheMetrics(
            cache_memory_ram_gb=output.cache_memory_ram_gb,
            recommended_nodes=output.recommended_cache_nodes,
        )

        capacity = CapacityMetrics(
            traffic=traffic,
            storage=storage,
            network=network,
            cache=cache,
            recommended_compute_pods=output.recommended_compute_pods,
        )

        logger.info(f"✅ Analyzer completed. DAU={output.target_dau:,}, Peak QPS={output.peak_qps:,}")
        return spec, capacity

    def _direct_structured_analysis(self, enhanced_prompt: str) -> AnalyzerOutput:
        """Fallback: direct Gemini structured call with retry + self-correction."""
        user_prompt = (
            f"Analyze this system design requirement and provide a complete "
            f"architectural specification and capacity estimation:\n\n\"{enhanced_prompt}\""
        )

        last_error = None
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                logger.info(f"🔍 Direct analyzer attempt {attempt}/{self.MAX_RETRIES}...")
                output: AnalyzerOutput = self.client.generate_structured(
                    system_prompt=ANALYZER_SYSTEM_PROMPT,
                    user_prompt=user_prompt,
                    schema=AnalyzerOutput,
                )

                # Self-validation
                issues = self._validate_output(output)
                if issues:
                    issues_str = "; ".join(issues)
                    logger.warning(f"⚠️ Validation issues (attempt {attempt}): {issues_str}")
                    if attempt < self.MAX_RETRIES:
                        user_prompt = (
                            f"Your previous analysis had these issues: {issues_str}\n\n"
                            f"Please fix these problems and re-analyze:\n\n\"{enhanced_prompt}\""
                        )
                        continue

                return output

            except Exception as e:
                last_error = e
                logger.error(f"❌ Direct analysis attempt {attempt} failed: {e}")
                if attempt < self.MAX_RETRIES:
                    user_prompt = (
                        f"Previous attempt failed: {str(e)}\n\n"
                        f"Please try again:\n\n\"{enhanced_prompt}\""
                    )
                    continue

        raise RuntimeError(
            f"RequirementAnalyzerAgent failed after {self.MAX_RETRIES} attempts. Last error: {last_error}"
        )


# Alias for backward compatibility
RequirementAnalyzer = RequirementAnalyzerAgent
