"""
NirmanAI - Legacy Orchestrator (Deprecated)
============================================
This module has been superseded by nirman.workflow.graph.NirmanWorkflow
which provides LangGraph-based cyclic multi-agent orchestration with:
- PromptEnhancer integration (Phase 0)
- Deterministic CapacityEstimator (Phase 2)
- State rollback on refinement regression
- Error handling at every node
- Self-validating agents with retry logic

Migration: Replace all `NirmanOrchestrator` usage with `NirmanWorkflow.run()`.
"""

# All orchestration is now handled by nirman.workflow.graph.NirmanWorkflow
# See: nirman/workflow/graph.py

import warnings


class NirmanOrchestrator:
    """DEPRECATED: Use nirman.workflow.graph.NirmanWorkflow instead."""

    def __init__(self, *args, **kwargs):
        warnings.warn(
            "NirmanOrchestrator is deprecated. Use nirman.workflow.graph.NirmanWorkflow instead.",
            DeprecationWarning,
            stacklevel=2,
        )

    def synthesize(self, *args, **kwargs):
        raise NotImplementedError(
            "NirmanOrchestrator has been deprecated. "
            "Use nirman.workflow.graph.NirmanWorkflow().run(prompt) instead."
        )
