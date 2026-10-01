"""
NirmanAI - LangGraph Cyclic Architecture Workflow
=================================================
State machine orchestrating the iterative feedback loop across all 5 agents:
Analyzer -> Generator -> Critic -> (Conditional: Score < 85 -> Refiner -> Critic) -> Synthesizer -> END
"""

import os
import logging
from typing import Dict, Any, Optional
from langgraph.graph import StateGraph, END

from nirman.workflow.state import NirmanState
from nirman.agents.gemini_client import GeminiClient
from nirman.agents.analyzer import RequirementAnalyzerAgent
from nirman.agents.generator import ArchitectureGeneratorAgent
from nirman.agents.critic import ArchitectureCriticAgent
from nirman.agents.refiner import ArchitectureRefinerAgent
from nirman.agents.synthesizer import SynthesizerAgent

logger = logging.getLogger("nirman.workflow")


class NirmanWorkflow:
    """Cyclic LangGraph multi-agent engine for distributed system architecture synthesis."""

    def __init__(
        self,
        gemini_client: Optional[GeminiClient] = None,
        output_dir: str = "output",
        max_iterations: int = 2,
    ):
        self.client = gemini_client or GeminiClient()
        self.output_dir = output_dir
        self.max_iterations = max_iterations

        # Instantiate LLM Agents
        self.analyzer = RequirementAnalyzerAgent(self.client)
        self.generator = ArchitectureGeneratorAgent(self.client)
        self.critic = ArchitectureCriticAgent(self.client)
        self.refiner = ArchitectureRefinerAgent(self.client)
        self.synthesizer = SynthesizerAgent()

        # Build Graph
        self.graph = self._build_graph()

    def _build_graph(self):
        builder = StateGraph(NirmanState)

        # 1. Define Nodes
        def analyzer_step(state: NirmanState) -> Dict[str, Any]:
            logger.info("Executing Phase 1: RequirementAnalyzerAgent...")
            spec, capacity = self.analyzer.analyze(state["raw_prompt"])
            return {"spec": spec, "capacity": capacity}

        def generator_step(state: NirmanState) -> Dict[str, Any]:
            logger.info("Executing Phase 2: ArchitectureGeneratorAgent...")
            arch = self.generator.generate(state["spec"], state["capacity"])
            return {"architecture": arch}

        def critic_step(state: NirmanState) -> Dict[str, Any]:
            logger.info("Executing Phase 3: ArchitectureCriticAgent (8-Pillar Rubric Audit)...")
            scorecard = self.critic.audit(state["spec"], state["capacity"], state["architecture"])
            return {"scorecard": scorecard}

        def refiner_step(state: NirmanState) -> Dict[str, Any]:
            current_iter = state.get("iterations", 0) + 1
            logger.info(f"Executing Phase 4: ArchitectureRefinerAgent (Iteration {current_iter})...")
            refined_arch, iter_log = self.refiner.refine(
                state["architecture"],
                state["scorecard"],
                iteration_number=current_iter,
            )
            history = list(state.get("refinement_history", []))
            if iter_log:
                history.append(iter_log)
            return {
                "architecture": refined_arch,
                "iterations": current_iter,
                "refinement_history": history,
            }

        def synthesizer_step(state: NirmanState) -> Dict[str, Any]:
            logger.info("Executing Phase 5: SynthesizerAgent (Compiling Dossier & Mermaid Dashboard)...")
            dossier = self.synthesizer.synthesize(
                spec=state["spec"],
                capacity=state["capacity"],
                arch=state["architecture"],
                scorecard=state["scorecard"],
                refinements=state.get("refinement_history", []),
            )
            saved = self.synthesizer.save(dossier, output_dir=self.output_dir)
            return {"dossier": dossier, "saved_files": saved}

        # 2. Add Nodes to Graph
        builder.add_node("analyzer", analyzer_step)
        builder.add_node("generator", generator_step)
        builder.add_node("critic", critic_step)
        builder.add_node("refiner", refiner_step)
        builder.add_node("synthesizer", synthesizer_step)

        # 3. Define Edges
        builder.set_entry_point("analyzer")
        builder.add_edge("analyzer", "generator")
        builder.add_edge("generator", "critic")

        # 4. Conditional Edge: Quality Gate (Score >= 85 and no SPOF)
        def route_critic(state: NirmanState) -> str:
            sc = state.get("scorecard")
            iters = state.get("iterations", 0)
            max_iters = state.get("max_iterations", self.max_iterations)

            if sc and (not sc.is_accepted or sc.spof_detected) and iters < max_iters:
                logger.info(f"Critic audit score {sc.overall_score}/100 requires refinement (Iteration {iters+1}/{max_iters}).")
                return "refine"
            logger.info(f"Critic audit approved (Score: {sc.overall_score if sc else 0}/100). Routing to Synthesizer.")
            return "synthesize"

        builder.add_conditional_edges(
            "critic",
            route_critic,
            {
                "refine": "refiner",
                "synthesize": "synthesizer",
            },
        )

        # Refiner loops back to Critic for re-evaluation
        builder.add_edge("refiner", "critic")
        builder.add_edge("synthesizer", END)

        return builder.compile()

    def run(self, prompt: str, max_iterations: int = 2) -> Dict[str, Any]:
        """Executes the full LangGraph multi-agent loop."""
        initial_state: NirmanState = {
            "raw_prompt": prompt,
            "spec": None,
            "capacity": None,
            "architecture": None,
            "scorecard": None,
            "iterations": 0,
            "max_iterations": max_iterations,
            "refinement_history": [],
            "dossier": None,
            "saved_files": None,
            "error": None,
        }

        final_state = self.graph.invoke(initial_state)
        return final_state
