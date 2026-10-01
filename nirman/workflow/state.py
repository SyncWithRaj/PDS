"""
NirmanAI - LangGraph State Definition
=====================================
Defines the shared state schema flowing across the cyclic multi-agent graph:
RequirementAnalyzer -> ArchitectureGenerator -> ArchitectureCritic -> RefinementAgent -> Synthesizer
"""

from typing import TypedDict, List, Optional, Dict, Any
from nirman.schemas.analyzer import RequirementSpec
from nirman.schemas.estimator import CapacityMetrics
from nirman.schemas.generator import SystemArchitecture
from nirman.schemas.critic import CriticScorecard
from nirman.schemas.refiner import RefinementIteration
from nirman.schemas.dossier import ArchitectureDossier


class NirmanState(TypedDict):
    """Global state container for the NirmanAI LangGraph cyclic architecture engine."""
    raw_prompt: str
    spec: Optional[RequirementSpec]
    capacity: Optional[CapacityMetrics]
    architecture: Optional[SystemArchitecture]
    scorecard: Optional[CriticScorecard]
    iterations: int
    max_iterations: int
    refinement_history: List[RefinementIteration]
    dossier: Optional[ArchitectureDossier]
    saved_files: Optional[Dict[str, str]]
    error: Optional[str]
