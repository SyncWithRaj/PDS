# NirmanAI - Project Roadmap & Status

## Completed Milestones

- [x] **210k+ Dataset Curation & Processing**: Synthetically generated architecture dossiers and unified with open-source QnA pairs into `datasets/`.
- [x] **QLoRA Fine-Tuning Execution**: 100% completed on NVIDIA RTX A2000 GPU (Qwen2.5-7B-Instruct 4-bit).
- [x] **Local GPU Singleton Loader**: `LocalModelLoader` supports loading cached 4-bit base model + LoRA adapter directly.
- [x] **Autonomous ReAct Agent Engine**: Think-Act-Observe loop with retry, self-validation, schema self-correction, and tool sandbox (`search_web`, `read_url`, `python_repl`, `validate_mermaid`).
- [x] **Deterministic Capacity Math Engine**: Exact formulas for Read/Write QPS, 5-year storage growth, and cache RAM (Phase 2).
- [x] **Multi-Agent 6-Phase Pipeline Orchestration**: Implemented via LangGraph (`PromptEnhancer` -> `RequirementAnalyzer` -> `CapacityEstimator` -> `ArchitectureGenerator` / `ArchitectureEnhancer` -> `ExpertPanel` -> `Synthesizer`).
- [x] **Parallel 3-Expert Panel Debate**: Security Lead, Database Architect, and SRE Lead review in parallel, followed by Lead Architect reconciler applying patches.
- [x] **DRY Mermaid Styling**: Shared dark theme and node formatting rules unified in `nirman/prompts.py`.
- [x] **Multi-Key API Pool Rotation**: Automatic cycling across multiple Gemini API keys on HTTP 429 rate limits.
- [x] **Codebase Semantic Restructuring**: Clean directory structure categorizing agents (`core/`, `pipeline/`, `legacy/`), schemas (`pipeline/`, `legacy/`), tools (`research/`, `execution/`, `validation/`), and interfaces (`cli.py`, `web_ui.py`).
- [x] **End-to-End Agentic Validation**: Verified with full E2E run (`tests/e2e/test_e2e_agentic.py`) producing 93.2/100 Critic Audit Score and 86/100 Expert Panel Score.
- [x] **Interactive Web UI**: Standalone browser dashboard in `nirman/interfaces/web_ui.py`.
- [x] **Interactive Terminal CLI**: Rich CLI synthesizer in `nirman/interfaces/cli.py`.
- [x] **Automated Setup Scripts**: Cross-platform post-clone setup via `setup.ps1` (PowerShell) and `setup.sh` (Bash).

---

## 🔮 Upcoming Enhancements (Future Horizon)

- [ ] **Interactive Conversational Copilot**: Allow users to query the architecture or request targeted mutations (e.g., "Replace Redis with DynamoDB DAX", "Add a Kafka dead-letter topic") without regenerating from scratch.
- [ ] **Infrastructure-as-Code (IaC) Generation**: Automatically compile the validated architecture diagram into deployable Terraform modules or AWS CloudFormation templates.
- [ ] **Live Inter-Agent Debate Streaming**: Stream WebSocket updates to the web interface so users can observe the Security and Database experts debating in real time.
- [ ] **100% Offline Air-Gapped Mode**: Full pipeline execution using only local quantized models without external cloud dependencies.
