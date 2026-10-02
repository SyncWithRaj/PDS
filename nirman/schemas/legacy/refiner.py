"""
NirmanAI - Refiner Schema
=========================
Defines the architectural mutation and patching data structures used
by the Refiner Agent to self-correct deficiencies flagged by the Critic.
"""

from enum import Enum
from typing import List, Dict, Optional
from pydantic import BaseModel, Field


class PatchActionType(str, Enum):
    ADD_READ_REPLICAS = "Add Read Replicas & Connection Pooling"
    INTRODUCE_CACHE = "Insert Cache-Aside Distributed Layer (Redis Cluster)"
    DECOUPLE_ASYNC = "Replace Synchronous RPC with Event-Driven Bus (Kafka)"
    ADD_CIRCUIT_BREAKER = "Configure Circuit Breaker, Rate Limiter & Bulkhead"
    SHARD_DATABASE = "Implement Horizontal Partitioning / Sharding Key"
    ADD_API_GATEWAY = "Insert Edge API Gateway with TLS Termination & WAF"
    MULTI_AZ_FAILOVER = "Configure Multi-AZ Active-Active Automated Failover"
    OPTIMIZE_ML_INFERENCE = "Add Triton Inference Server with Dynamic Batching & Vector Cache"


class SurgicalPatch(BaseModel):
    patch_id: str = Field(..., description="Unique patch ID (e.g. 'PATCH-01')")
    target_deficiency_id: str = Field(..., description="Corresponding DEF-ID from Critic deficiency log")
    action_type: PatchActionType = Field(..., description="Categorized remediation action")
    target_node_id: str = Field(..., description="Component modified or added in architecture graph")
    modification_summary: str = Field(..., description="Precise change applied to architecture")
    expected_pillar_impact: str = Field(..., description="Which rubric pillar score this patch aims to boost")


class RefinementIteration(BaseModel):
    iteration_number: int = Field(..., description="Current loop iteration (1, 2, or 3)")
    starting_score: float = Field(..., description="Critic score before this refinement step")
    patches_applied: List[SurgicalPatch] = Field(default_factory=list, description="All architectural patches executed")
    resolved_deficiencies: List[str] = Field(default_factory=list, description="IDs of defects resolved in this iteration")
    refinement_summary: str = Field(..., description="High-level engineering narrative of the iteration")
