"""
NirmanAI - Capacity Estimator Agent (ReAct Agentic)
=====================================================
TRUE AUTONOMOUS AGENT — NOT hardcoded math.

Uses the ReAct (Reason + Act) loop to:
1. THINK about what capacity calculations are needed for this specific domain
2. WRITE custom Python code to calculate QPS, storage, bandwidth, cache
3. RUN the code via python_repl tool and read the output
4. SEARCH for real-world benchmarks to validate its numbers
5. ADAPT calculations to the domain (legal = 8hr workday, social = 24hr, gaming = high concurrent)
6. PRODUCE validated, research-backed CapacityMetrics

Falls back to deterministic math engine if the ReAct loop fails.
"""

import logging
from typing import Optional, Union
from pydantic import BaseModel, Field

from nirman.schemas.pipeline.estimator import (
    CapacityMetrics,
    TrafficMetrics,
    StorageMetrics,
    NetworkMetrics,
    CacheMetrics,
)
from nirman.schemas.pipeline.analyzer import RequirementSpec
from nirman.agents.core.gemini_client import GeminiClient
from nirman.agents.core.react_engine import ReActEngine
from nirman.tools.registry import build_default_registry

logger = logging.getLogger("nirman.estimator")


# === Persona ===
ESTIMATOR_PERSONA = (
    "Principal Performance Engineer & Capacity Planner with 15+ years at Netflix, "
    "Amazon, and Google. You specialize in back-of-the-envelope calculations for "
    "distributed systems. You ALWAYS validate your math by writing Python code and "
    "cross-checking against real-world benchmarks. You understand that different "
    "domains have wildly different traffic patterns — legal search has 8-hour workdays, "
    "social media is 24/7, gaming has massive concurrent spikes, fintech has burst "
    "patterns around market hours."
)


class CapacityEstimatorAgent:
    """ReAct-powered capacity planning agent.

    This agent autonomously:
    1. Analyzes the domain to determine traffic patterns
    2. Writes Python code to calculate QPS, storage, bandwidth, cache sizing
    3. Executes the code and reads the results
    4. Searches for real-world benchmarks to validate numbers
    5. Produces validated CapacityMetrics

    Falls back to deterministic math on failure.
    """

    SECONDS_PER_DAY = 86_400

    def __init__(self, gemini_client: Optional[GeminiClient] = None):
        self.client = gemini_client or GeminiClient()
        self._registry = build_default_registry()

    def estimate(
        self,
        spec_or_dau: Optional[Union[RequirementSpec, int]] = None,
        *,
        dau: Optional[int] = None,
        actions_per_user_day: int = 30,
        read_ratio: float = 0.80,
        avg_payload_size_kb: float = 2.5,
        peak_factor: Optional[float] = None,
        replication_factor: int = 3,
        working_set_fraction: float = 0.20,
    ) -> CapacityMetrics:
        """Estimate capacity using ReAct agent with Python REPL and web search.

        Falls back to deterministic math on failure.
        """
        # Extract DAU and domain context
        if spec_or_dau is not None:
            if isinstance(spec_or_dau, RequirementSpec):
                target_dau = spec_or_dau.target_dau
                peak_factor = spec_or_dau.peak_factor or 3.0
                domain_context = (
                    f"Domain: {spec_or_dau.domain.value}, "
                    f"Scale: {spec_or_dau.target_scale.value}, "
                    f"Cloud: {spec_or_dau.cloud_provider.value}"
                )
            else:
                target_dau = int(spec_or_dau)
                peak_factor = peak_factor or 3.0
                domain_context = "General web application"
        elif dau is not None:
            target_dau = int(dau)
            peak_factor = peak_factor or 3.0
            domain_context = "General web application"
        else:
            raise ValueError("Either spec_or_dau or dau must be provided.")

        # Try ReAct agent first
        try:
            return self._react_estimate(
                target_dau, domain_context, peak_factor,
                actions_per_user_day, read_ratio, avg_payload_size_kb,
                replication_factor, working_set_fraction,
            )
        except Exception as e:
            logger.warning(f"ReAct estimator failed ({e}), using deterministic fallback.")
            return self._deterministic_fallback(
                target_dau, peak_factor, actions_per_user_day,
                read_ratio, avg_payload_size_kb, replication_factor,
                working_set_fraction,
            )

    def _react_estimate(
        self, dau, domain_context, peak_factor,
        actions_per_user_day, read_ratio, avg_payload_size_kb,
        replication_factor, working_set_fraction,
    ) -> CapacityMetrics:
        """Use ReAct agent with python_repl + search_web to calculate capacity."""
        logger.info(f"🤖 CapacityEstimator ReAct Agent starting | DAU={dau:,} | {domain_context}")

        tools = self._registry.get_tools(["python_repl", "search_web"])
        engine = ReActEngine(
            gemini_client=self.client,
            persona=ESTIMATOR_PERSONA,
            tools=tools,
            output_schema=CapacityMetrics,
            max_steps=8,
        )

        goal = (
            f"Calculate precise capacity metrics for this system.\n\n"
            f"SYSTEM CONTEXT: {domain_context}\n"
            f"DAU: {dau:,}\n"
            f"Peak Factor: {peak_factor}x\n"
            f"Actions Per User/Day: {actions_per_user_day}\n"
            f"Read/Write Ratio: {int(read_ratio*100)}:{int((1-read_ratio)*100)}\n"
            f"Avg Payload: {avg_payload_size_kb} KB\n"
            f"Replication Factor: {replication_factor}x\n\n"
            f"INSTRUCTIONS:\n"
            f"1. Use the python_repl tool to calculate:\n"
            f"   - Average QPS and Peak QPS (adapt to domain traffic patterns)\n"
            f"   - Daily storage growth, yearly, and 5-year projections\n"
            f"   - Network bandwidth (ingress + egress in Gbps)\n"
            f"   - Redis cache sizing (80/20 Pareto rule)\n"
            f"   - Kubernetes pod count\n"
            f"2. Optionally search_web to validate against real-world benchmarks\n"
            f"3. Produce your FINAL_ANSWER as a CapacityMetrics JSON\n\n"
            f"The output must have this structure:\n"
            f'{{"traffic": {{"dau": int, "read_write_ratio": "80:20", "read_ratio": 0.8, '
            f'"write_ratio": 0.2, "avg_qps": int, "peak_qps": int, '
            f'"read_peak_qps": int, "write_peak_qps": int}}, '
            f'"storage": {{"daily_storage_gb": float, "yearly_storage_tb": float, '
            f'"five_year_storage_tb": float, "effective_5yr_storage_tb": float}}, '
            f'"network": {{"ingress_bandwidth_gbps": float, "egress_bandwidth_gbps": float, '
            f'"total_peak_bandwidth_gbps": float}}, '
            f'"cache": {{"cache_memory_ram_gb": float, "recommended_nodes": int}}, '
            f'"recommended_compute_pods": int}}'
        )

        result = engine.run(goal)
        capacity: CapacityMetrics = result.output

        logger.info(
            f"✅ ReAct Estimator completed in {result.total_steps} steps, "
            f"{len(result.tools_used)} tool calls | "
            f"DAU={capacity.traffic.dau:,}, Peak QPS={capacity.traffic.peak_qps:,}, "
            f"Storage 5yr={capacity.storage.effective_5yr_storage_tb:.1f} TB"
        )
        return capacity

    def _deterministic_fallback(
        self, dau, peak_factor, actions_per_user_day,
        read_ratio, avg_payload_size_kb, replication_factor,
        working_set_fraction,
    ) -> CapacityMetrics:
        """Pure mathematical deterministic fallback (no LLM, no tools)."""
        logger.info(f"📐 Deterministic capacity estimation for DAU={dau:,}")

        write_ratio = round(1.0 - read_ratio, 2)
        read_write_str = f"{int(read_ratio * 100)}:{int(write_ratio * 100)}"

        # 1. Traffic
        total_daily_ops = dau * actions_per_user_day
        avg_qps = max(1, int(round(total_daily_ops / self.SECONDS_PER_DAY)))
        peak_qps = max(1, int(round(avg_qps * peak_factor)))
        read_peak_qps = max(1, int(round(peak_qps * read_ratio)))
        write_peak_qps = max(1, int(round(peak_qps * write_ratio)))

        traffic = TrafficMetrics(
            dau=dau,
            actions_per_user_day=actions_per_user_day,
            read_write_ratio=read_write_str,
            read_ratio=read_ratio,
            write_ratio=write_ratio,
            avg_qps=avg_qps,
            peak_qps=peak_qps,
            read_peak_qps=read_peak_qps,
            write_peak_qps=write_peak_qps,
        )

        # 2. Storage
        daily_write_events = total_daily_ops * write_ratio
        daily_storage_kb = daily_write_events * avg_payload_size_kb
        daily_storage_gb = round(daily_storage_kb / (1024.0 * 1024.0), 3)
        yearly_storage_tb = round((daily_storage_gb * 365.0) / 1024.0, 3)
        five_year_storage_tb = round(yearly_storage_tb * 5.0, 3)
        effective_5yr_storage_tb = round(five_year_storage_tb * replication_factor, 3)

        storage = StorageMetrics(
            avg_payload_size_kb=avg_payload_size_kb,
            daily_storage_gb=daily_storage_gb,
            yearly_storage_tb=yearly_storage_tb,
            five_year_storage_tb=five_year_storage_tb,
            replication_factor=replication_factor,
            effective_5yr_storage_tb=effective_5yr_storage_tb,
        )

        # 3. Network
        ingress_kbps = write_peak_qps * avg_payload_size_kb * 8.0
        ingress_gbps = round(ingress_kbps / (1024.0 * 1024.0), 4)
        avg_read_payload_kb = avg_payload_size_kb * 2.0
        egress_kbps = read_peak_qps * avg_read_payload_kb * 8.0
        egress_gbps = round(egress_kbps / (1024.0 * 1024.0), 4)
        total_bandwidth_gbps = round(ingress_gbps + egress_gbps, 4)

        network = NetworkMetrics(
            ingress_bandwidth_gbps=ingress_gbps,
            egress_bandwidth_gbps=egress_gbps,
            total_peak_bandwidth_gbps=total_bandwidth_gbps,
        )

        # 4. Cache
        raw_hot_data_gb = daily_storage_gb * working_set_fraction
        cache_ram_gb = round(max(4.0, raw_hot_data_gb * 1.30), 2)
        recommended_nodes = max(3, int(round(cache_ram_gb / 32.0)) * 2 + 1)

        cache = CacheMetrics(
            cache_policy="LRU (Least Recently Used) with Volatile-TTL",
            working_set_fraction=working_set_fraction,
            cache_memory_ram_gb=cache_ram_gb,
            recommended_nodes=recommended_nodes,
        )

        # 5. Compute
        compute_pods = max(3, int(round(peak_qps / 2500.0)) + 2)

        logger.info(
            f"✅ Deterministic capacity: DAU={dau:,}, Peak QPS={peak_qps:,}, "
            f"Storage 5yr={effective_5yr_storage_tb:.1f} TB"
        )

        return CapacityMetrics(
            traffic=traffic,
            storage=storage,
            network=network,
            cache=cache,
            recommended_compute_pods=compute_pods,
        )


# Alias for backward compatibility
CapacityEstimator = CapacityEstimatorAgent
