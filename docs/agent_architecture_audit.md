# NirmanAI Agent Architecture — Honest Audit Report

> **Audit Date**: 01-Oct-2026  
> **Audited Files**: All 18 agent, workflow, schema, and client files  
> **Verdict**: The foundation (LangGraph + Pydantic schemas) is solid, but there are **critical bugs, dead code, and architectural anti-patterns** that need fixing before a serious demo.

---

## 📊 Agent-by-Agent Scorecard

| Agent | Is It a Real Agent? | Uses LLM? | Error Handling | Prompt Quality | Verdict |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **RequirementAnalyzer** | ❌ Single-shot wrapper | ✅ Gemini | ❌ Zero try-except | ⚠️ Fair | Needs error handling + math delegation |
| **CapacityEstimator** | ❌ Pure math utility | ❌ None | ⚠️ Basic | N/A | **Bypassed in LangGraph — never called!** |
| **ArchitectureGenerator** | ❌ Single-shot wrapper | ✅ Gemini/Ollama | ⚠️ Ollama fallback only | ✅ Good | Needs Mermaid validation |
| **ArchitectureCritic** | ❌ Single-shot wrapper | ✅ Gemini | ❌ Zero try-except | ✅ Strong rubric | LLM math is unreliable for scoring |
| **ArchitectureRefiner** | ❌ Single-shot wrapper | ✅ Gemini | ❌ Zero try-except | ⚠️ Moderate | Rewrites entire arch instead of patching |
| **SynthesizerAgent** | ❌ Template engine | ❌ None | ⚠️ Fair | N/A | **Trade-offs are 100% hardcoded strings!** |
| **PromptEnhancer** | ❌ Rule-based preprocessor | ❌ None | N/A | N/A | **Dead code — never called anywhere!** |
| **NirmanOrchestrator** | ❌ Procedural while-loop | ❌ None | ❌ Broken | N/A | **Crashes on execution — broken signatures!** |

---

## 🔴 Critical Issues (Must Fix)

### 1. The Orchestrator is Broken — Two Competing Systems
Your codebase has TWO orchestration engines that are out of sync:
- **LangGraph** (`nirman/workflow/graph.py`) — Used by the Web UI. This one actually works.
- **Procedural Orchestrator** (`nirman/agents/orchestrator.py`) — Used by CLI. **This one crashes** because it passes `use_llm=True` to agents that don't accept that parameter, and it unpacks return values incorrectly.

Additionally, `orchestrator.py` duplicates ~450 lines of `SynthesizerAgent` code verbatim.

### 2. CapacityEstimator Is Completely Bypassed
You built a proper deterministic math engine (`CapacityEstimator`) that correctly calculates QPS, storage, cache sizing, and pod counts. But in the LangGraph workflow, the `analyzer_step` asks the **LLM to do floating-point arithmetic** instead of using this engine.

LLMs are notoriously bad at math. This means your capacity numbers (`peak_qps`, `storage_per_year`, `cache_memory`) are **hallucinated guesses** rather than deterministic calculations.

### 3. Synthesizer Outputs Fake Trade-Offs
In `synthesizer.py` (lines 50-87), the architectural trade-offs and bottleneck mitigations are **100% hardcoded static strings**. Whether the user asks for a payment system, a gaming server, or an IoT pipeline, the output always says the same thing about "Polyglot Persistence Layer" and "Asynchronous Event Streaming Backbone".

An evaluator who runs two different prompts and sees identical trade-offs will immediately know it's faked.

### 4. Zero Error Handling in 4 LLM Agents
The Analyzer, Critic, Refiner, and Generator (Gemini path) have **zero try-except blocks**. If the Gemini API returns malformed JSON, hits a rate limit, or times out, the entire LangGraph execution crashes with an unhandled exception.

### 5. PromptEnhancer Is Dead Code
`PromptEnhancer` is defined in `enhancer.py` but is **never imported or called** anywhere — not in the LangGraph workflow, not in the orchestrator, not in the CLI, not in the Web UI.

---

## 🟡 Architectural Anti-Patterns

### 6. Agents Are Not True Agents — They're Wrappers
In modern agentic AI (as defined by Google DeepMind, Anthropic, and OpenAI), an "agent" should be able to:
- **Plan** (break down tasks into sub-steps)
- **Use Tools** (call APIs, databases, calculators)
- **Reflect** (evaluate its own output and retry)
- **Maintain Memory** (track context across interactions)

Your current agents do **none of these**. Each one is a single-shot LLM API call wrapped in a class method. They cannot plan, cannot use tools, cannot reflect on their output, and have no memory.

### 7. GeminiClient Doesn't Use Native Structured Output
Gemini's API natively supports `response_mime_type="application/json"` and `response_schema` in `generationConfig`. Instead, your client:
1. Injects the JSON schema into the prompt text (wasting tokens)
2. Parses the response with regex brace-matching
3. Falls back to `json_repair`

This is fragile and wastes ~500 tokens per call on schema injection.

### 8. No State Rollback in Refinement Loop
When the Refiner produces a new architecture, it **completely replaces** the previous one in state. If the refinement accidentally makes the architecture worse (LLMs do this), there's no rollback to the previous best version. The Critic just sees the degraded version.

### 9. Fictional Fallback Model Names
In `gemini_client.py`, the fallback model chain includes `"gemini-3.5-flash"` and `"gemini-3.1-flash-lite"` — these are **not real Google model IDs** and will return 404 errors.

---

## ✅ What's Actually Good

1. **LangGraph Cyclic Workflow**: The conditional `route_critic` → `refiner` → `critic` feedback loop is a genuinely solid architecture pattern. This is the right way to use LangGraph.
2. **Pydantic v2 Schema Contracts**: Every agent boundary is enforced by typed schemas (`RequirementSpec`, `SystemArchitecture`, `CriticScorecard`, `SurgicalPatch`). This prevents hallucination drift between agents.
3. **5-Key Circular API Pool**: The key rotation with HTTP 429 detection and auto-rotation is a clever resilience mechanism.
4. **Dual Engine (Ollama + Gemini)**: The Generator's ability to use either local fine-tuned model or cloud Gemini is a strong architectural feature.
5. **Fine-Tuned Local LLM**: Having a custom-trained `nirmanai:7b` model is genuinely impressive and differentiates from generic API-wrapper projects.

---

## 🛠️ Recommended Fixes (Priority Order)

### P0 — Must Fix Before Demo
1. **Delete `orchestrator.py`** — Route CLI through `NirmanWorkflow` (LangGraph). Eliminates 450 lines of broken duplicate code.
2. **Wire `CapacityEstimator` into LangGraph** — Add it as a node between `analyzer` and `generator`. Never let the LLM do arithmetic.
3. **Add try-except to all 4 LLM agents** — Catch JSON parse errors, API timeouts, and rate limits. Return structured error states instead of crashing.
4. **Make Synthesizer use actual LLM-generated trade-offs** — Add `trade_offs` and `bottleneck_mitigations` fields to `SystemArchitecture` schema so the Generator fills them dynamically per prompt.

### P1 — Should Fix
5. **Use Gemini native structured output** — Add `response_mime_type="application/json"` and `response_schema` to `generationConfig`.
6. **Add state rollback** — Track `best_architecture` and `best_score` in `NirmanState`. Only replace if the new score is higher.
7. **Fix model fallback names** — Replace fictional model IDs with real ones (`gemini-2.0-flash`, `gemini-1.5-flash`).
8. **Integrate PromptEnhancer** — Wire it as the first node in LangGraph or delete the dead code.

### P2 — Nice to Have
9. **Add Mermaid syntax validation** — Parse the generated diagram before sending to client.
10. **Add LangGraph checkpointing** — Use `MemorySaver` for state persistence and run history.
11. **True agentic behavior** — Give agents tool-calling capabilities (e.g., Critic could call a rules engine, Generator could query a component catalog).
