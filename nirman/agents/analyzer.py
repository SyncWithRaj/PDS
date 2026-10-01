"""
NirmanAI - Requirement Analyzer Agent (Gemini LLM)
==================================================
Real LLM reasoning agent acting as Principal Systems Architect & Capacity Planner:
- Analyzes unstructured natural language prompts
- Derives domain profile, scale tiers, cloud environments
- Reasons through back-of-the-envelope capacity planning
- Extracts explicit Functional Requirements (FRs) and Non-Functional SLAs (NFRs)
"""

import os
import json
import logging
from typing import Optional, Tuple
from pydantic import BaseModel, Field

from nirman.schemas.analyzer import (
    RequirementSpec,
    DomainType,
    TargetScale,
    CloudEnvironment,
    ArchitecturalStyle,
    FunctionalRequirement,
    NonFunctionalRequirement,
)
from nirman.schemas.estimator import (
    CapacityMetrics,
    TrafficMetrics,
    StorageMetrics,
    NetworkMetrics,
    CacheMetrics,
)
from nirman.agents.gemini_client import GeminiClient

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
    """Real LLM Agent that analyzes prompts and outputs RequirementSpec & CapacityMetrics."""

    def __init__(self, gemini_client: Optional[GeminiClient] = None):
        self.client = gemini_client or GeminiClient()

    def analyze(self, prompt: str) -> Tuple[RequirementSpec, CapacityMetrics]:
        """Invokes Gemini LLM to reason and extract specs and capacity sizing."""
        user_prompt = f"Analyze this system design requirement and provide a complete architectural specification and capacity estimation:\n\n\"{prompt}\""
        
        # Real LLM call
        output: AnalyzerOutput = self.client.generate_structured(
            system_prompt=ANALYZER_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            schema=AnalyzerOutput,
        )

        # Assemble RequirementSpec
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

        # Assemble CapacityMetrics
        traffic = TrafficMetrics(
            dau=output.target_dau,
            read_write_ratio=output.read_write_ratio,
            read_ratio=0.80,
            write_ratio=0.20,
            avg_qps=output.avg_qps,
            peak_qps=output.peak_qps,
            read_peak_qps=int(output.peak_qps * 0.8),
            write_peak_qps=int(output.peak_qps * 0.2),
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

        return spec, capacity


# Alias for backward compatibility
RequirementAnalyzer = RequirementAnalyzerAgent
