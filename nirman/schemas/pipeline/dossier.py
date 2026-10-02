"""
NirmanAI - Master Output Dossier Schema
=======================================
Defines the final, comprehensive System Architecture Dossier deliverable
including capacity planning tables, visual Mermaid diagrams, component specs,
trade-off matrices, and critic scorecard history.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from nirman.schemas.pipeline.analyzer import RequirementSpec
from nirman.schemas.pipeline.estimator import CapacityMetrics
from nirman.schemas.pipeline.generator import SystemArchitecture
from nirman.schemas.legacy.critic import CriticScorecard
from nirman.schemas.legacy.refiner import RefinementIteration


class ComponentDetailItem(BaseModel):
    name: str = Field(..., description="Component Name (e.g. 'API Gateway & Ingress Layer')")
    tech: str = Field(..., description="Selected Technology (e.g. 'Envoy Gateway / Kong')")
    rationale: str = Field(..., description="Technical justification for this technology choice over alternatives")


class TradeOffItem(BaseModel):
    decision: str = Field(..., description="Architectural design decision (e.g. 'CQRS with Separate Read/Write Stores')")
    option_chosen: str = Field(..., description="Technology/Pattern chosen")
    option_discarded: str = Field(..., description="Technology/Pattern considered and discarded")
    trade_off_rationale: str = Field(..., description="Detailed trade-off analysis (e.g. Eventual consistency vs lower latency)")


class BottleneckMitigationItem(BaseModel):
    bottleneck_description: str = Field(..., description="Potential failure mode or performance choke point")
    mitigation_strategy: str = Field(..., description="Specific engineering solution implemented to eliminate the bottleneck")


class ArchitectureDossier(BaseModel):
    title: str = Field(..., description="System Architecture Title")
    domain: str = Field(..., description="Industry domain")
    style: str = Field(..., description="Architectural style")
    cloud: str = Field(..., description="Target cloud platform")
    
    # Core Dossier Sections
    system_overview: str = Field(..., description="Executive summary and architectural narrative")
    capacity_planning: CapacityMetrics = Field(..., description="Back-of-the-envelope traffic, storage, and RAM math")
    mermaid_diagram: str = Field(..., description="Full production-grade Mermaid.js diagram code")
    sequence_diagram: str = Field(default="", description="Mermaid sequence diagram showing the critical path data flow")
    component_breakdown: List[ComponentDetailItem] = Field(default_factory=list, description="Detailed component specifications")
    trade_offs: List[TradeOffItem] = Field(default_factory=list, description="Explicit architectural trade-off justifications")
    bottlenecks_and_mitigation: List[BottleneckMitigationItem] = Field(default_factory=list, description="Failure mode analysis and concrete mitigations")
    
    # Audit & Refinement History
    final_scorecard: CriticScorecard = Field(..., description="Approved 8-pillar quality evaluation scorecard")
    refinement_history: List[RefinementIteration] = Field(default_factory=list, description="Step-by-step changelog of refinement iterations")
