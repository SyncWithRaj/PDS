"""
NirmanAI Schemas
================
Strict, validated Pydantic v2 data models for the 5-Agent Architecture System:
  - analyzer: Requirements, domains, SLAs
  - estimator: Deterministic capacity math, QPS, storage, bandwidth
  - generator: Component graph, nodes, edges, Mermaid diagrams
  - critic: 8-pillar rubric scorecard, SPOF logs, deficiencies
  - refiner: Surgical patches, mutation plans, iteration tracking
  - dossier: Final comprehensive system architecture dossier
"""

from nirman.schemas.pipeline.analyzer import (
    DomainType,
    TargetScale,
    CloudEnvironment,
    ArchitecturalStyle,
    FunctionalRequirement,
    NonFunctionalRequirement,
    RequirementSpec,
)
from nirman.schemas.pipeline.estimator import (
    TrafficMetrics,
    StorageMetrics,
    NetworkMetrics,
    CacheMetrics,
    CapacityMetrics,
)
from nirman.schemas.pipeline.generator import (
    LayerType,
    CommunicationProtocol,
    ComponentNode,
    ConnectionEdge,
    SystemArchitecture,
)
from nirman.schemas.legacy.critic import (
    EvaluationPillar,
    VulnerabilitySeverity,
    DeficiencyFinding,
    PillarScore,
    CriticScorecard,
)
from nirman.schemas.legacy.refiner import (
    PatchActionType,
    SurgicalPatch,
    RefinementIteration,
)
from nirman.schemas.pipeline.dossier import (
    ComponentDetailItem,
    TradeOffItem,
    BottleneckMitigationItem,
    ArchitectureDossier,
)

__all__ = [
    # Analyzer
    "DomainType",
    "TargetScale",
    "CloudEnvironment",
    "ArchitecturalStyle",
    "FunctionalRequirement",
    "NonFunctionalRequirement",
    "RequirementSpec",
    # Estimator
    "TrafficMetrics",
    "StorageMetrics",
    "NetworkMetrics",
    "CacheMetrics",
    "CapacityMetrics",
    # Generator
    "LayerType",
    "CommunicationProtocol",
    "ComponentNode",
    "ConnectionEdge",
    "SystemArchitecture",
    # Critic
    "EvaluationPillar",
    "VulnerabilitySeverity",
    "DeficiencyFinding",
    "PillarScore",
    "CriticScorecard",
    # Refiner
    "PatchActionType",
    "SurgicalPatch",
    "RefinementIteration",
    # Dossier
    "ComponentDetailItem",
    "TradeOffItem",
    "BottleneckMitigationItem",
    "ArchitectureDossier",
]
