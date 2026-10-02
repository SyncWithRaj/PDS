"""
NirmanAI - LangGraph Agentic Architecture Workflow
====================================================
Production-grade state machine orchestrating TRUE autonomous agents across 6 phases:

Phase 0: PromptEnhancer      → ReAct agent: domain research + enhancement
Phase 1: Analyzer            → ReAct agent: compliance research + requirement extraction
Phase 2: CapacityEstimator   → ReAct agent: Python REPL calculations + benchmark validation
Phase 3: Generator           → ReAct agent: reference architecture research + design
Phase 4: ExpertPanel         → 3 independent ReAct experts (Security, DB, SRE) + Lead Architect
Phase 5: Synthesizer         → Template renderer (validates Mermaid)

Every agent has graceful fallback to direct Gemini structured call on ReAct failure.
"""

import os
import logging
from typing import Dict, Any, Optional
from langgraph.graph import StateGraph, END

from nirman.workflow.state import NirmanState
from nirman.agents.gemini_client import GeminiClient
from nirman.agents.enhancer import PromptEnhancer
from nirman.agents.analyzer import RequirementAnalyzerAgent
from nirman.agents.estimator import CapacityEstimator
from nirman.agents.generator import ArchitectureGeneratorAgent
from nirman.agents.architecture_enhancer import ArchitectureEnhancerAgent
from nirman.agents.expert_panel import ExpertPanelAgent
from nirman.agents.critic import ArchitectureCriticAgent
from nirman.agents.refiner import ArchitectureRefinerAgent
from nirman.agents.synthesizer import SynthesizerAgent

logger = logging.getLogger("nirman.workflow")


class NirmanWorkflow:
    """Agentic LangGraph multi-agent engine for distributed system architecture synthesis.
    
    Pipeline:
    Enhancer → Analyzer → Estimator → Generator → ExpertPanel → Synthesizer → END
    
    Every agent is a TRUE autonomous ReAct agent with tools, research, and self-reflection.
    The Expert Panel replaces the old Critic+Refiner loop with 3 independent expert agents.
    """

    def __init__(
        self,
        gemini_client: Optional[GeminiClient] = None,
        output_dir: str = "output",
        max_iterations: int = 2,
    ):
        self.client = gemini_client or GeminiClient()
        self.output_dir = output_dir
        self.max_iterations = max_iterations

        # Instantiate agents (all are now ReAct-powered)
        self.enhancer = PromptEnhancer(gemini_client=self.client)
        self.analyzer = RequirementAnalyzerAgent(self.client)
        self.estimator = CapacityEstimator(gemini_client=self.client)
        self.generator = ArchitectureGeneratorAgent(self.client)
        self.arch_enhancer = ArchitectureEnhancerAgent(self.client)
        self.expert_panel = ExpertPanelAgent(self.client)
        # Keep old agents as fallback (Expert Panel uses them internally if needed)
        self.critic = ArchitectureCriticAgent(self.client)
        self.refiner = ArchitectureRefinerAgent(self.client)
        self.synthesizer = SynthesizerAgent()

        # Build Graph
        self.graph = self._build_graph()

    def _build_graph(self):
        builder = StateGraph(NirmanState)

        # ──────────────────────────────────────────────────────────────
        # Phase 0: PromptEnhancer (Domain Context Enrichment)
        # ──────────────────────────────────────────────────────────────
        def enhancer_step(state: NirmanState) -> Dict[str, Any]:
            logger.info("🔮 Phase 0: PromptEnhancer (Domain Context Enrichment)...")
            try:
                enhanced_data = self.enhancer.enhance(state["raw_prompt"])
                enhanced_prompt = state["raw_prompt"]
                if isinstance(enhanced_data, dict) and enhanced_data.get("enhanced_prompt"):
                    enhanced_prompt = enhanced_data["enhanced_prompt"]
                elif isinstance(enhanced_data, str):
                    enhanced_prompt = enhanced_data
                logger.info("✅ PromptEnhancer enriched prompt with domain-specific context.")
                return {"enhanced_prompt": enhanced_prompt, "raw_prompt": enhanced_prompt}
            except Exception as e:
                logger.warning(f"⚠️ PromptEnhancer failed ({e}), using raw prompt.")
                return {"enhanced_prompt": state["raw_prompt"]}

        # ──────────────────────────────────────────────────────────────
        # Phase 1: RequirementAnalyzer (NLP Extraction + Self-Validation)
        # ──────────────────────────────────────────────────────────────
        def analyzer_step(state: NirmanState) -> Dict[str, Any]:
            logger.info("🔍 Phase 1: RequirementAnalyzerAgent (NLP Extraction + Capacity)...")
            try:
                spec, llm_capacity = self.analyzer.analyze(state["raw_prompt"])
                # Store LLM capacity as fallback; Phase 2 will override with deterministic math
                return {"spec": spec, "capacity": llm_capacity}
            except Exception as e:
                logger.error(f"❌ Phase 1 FAILED: {e}")
                return {"error": f"Analyzer failed: {str(e)}"}

        # ──────────────────────────────────────────────────────────────
        # Phase 2: CapacityEstimator (Deterministic Math Engine)
        # ──────────────────────────────────────────────────────────────
        def estimator_step(state: NirmanState) -> Dict[str, Any]:
            logger.info("📐 Phase 2: CapacityEstimator (Deterministic Math Engine)...")
            if state.get("error"):
                return {}  # Skip if previous phase failed
            try:
                deterministic_capacity = self.estimator.estimate(state["spec"])
                logger.info(
                    f"✅ Deterministic capacity: DAU={deterministic_capacity.traffic.dau:,}, "
                    f"Peak QPS={deterministic_capacity.traffic.peak_qps:,}, "
                    f"Storage 5yr={deterministic_capacity.storage.effective_5yr_storage_tb:.1f} TB"
                )
                return {"capacity": deterministic_capacity}
            except Exception as e:
                logger.warning(f"⚠️ CapacityEstimator failed ({e}), using LLM-estimated capacity as fallback.")
                # Keep LLM capacity from Phase 1 as fallback
                return {}

        # ──────────────────────────────────────────────────────────────
        # Phase 3: ArchitectureGenerator (Topology + Mermaid Synthesis)
        # ──────────────────────────────────────────────────────────────
        def generator_step(state: NirmanState) -> Dict[str, Any]:
            logger.info("Phase 3: ArchitectureGeneratorAgent (Topology Synthesis)...")
            if state.get("error"):
                return {}
            try:
                import os
                engine = os.getenv("GENERATOR_ENGINE", "gemini").lower()
                
                if engine == "local":
                    # Draft→Refine: Fine-tuned model generates raw architecture
                    logger.info("Phase 3a: Fine-tuned model generating domain-specific skeleton on GPU...")
                    raw_output = self.generator._generate_raw_local(
                        user_prompt=state["raw_prompt"],
                        spec=state["spec"],
                        capacity=state["capacity"],
                    )
                    # Phase 3b: Enhancement Agent enriches via Gemini
                    logger.info("Phase 3b: ArchitectureEnhancerAgent enriching via Gemini...")
                    arch = self.arch_enhancer.enhance(
                        raw_model_output=raw_output,
                        original_prompt=state["raw_prompt"],
                        spec=state["spec"],
                        capacity=state["capacity"],
                    )
                    logger.info(
                        f"Draft->Refine complete: "
                        f"{len(raw_output.get('component_breakdown', []))} base components -> "
                        f"{len(arch.components)} enhanced components"
                    )
                else:
                    # Direct Gemini generation (no enhancement needed)
                    arch = self.generator.generate(state["spec"], state["capacity"])
                
                return {"architecture": arch}
            except Exception as e:
                logger.error(f"Phase 3 FAILED: {e}")
                # Fallback: try direct Gemini generation if Draft→Refine failed
                try:
                    logger.info("Falling back to direct Gemini generation...")
                    arch = self.generator.generate(state["spec"], state["capacity"])
                    return {"architecture": arch}
                except Exception as e2:
                    logger.error(f"Fallback also failed: {e2}")
                    return {"error": f"Generator failed: {str(e)} | Fallback: {str(e2)}"}

        # ──────────────────────────────────────────────────────────────
        # Phase 4: Expert Panel (3 Independent Experts + Lead Architect)
        #   Replaces old Critic + Refiner cyclic loop
        # ──────────────────────────────────────────────────────────────
        def expert_panel_step(state: NirmanState) -> Dict[str, Any]:
            logger.info("🏛️ Phase 4: Expert Panel (Security + Database + SRE)...")
            if state.get("error"):
                return {}
            try:
                result = self.expert_panel.evaluate_and_refine(
                    architecture=state["architecture"],
                    spec=state["spec"],
                    capacity=state["capacity"],
                )

                # Use the refined architecture
                verdict = result.verdict
                logger.info(
                    f"✅ Expert Panel verdict: {verdict.consensus_score}/100 "
                    f"({'ACCEPTED' if verdict.accepted else 'NEEDS WORK'}) | "
                    f"{len(result.patches_applied)} patches applied"
                )

                # Build a scorecard-compatible object for the synthesizer
                # (backward compat with existing synthesizer that expects a scorecard)
                scorecard = self.critic.audit(state["spec"], state["capacity"], result.architecture)

                return {
                    "architecture": result.architecture,
                    "scorecard": scorecard,
                    "best_architecture": result.architecture,
                    "best_score": verdict.consensus_score,
                    "expert_verdict": {
                        "consensus_score": verdict.consensus_score,
                        "accepted": verdict.accepted,
                        "summary": verdict.verdict_summary,
                        "patches": result.patches_applied,
                        "risks": verdict.remaining_risks,
                    },
                }
            except Exception as e:
                logger.warning(f"⚠️ Expert Panel failed ({e}), falling back to old Critic...")
                try:
                    scorecard = self.critic.audit(state["spec"], state["capacity"], state["architecture"])
                    return {"scorecard": scorecard}
                except Exception as e2:
                    logger.error(f"❌ Critic fallback also failed: {e2}")
                    return {"error": f"Expert Panel and Critic both failed: {e} | {e2}"}

        # ──────────────────────────────────────────────────────────────
        # Phase 5: Synthesizer (Dynamic Dossier Compilation)
        # ──────────────────────────────────────────────────────────────
        def synthesizer_step(state: NirmanState) -> Dict[str, Any]:
            logger.info("📄 Phase 6: SynthesizerAgent (Compiling Dossier & Mermaid Dashboard)...")
            if state.get("error"):
                return {}
            try:
                # Use best architecture if available and better than current
                best_arch = state.get("best_architecture")
                best_score = state.get("best_score") or 0
                current_score = state["scorecard"].overall_score if state.get("scorecard") else 0

                if best_arch and best_score > current_score:
                    logger.info(
                        f"📈 Using best architecture (score {best_score}) over current (score {current_score})"
                    )
                    arch_to_use = best_arch
                else:
                    arch_to_use = state["architecture"]

                dossier = self.synthesizer.synthesize(
                    spec=state["spec"],
                    capacity=state["capacity"],
                    arch=arch_to_use,
                    scorecard=state["scorecard"],
                    refinements=state.get("refinement_history", []),
                )
                saved = self.synthesizer.save(dossier, output_dir=self.output_dir)
                return {"dossier": dossier, "saved_files": saved}
            except Exception as e:
                logger.error(f"❌ Phase 6 FAILED: {e}")
                return {"error": f"Synthesizer failed: {str(e)}"}

        # ══════════════════════════════════════════════════════════════
        # Build the LangGraph State Machine (Linear Agentic Flow)
        # ══════════════════════════════════════════════════════════════

        # Add Nodes
        builder.add_node("enhancer", enhancer_step)
        builder.add_node("analyzer", analyzer_step)
        builder.add_node("estimator", estimator_step)
        builder.add_node("generator", generator_step)
        builder.add_node("expert_panel", expert_panel_step)
        builder.add_node("synthesizer", synthesizer_step)

        # Define Edges: Linear agentic flow
        # Enhancer → Analyzer → Estimator → Generator → ExpertPanel → Synthesizer → END
        builder.set_entry_point("enhancer")
        builder.add_edge("enhancer", "analyzer")
        builder.add_edge("analyzer", "estimator")
        builder.add_edge("estimator", "generator")
        builder.add_edge("generator", "expert_panel")
        builder.add_edge("expert_panel", "synthesizer")
        builder.add_edge("synthesizer", END)

        return builder.compile()

    def run(self, prompt: str, max_iterations: int = 2) -> Dict[str, Any]:
        """Executes the full LangGraph agentic pipeline.
        
        Pipeline:
        Enhancer → Analyzer → Estimator → Generator → ExpertPanel → Synthesizer
        
        Every agent is a TRUE autonomous ReAct agent that researches, thinks, and acts.
        """
        initial_state: NirmanState = {
            "raw_prompt": prompt,
            "enhanced_prompt": None,
            "spec": None,
            "capacity": None,
            "architecture": None,
            "scorecard": None,
            "iterations": 0,
            "max_iterations": max_iterations,
            "refinement_history": [],
            "best_architecture": None,
            "best_score": None,
            "expert_verdict": None,
            "dossier": None,
            "saved_files": None,
            "error": None,
        }

        logger.info("=" * 70)
        logger.info("🚀 NirmanAI LangGraph Multi-Agent Pipeline Starting...")
        logger.info(f"   Prompt: {prompt[:100]}...")
        logger.info(f"   Max Refinement Iterations: {max_iterations}")
        logger.info("=" * 70)

        final_state = self.graph.invoke(initial_state)

        if final_state.get("error"):
            logger.error(f"⚠️ Pipeline completed with error: {final_state['error']}")
        else:
            logger.info("✅ Pipeline completed successfully!")
            if final_state.get("saved_files"):
                for fmt, path in final_state["saved_files"].items():
                    logger.info(f"   📄 {fmt.upper()}: {path}")

        return final_state
