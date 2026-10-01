"""
NirmanAI - Capacity Estimator Agent
===================================
Deterministic capacity planning mathematics engine for high-scale distributed systems.
Performs exact calculations for:
- Peak QPS & Read/Write concurrency
- Ingress & Egress network throughput in Gbps
- 5-Year storage footprints and multi-AZ physical disk projections
- 80/20 Pareto rule Redis/Memcached in-memory sizing
- Stateless Kubernetes pod scaling projections
"""

from typing import Optional, Union
from nirman.schemas.estimator import (
    CapacityMetrics,
    TrafficMetrics,
    StorageMetrics,
    NetworkMetrics,
    CacheMetrics,
)
from nirman.schemas.analyzer import RequirementSpec


class CapacityEstimator:
    """Pure mathematical deterministic capacity estimator.
    Guarantees mathematically rigorous, non-hallucinated capacity metrics.
    """

    SECONDS_PER_DAY = 86_400

    def __init__(self, default_peak_factor: float = 3.0):
        self.default_peak_factor = default_peak_factor

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
        """Computes complete deterministic CapacityMetrics."""
        if spec_or_dau is not None:
            if isinstance(spec_or_dau, RequirementSpec):
                target_dau = spec_or_dau.target_dau
                peak_factor = spec_or_dau.peak_factor or self.default_peak_factor
            else:
                target_dau = int(spec_or_dau)
                peak_factor = peak_factor or self.default_peak_factor
        elif dau is not None:
            target_dau = int(dau)
            peak_factor = peak_factor or self.default_peak_factor
        else:
            raise ValueError("Either spec_or_dau or dau must be provided to CapacityEstimator.estimate()")

        dau = target_dau

        write_ratio = round(1.0 - read_ratio, 2)
        read_write_str = f"{int(read_ratio * 100)}:{int(write_ratio * 100)}"

        # 1. Traffic Concurrency Calculations
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

        # 2. Multi-Year Storage Lifecycle Projections
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

        # 3. Peak Network Throughput (in Gbps)
        # 1 KB = 8 Kilobits. 1 Gbps = 1,000,000 Kilobits (or 1,024 * 1024 Kb)
        ingress_kbps = write_peak_qps * avg_payload_size_kb * 8.0
        ingress_gbps = round(ingress_kbps / (1024.0 * 1024.0), 4)

        # Reads usually return richer payload representations (~2.0x write payload)
        avg_read_payload_kb = avg_payload_size_kb * 2.0
        egress_kbps = read_peak_qps * avg_read_payload_kb * 8.0
        egress_gbps = round(egress_kbps / (1024.0 * 1024.0), 4)

        total_bandwidth_gbps = round(ingress_gbps + egress_gbps, 4)

        network = NetworkMetrics(
            ingress_bandwidth_gbps=ingress_gbps,
            egress_bandwidth_gbps=egress_gbps,
            total_peak_bandwidth_gbps=total_bandwidth_gbps,
        )

        # 4. In-Memory Cache (Redis Cluster / Pareto 80/20 Rule)
        # Hot data working set = 20% of daily data volume
        raw_hot_data_gb = daily_storage_gb * working_set_fraction
        # Redis memory overhead buffer (30% for key metadata, hash tables, jemalloc)
        cache_ram_gb = round(max(4.0, raw_hot_data_gb * 1.30), 2)
        # Recommended node count assuming 32GB or 64GB instances with primary-replica pairing
        recommended_nodes = max(3, int(round(cache_ram_gb / 32.0)) * 2 + 1)

        cache = CacheMetrics(
            cache_policy="LRU (Least Recently Used) with Volatile-TTL",
            working_set_fraction=working_set_fraction,
            cache_memory_ram_gb=cache_ram_gb,
            recommended_nodes=recommended_nodes,
        )

        # 5. Stateless Compute Tier Pod Estimation (assuming ~2,500 RPS per pod)
        compute_pods = max(3, int(round(peak_qps / 2500.0)) + 2)

        return CapacityMetrics(
            traffic=traffic,
            storage=storage,
            network=network,
            cache=cache,
            recommended_compute_pods=compute_pods,
        )
