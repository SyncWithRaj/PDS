"""
NirmanAI - LangGraph Cyclic Multi-Agent Workflow
================================================
State machine orchestrating the iterative architecture synthesis feedback loop:
1. RequirementAnalyzer (Gemini LLM)
2. ArchitectureGenerator (Gemini LLM)
3. ArchitectureCritic (Gemini LLM - 8 Pillars)
4. RefinementAgent (Gemini LLM - Surgical Patches)
5. SynthesizerAgent (Dossier & Live Mermaid.js Deliverables)
"""

from nirman.workflow.state import NirmanState
from nirman.workflow.graph import NirmanWorkflow

__all__ = ["NirmanState", "NirmanWorkflow"]
