"""
NirmanAI - Multi-Agent Suite
============================
Autonomous architecture synthesis agents powered by Google Gemini LLM:
- RequirementAnalyzerAgent: NLP spec extraction & back-of-the-envelope capacity planning
- ArchitectureGeneratorAgent: Multi-tier topology synthesis & Mermaid flowchart authoring
- ArchitectureCriticAgent: 8-pillar stress testing & Single Point of Failure (SPOF) audit
- ArchitectureRefinerAgent: Targeted surgical patch mutation & self-correction loop
- SynthesizerAgent: Dossier compilation & live Mermaid.js report generator
"""

from nirman.agents.gemini_client import GeminiClient
from nirman.agents.analyzer import RequirementAnalyzerAgent
from nirman.agents.generator import ArchitectureGeneratorAgent
from nirman.agents.critic import ArchitectureCriticAgent
from nirman.agents.refiner import ArchitectureRefinerAgent
from nirman.agents.synthesizer import SynthesizerAgent

# Aliases for backward compatibility
RequirementAnalyzer = RequirementAnalyzerAgent
ArchitectureGenerator = ArchitectureGeneratorAgent
ArchitectureCritic = ArchitectureCriticAgent
ArchitectureRefiner = ArchitectureRefinerAgent

__all__ = [
    "GeminiClient",
    "RequirementAnalyzerAgent",
    "ArchitectureGeneratorAgent",
    "ArchitectureCriticAgent",
    "ArchitectureRefinerAgent",
    "SynthesizerAgent",
    # Aliases
    "RequirementAnalyzer",
    "ArchitectureGenerator",
    "ArchitectureCritic",
    "ArchitectureRefiner",
]
