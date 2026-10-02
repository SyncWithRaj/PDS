"""
NirmanAI - Multi-Agent Suite
============================
Autonomous architecture synthesis agents powered by Google Gemini LLM:
- RequirementAnalyzerAgent: NLP spec extraction with self-validation & retry
- CapacityEstimator: Deterministic mathematical capacity planning engine
- PromptEnhancer: Domain-specific context enrichment preprocessor
- ArchitectureGeneratorAgent: Multi-tier topology synthesis with Mermaid validation
- ArchitectureCriticAgent: 8-pillar stress testing with deterministic score recalculation
- ArchitectureRefinerAgent: Targeted surgical patch mutation with safe rollback
- SynthesizerAgent: Dynamic dossier compilation & live Mermaid.js report generator

All agents feature:
- Error handling with structured retries (up to 3 attempts)
- Output self-validation
- Self-correction (feeds validation errors back to LLM)
"""

from nirman.agents.gemini_client import GeminiClient
from nirman.agents.analyzer import RequirementAnalyzerAgent
from nirman.agents.estimator import CapacityEstimator
from nirman.agents.enhancer import PromptEnhancer
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
    "CapacityEstimator",
    "PromptEnhancer",
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
