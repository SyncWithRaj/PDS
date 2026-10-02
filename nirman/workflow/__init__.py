"""
NirmanAI - LangGraph Cyclic Multi-Agent Workflow
================================================
Production-grade state machine orchestrating the iterative architecture synthesis loop:
0. PromptEnhancer (Domain Context Enrichment)
1. RequirementAnalyzer (Gemini LLM - Self-Validating)
2. CapacityEstimator (Deterministic Math Engine)
3. ArchitectureGenerator (Gemini/Ollama LLM - Mermaid Validated)
4. ArchitectureCritic (Gemini LLM - 8-Pillar Rubric + Deterministic Scoring)
5. ArchitectureRefiner (Gemini LLM - Surgical Patches + Rollback)
6. SynthesizerAgent (Dynamic Dossier & Live Mermaid.js Deliverables)
"""

from nirman.workflow.state import NirmanState
from nirman.workflow.graph import NirmanWorkflow

__all__ = ["NirmanState", "NirmanWorkflow"]
