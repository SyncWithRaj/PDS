# NirmanAI - Project Roadmap & TODOs

## 📋 Upcoming Enhancements (Backlog)

### 1. Dedicated "Diagram Visualizer & Stylist Agent" (LangGraph Expansion)
- [ ] **Architecture**: Expand the current 7-agent LangGraph workflow into an **8-Agent Swarm** by introducing `DiagramVisualizerAgent`.
- [ ] **Workflow Position**: Placed between `ArchitectureGeneratorAgent` and `ArchitectureCriticAgent` (`Enhancer` → `Analyzer` → `Estimator` → `Generator` → **`DiagramVisualizer`** → `Critic` → `Refiner` → `Synthesizer`).
- [ ] **Agent Responsibility**:
  - Ingests raw components, data flows, and capacity metrics from the generator.
  - Generates rich, production-grade Mermaid.js diagrams with 2-line semantic cards:
    ```mermaid
    Kafka[["Apache Kafka Cluster<br/><b>Role:</b> High-throughput async ingestion of GPS pings & ride dispatch events"]]
    Postgres[("Amazon Aurora PostgreSQL<br/><b>Role:</b> ACID transactional store for ride payments & ledger")]
    ```
  - Enforces semantic node shapes: cylinders `[(...)]` for persistence, double brackets `[[...]]` for streaming queues, rectangles `[...]` for microservices.
  - Applies cohesive dark-mode SVG themes and subgraph boundaries.
- [ ] **Deterministic Fallback**: Include a Python enricher layer to guarantee 100% two-line card coverage if the LLM output is brief.

---

## 🚀 Immediate Next Steps
- [ ] **End-to-End Pipeline Test**: Run the full 7-phase LangGraph pipeline with the local fine-tuned model to verify everything works together.
- [ ] **Web UI Test**: Launch `web_ui.py`, submit a prompt, verify the HTML dashboard renders with dynamic trade-offs.

---

## ✅ Completed Milestones
- [x] **20k Gold Dataset Preparation**: Rich system design dossiers structured for instruction fine-tuning.
- [x] **QLoRA Fine-Tuning Execution**: 100% completed (1250/1250 steps, Epoch 1.0) on NVIDIA RTX A2000 12GB.
- [x] **Convergence Metrics**: Training loss dropped from `1.5285` to `0.2698`; token accuracy reached `91.46%`.
- [x] **Resilience & Checkpoint Recovery**: Resumed after unexpected power outages using saved optimizer and dataloader states.
- [x] **Direct Inference Quality Validation**: Validated via `training/test_model.py` generating accurate JSON dossiers, capacity estimations, and structured Mermaid topologies.
- [x] **Agent Architecture Audit**: Comprehensive audit of all 18 files identifying critical bugs, dead code, and anti-patterns (see `docs/agent_architecture_audit.md`).
- [x] **Full Agent Refactoring**: All 4 LLM agents refactored from thin wrappers to real agents with retry, self-validation, self-correction, and deterministic scoring.
- [x] **Synthesizer Dynamic Trade-Offs**: Replaced 100% hardcoded trade-offs with dynamic extraction from `arch.trade_offs` and `arch.bottleneck_mitigations`.
- [x] **CapacityEstimator Integration**: Wired as Phase 2 deterministic math node in LangGraph (was bypassed).
- [x] **PromptEnhancer Integration**: Wired as Phase 0 domain context enrichment node (was dead code).
- [x] **Orchestrator Deprecation**: Deleted broken 550-line `orchestrator.py`, all orchestration via LangGraph.
- [x] **State Rollback**: Added `best_architecture`/`best_score` tracking with automatic rollback on refinement regression.
- [x] **GeminiClient Fixes**: Fixed fictional model names, added native JSON mode, fixed `max_retries` parameter.
- [x] **Fine-Tuned Model Connected**: Created `LocalModelLoader` singleton with `GENERATOR_ENGINE=local` support — loads cached 4-bit base + LoRA adapter directly on RTX A2000 GPU.
