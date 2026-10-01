"""
NirmanAI - Estimator Schema
===========================
Defines deterministic capacity planning data structures: QPS, network bandwidth,
multi-year storage projections, and cache memory allocations.
"""

from typing import Dict, Optional
from pydantic import BaseModel, Field


class TrafficMetrics(BaseModel):
    dau: int = Field(..., description="Daily Active Users")
    actions_per_user_day: int = Field(default=30, description="Average operations performed per user daily")
    read_write_ratio: str = Field(default="80:20", description="Read to write ratio")
    read_ratio: float = Field(default=0.80, description="Read traffic fraction (0.0 - 1.0)")
    write_ratio: float = Field(default=0.20, description="Write traffic fraction (0.0 - 1.0)")
    avg_qps: int = Field(..., description="Average Queries Per Second across 24h")
    peak_qps: int = Field(..., description="Peak Queries Per Second under maximum load")
    read_peak_qps: int = Field(..., description="Peak read queries per second")
    write_peak_qps: int = Field(..., description="Peak write queries per second")


class StorageMetrics(BaseModel):
    avg_payload_size_kb: float = Field(default=2.5, description="Average write record size in Kilobytes")
    daily_storage_gb: float = Field(..., description="Net raw storage ingested per day in Gigabytes")
    yearly_storage_tb: float = Field(..., description="Net storage ingested per year in Terabytes")
    five_year_storage_tb: float = Field(..., description="Net storage over 5-year operational lifecycle in TB")
    replication_factor: int = Field(default=3, description="Database Multi-AZ replication multiplier")
    effective_5yr_storage_tb: float = Field(..., description="Total physical disk footprint including replication (TB)")


class NetworkMetrics(BaseModel):
    ingress_bandwidth_gbps: float = Field(..., description="Inbound network bandwidth under peak traffic (Gbps)")
    egress_bandwidth_gbps: float = Field(..., description="Outbound network bandwidth under peak traffic (Gbps)")
    total_peak_bandwidth_gbps: float = Field(..., description="Aggregated network throughput at edge ingress (Gbps)")


class CacheMetrics(BaseModel):
    cache_policy: str = Field(default="LRU (Least Recently Used)", description="Cache eviction strategy")
    working_set_fraction: float = Field(default=0.20, description="80/20 Pareto rule fraction of daily hot data in RAM")
    cache_memory_ram_gb: float = Field(..., description="Dedicated Redis/Memcached RAM allocation (GB)")
    recommended_nodes: int = Field(default=3, description="Recommended Redis Cluster node count for high availability")


class CapacityMetrics(BaseModel):
    traffic: TrafficMetrics = Field(..., description="Throughput and concurrency profile")
    storage: StorageMetrics = Field(..., description="Data volume and disk capacity projections")
    network: NetworkMetrics = Field(..., description="Ingress and egress bandwidth requirements")
    cache: CacheMetrics = Field(..., description="In-memory cache sizing specifications")
    recommended_compute_pods: int = Field(..., description="Estimated Kubernetes stateless service pod count")
