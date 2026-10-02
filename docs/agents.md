# NirmanAI — True Agentic Architecture

> **Mission:** Transform every component from a "glorified API wrapper" into a truly autonomous ReAct agent with tools, planning, research, and self-reflection.

---

## The Problem: What We Have Now

Every "agent" in our pipeline is a **single Gemini API call** wrapped in a class. None of them think, plan, research, or use tools. They are **prompt-in, JSON-out transformers** — not agents.

### Current Reality Check

| Component | What We Call It | What It Actually Does | Agentic? |
|:---|:---|:---|:---:|
| PromptEnhancer | "LLM Agent" | Single Gemini call → returns JSON | ❌ |
| RequirementAnalyzer | "Agent" | Gemini call + Pydantic retry | ❌ |
| CapacityEstimator | "Agent" | Hardcoded Python math formulas | ❌ |
| ArchitectureGenerator | "Agent" | GPU inference → Gemini enhancement | ❌ |
| ArchitectureEnhancer | "Agent" | Gemini call + validation retry | ❌ |
| ArchitectureCritic | "Agent" | Gemini call + deterministic math | ❌ |
| ArchitectureRefiner | "Agent" | Gemini call + retry on parse failure | ❌ |
| Synthesizer | "Agent" | Python template rendering | ❌ |

**Verdict:** 0/8 are actual agents. The pipeline works, but it's a **chain of prompts**, not an agentic system.

---

## The Solution: ReAct Agent Architecture

### What Makes a Real Agent

A real agent runs an **autonomous reasoning loop**:

```
while not satisfied:
    THINK   →  "What do I need to figure out next?"
    PLAN    →  "I should search for AWS RAG reference architectures"
    ACT     →  Execute a tool (search_web, run_python, read_docs)
    OBSERVE →  Read the tool's output
    REFLECT →  "Is this enough? Should I dig deeper or move on?"
```

The key difference: **The agent decides its own next action.** We don't hardcode the flow. The agent has tools and autonomously chooses which ones to use, when, and how many times.

### Agent vs Wrapper Comparison

```python
# ❌ WRAPPER (what we have now)
def enhance(prompt):
    result = gemini.call(system_prompt, prompt, schema=OutputSchema)
    return result  # One shot. No thinking. No tools. No research.

# ✅ AGENT (what we're building)
def enhance(prompt):
    agent = ReActAgent(
        goal=f"Deeply understand '{prompt}' and create comprehensive spec",
        persona="Principal Product Manager & Systems Analyst",
        tools=[search_web, read_url, python_repl],
        output_schema=EnhancedPromptSpec,
    )
    return agent.run()  # Agent autonomously researches, thinks, acts, reflects
```

---

## System Architecture

### Layer 1: Tool Registry

Shared tools that any agent can call. Each tool is a Python class with a `name`, `description`, `parameters` schema, and an `execute()` method.

```
nirman/tools/
├── __init__.py
├── registry.py          # ToolRegistry class - agents pick what they need
├── search_web.py        # Google search via SerpAPI/Tavily → top results
├── read_url.py          # Scrape & read a webpage, return markdown content
├── python_repl.py       # Execute Python code in a sandboxed subprocess
└── validate_mermaid.py  # Parse Mermaid syntax, return errors or "valid"
```

#### Tool Interface

```python
class Tool:
    name: str                    # e.g. "search_web"
    description: str             # Human-readable description for the LLM
    parameters: dict             # JSON Schema of input parameters
    
    def execute(self, **kwargs) -> str:
        """Run the tool and return a string observation."""
        ...
```

#### Tool Descriptions (for LLM function calling)

| Tool | Name | Description | When An Agent Uses It |
|:---|:---|:---|:---|
| **SearchWeb** | `search_web` | Search Google for a query. Returns top 5 results with titles, snippets, and URLs. | Before designing anything — research latest patterns, benchmarks, and reference architectures |
| **ReadURL** | `read_url` | Fetch and read a webpage. Returns the page content as clean markdown text. | After finding a relevant URL from search — deep-read an AWS blog, architecture doc, or benchmark report |
| **PythonREPL** | `python_repl` | Execute Python code in a sandboxed subprocess. Returns stdout/stderr. Max 30s timeout. | Calculate capacity math, validate data structures, run quick computations, test formulas |
| **ValidateMermaid** | `validate_mermaid` | Parse a Mermaid diagram string and check for syntax errors. Returns "valid" or error details. | After generating a diagram — self-check before submitting |

### Layer 2: ReAct Engine

The core agentic reasoning loop. Every agent in NirmanAI uses this engine.

```
nirman/agents/
├── react_engine.py      # The shared ReAct loop (THINK → ACT → OBSERVE)
```

#### ReAct Engine Design

```python
class ReActEngine:
    """
    Core autonomous agent loop.
    
    The engine sends the LLM a prompt with:
    - The agent's GOAL (what it needs to accomplish)
    - The agent's PERSONA (who it is)
    - Available TOOLS (with descriptions and parameter schemas)
    - Conversation HISTORY (previous thoughts, actions, observations)
    - Output SCHEMA (what the final answer must look like)
    
    The LLM responds with either:
    - A THOUGHT + ACTION (use a tool) → engine executes tool, adds observation
    - A FINAL_ANSWER (structured output) → engine returns it
    """
    
    def __init__(self, gemini_client, persona, tools, output_schema, max_steps=10):
        self.client = gemini_client
        self.persona = persona
        self.tools = tools
        self.output_schema = output_schema
        self.max_steps = max_steps
    
    def run(self, goal: str) -> BaseModel:
        history = []
        
        for step in range(self.max_steps):
            # Ask LLM: "Given your goal, history, and tools — what next?"
            response = self._think(goal, history)
            
            if response.type == "FINAL_ANSWER":
                # Agent is satisfied — return structured output
                return self._parse_final_answer(response.content)
            
            elif response.type == "TOOL_CALL":
                # Agent wants to use a tool
                tool = self.tools[response.tool_name]
                observation = tool.execute(**response.tool_args)
                
                history.append({
                    "step": step + 1,
                    "thought": response.reasoning,
                    "action": f"{response.tool_name}({response.tool_args})",
                    "observation": observation[:2000],  # truncate long outputs
                })
        
        # Max steps reached — force final answer from current knowledge
        return self._force_final_answer(goal, history)
```

#### ReAct Prompt Template

```
You are {persona}.

YOUR GOAL: {goal}

You have access to the following tools:
{tool_descriptions}

CONVERSATION SO FAR:
{history}

RULES:
1. Think step-by-step about what you need to do next.
2. If you need more information, use a tool.
3. If you have enough information, provide your FINAL_ANSWER.
4. Your final answer MUST match this JSON schema: {output_schema}

Respond in this exact format:

THOUGHT: [Your reasoning about what to do next]
ACTION: [tool_name]
ACTION_INPUT: [tool arguments as JSON]

OR if you're ready to answer:

THOUGHT: [Your reasoning about why you're ready]
FINAL_ANSWER: [Your structured JSON output]
```

### Layer 3: Agentic Components

Each agent is a thin wrapper around ReActEngine with a specific persona and tool set.

---

## Agent Specifications

### Agent 1: Prompt Enhancer Agent

**Current:** Single Gemini API call with fallback.

**Agentic Upgrade:**

| Property | Value |
|:---|:---|
| **Persona** | Principal Product Manager & Distributed Systems Analyst (15yr FAANG) |
| **Goal** | "Deeply understand the user's TRUE intent and create a comprehensive architecture specification" |
| **Tools** | `search_web`, `read_url` |
| **Output Schema** | `EnhancedPromptSpec` |
| **Max Steps** | 8 |

**Example Autonomous Behavior:**
```
User Input: "Build me a LegalTrace app"

Step 1:
  THOUGHT: "LegalTrace sounds like a legal tech product. Let me research what 
            legal tech architectures look like in production."
  ACTION: search_web
  ACTION_INPUT: {"query": "legal tech RAG architecture best practices 2024"}
  OBSERVATION: [5 results about legal AI, RAG patterns, court case search]

Step 2:
  THOUGHT: "The first result from AWS looks relevant. Let me read it in detail."
  ACTION: read_url
  ACTION_INPUT: {"url": "https://aws.amazon.com/blogs/...legal-rag-architecture"}
  OBSERVATION: [Full article about using Bedrock + Knowledge Bases for legal RAG]

Step 3:
  THOUGHT: "Now I understand the domain. Legal RAG needs: document ingestion with 
            OCR, vector embeddings, hybrid search (BM25 + semantic), citation 
            grounding to prevent hallucination, and strict compliance (GDPR, SOC2, 
            eDiscovery). The user didn't mention any of this, but it's mandatory."
  FINAL_ANSWER: {
    "detected_domain": "Legal Tech - AI-Powered Case Research & RAG",
    "detected_scale": "100K DAU",
    "unstated_features": [
      "Document ingestion pipeline with OCR (Tesseract/Textract)",
      "Hybrid search (BM25 keyword + vector semantic)",
      "Citation grounding engine to prevent LLM hallucination",
      "Multi-tenant data isolation",
      "Audit trail for all searches (eDiscovery compliance)",
      "Role-based access control (attorney, paralegal, admin)"
    ],
    "implicit_slas": [
      "P99 < 500ms for search results",
      "P99 < 3s for LLM-generated case summary",
      "99.9% availability",
      "< 30min document ingestion latency"
    ],
    "compliance_requirements": ["SOC2 Type II", "GDPR", "eDiscovery"],
    "enhanced_prompt": "..."
  }
```

---

### Agent 2: Requirement Analyzer Agent

**Current:** Single Gemini call with retry on validation failure.

**Agentic Upgrade:**

| Property | Value |
|:---|:---|
| **Persona** | Staff Solutions Architect & Requirements Engineer |
| **Goal** | "Extract precise, validated functional and non-functional requirements" |
| **Tools** | `search_web`, `read_url` |
| **Output Schema** | `RequirementSpec` |
| **Max Steps** | 6 |

**Example Autonomous Behavior:**
```
Step 1:
  THOUGHT: "The enhanced prompt mentions SOC2 and eDiscovery compliance.
            Let me verify what specific technical requirements those impose."
  ACTION: search_web
  ACTION_INPUT: {"query": "SOC2 Type II technical requirements cloud architecture"}
  OBSERVATION: [Results about encryption at rest, audit logging, access controls]

Step 2:
  THOUGHT: "SOC2 requires AES-256 encryption at rest, TLS 1.3 in transit,
            centralized audit logging, and annual penetration testing. Let me
            also check eDiscovery requirements."
  ACTION: search_web
  ACTION_INPUT: {"query": "eDiscovery technical requirements legal hold data retention"}
  OBSERVATION: [Results about immutable storage, litigation hold, chain of custody]

Step 3:
  THOUGHT: "Now I have enough context. eDiscovery requires immutable audit logs,
            7-year data retention, and legal hold capability. I'll add these as
            non-functional requirements that the user never mentioned but are
            legally mandatory."
  FINAL_ANSWER: { RequirementSpec with researched, validated requirements }
```

---

### Agent 3: Capacity Estimator Agent

**Current:** Hardcoded Python math formulas. No intelligence.

**Agentic Upgrade:**

| Property | Value |
|:---|:---|
| **Persona** | Principal Performance Engineer & Capacity Planner |
| **Goal** | "Calculate precise, validated capacity estimates using real-world benchmarks" |
| **Tools** | `python_repl`, `search_web` |
| **Output Schema** | `CapacityMetrics` |
| **Max Steps** | 8 |

**Example Autonomous Behavior:**
```
Step 1:
  THOUGHT: "I need to calculate QPS for a legal search system with 100K DAU.
            Legal searches are different from social media — users do fewer
            but longer queries. Let me estimate."
  ACTION: python_repl
  ACTION_INPUT: {"code": "
    dau = 100_000
    searches_per_user_per_day = 15  # legal researchers do deep searches
    active_seconds = 8 * 3600  # 8-hour workday, not 24h
    avg_qps = dau * searches_per_user_per_day / active_seconds
    peak_multiplier = 3  # legal has morning spikes, not 5x like social
    peak_qps = avg_qps * peak_multiplier
    print(f'Avg QPS: {avg_qps:.1f}, Peak QPS: {peak_qps:.1f}')
  "}
  OBSERVATION: "Avg QPS: 52.1, Peak QPS: 156.3"

Step 2:
  THOUGHT: "Let me validate this against real-world legal search benchmarks."
  ACTION: search_web
  ACTION_INPUT: {"query": "legal search engine QPS benchmark Westlaw Elasticsearch"}
  OBSERVATION: [Results suggesting 100-500 QPS for legal search at this scale]

Step 3:
  THOUGHT: "My estimate of 156 peak QPS aligns with industry benchmarks. 
            Now let me calculate storage for 50M court documents."
  ACTION: python_repl
  ACTION_INPUT: {"code": "
    total_docs = 50_000_000
    avg_doc_size_kb = 75  # court docs are longer than average
    raw_storage_tb = total_docs * avg_doc_size_kb / 1024 / 1024 / 1024
    vector_storage_tb = total_docs * 1536 * 4 / 1024**4  # 1536-dim embeddings
    total_tb = raw_storage_tb + vector_storage_tb
    replicated_tb = total_tb * 3  # 3x replication
    print(f'Raw: {raw_storage_tb:.2f} TB')
    print(f'Vectors: {vector_storage_tb:.2f} TB')
    print(f'Total (3x replicated): {replicated_tb:.2f} TB')
  "}
  OBSERVATION: "Raw: 3.49 TB\nVectors: 0.27 TB\nTotal (3x replicated): 11.27 TB"

Step 4:
  THOUGHT: "Good. The numbers are validated. Legal docs at 75KB average is
            realistic. Let me compile the full capacity report."
  FINAL_ANSWER: { CapacityMetrics with computed + validated numbers }
```

---

### Agent 4: Architecture Designer Agent

**Current:** GPU model generates skeleton → Gemini expands to 14 components. No research.

**Agentic Upgrade:**

| Property | Value |
|:---|:---|
| **Persona** | Distinguished Architect & Chief Systems Designer |
| **Goal** | "Design a production-grade system architecture backed by real-world research and validated patterns" |
| **Tools** | `search_web`, `read_url`, `python_repl`, `validate_mermaid` |
| **Output Schema** | `SystemArchitecture` |
| **Max Steps** | 12 |

**Example Autonomous Behavior:**
```
Step 1:
  THOUGHT: "I need to design a legal RAG system. Before I start, let me
            research how real companies have built similar systems."
  ACTION: search_web
  ACTION_INPUT: {"query": "retrieval augmented generation architecture diagram 2024"}
  OBSERVATION: [Results with RAG architecture patterns]

Step 2:
  THOUGHT: "Let me read the top result — it looks like a detailed reference arch."
  ACTION: read_url
  ACTION_INPUT: {"url": "https://...rag-reference-architecture"}
  OBSERVATION: [Detailed article about RAG with ingestion, chunking, embedding,
                retrieval, reranking, and generation stages]

Step 3:
  THOUGHT: "Good. The standard RAG pattern has 6 stages. But for legal, I also
            need citation grounding (anti-hallucination) and hybrid search.
            Let me research hybrid search architectures."
  ACTION: search_web
  ACTION_INPUT: {"query": "hybrid search BM25 vector OpenSearch vs Elasticsearch"}
  OBSERVATION: [Comparison articles]

Step 4-8:
  [Agent continues researching, reading docs, building component list]

Step 9:
  THOUGHT: "I now have enough knowledge to design the architecture. Let me
            create the Mermaid diagram and validate it."
  ACTION: validate_mermaid
  ACTION_INPUT: {"diagram": "flowchart TD\n  ..."}
  OBSERVATION: "Error: Line 23 - unclosed bracket"

Step 10:
  THOUGHT: "Syntax error on line 23. Let me fix the bracket."
  ACTION: validate_mermaid
  ACTION_INPUT: {"diagram": "flowchart TD\n  ... [fixed]"}
  OBSERVATION: "Valid. 14 nodes, 18 edges detected."

Step 11:
  THOUGHT: "Diagram is valid. Now I'll compile the full architecture."
  FINAL_ANSWER: { SystemArchitecture with researched components + validated diagram }
```

---

### Agent 5: Expert Panel (Replaces Critic + Refiner)

**Current:** Single Critic scores → single Refiner patches → mechanical loop.

**Agentic Upgrade:** Three independent expert agents that each autonomously research and critique, plus a Lead Architect that resolves conflicts.

| Expert Agent | Persona | Tools | Focus Area |
|:---|:---|:---|:---|
| **Security Architect** | "CISO with 20yr experience in zero-trust architecture" | `search_web`, `read_url` | Encryption, auth, compliance, attack vectors |
| **Database Engineer** | "Principal Database Engineer, ex-Amazon DynamoDB team" | `search_web`, `python_repl` | Schema design, consistency models, replication, query patterns |
| **SRE / Infrastructure Lead** | "Staff SRE at Google, authored SRE Handbook chapter" | `search_web`, `python_repl` | SPOFs, failover, blast radius, observability, capacity validation |

**How the Panel Works:**

```
1. Each expert agent receives the architecture
2. Each expert INDEPENDENTLY runs a ReAct loop:
   - Researches best practices in their domain
   - Identifies specific flaws with evidence
   - Proposes concrete fixes
3. The Lead Architect agent receives ALL critiques
4. Lead Architect resolves conflicts and applies patches
5. If consensus score >= 85 → Accept
6. If not → Another round of debate (max 2 rounds)
```

**Example: Security Architect Agent**
```
Step 1:
  THOUGHT: "Let me check if this legal system has proper data encryption.
            Legal data is extremely sensitive — court documents, client info."
  ACTION: search_web
  ACTION_INPUT: {"query": "legal document management encryption requirements SOC2"}
  OBSERVATION: [Results about AES-256 at rest, TLS 1.3 in transit, field-level
                encryption for PII]

Step 2:
  THOUGHT: "The architecture uses Aurora Postgres but doesn't mention
            encryption at rest. This is a SOC2 violation. Also, I don't see
            any mention of field-level encryption for PII in court documents.
            Let me check if the API Gateway has rate limiting configured."
  ACTION: search_web
  ACTION_INPUT: {"query": "API gateway security best practices DDoS legal platform"}
  OBSERVATION: [Results about WAF rules, rate limiting, IP whitelisting]

Step 3:
  THOUGHT: "I've found 3 critical security issues:
            1. No encryption at rest specified for Aurora
            2. No field-level encryption for PII in documents
            3. No WAF rules specified for the CDN edge
            I'll report these with specific remediation steps."
  FINAL_ANSWER: {
    "expert": "Security Architect",
    "overall_assessment": "CRITICAL GAPS",
    "findings": [
      {
        "severity": "CRITICAL",
        "component": "Aurora PostgreSQL",
        "flaw": "No encryption at rest specified",
        "evidence": "SOC2 CC6.1 requires encryption of sensitive data at rest",
        "fix": "Enable Aurora encryption with AWS KMS CMK, rotate keys every 90 days"
      },
      ...
    ]
  }
```

---

### Agent 6: Synthesizer

**Stays mostly as-is.** This is a template renderer — it doesn't need to be agentic. It takes structured data and formats it into Markdown + HTML. Making it agentic would add latency without adding value.

The only enhancement: use the `validate_mermaid` tool to verify diagrams before rendering.

---

## Implementation Roadmap

### Phase 1: Foundation (Tools + ReAct Engine)

```
Files to create:
  nirman/tools/__init__.py
  nirman/tools/registry.py
  nirman/tools/search_web.py
  nirman/tools/read_url.py
  nirman/tools/python_repl.py
  nirman/tools/validate_mermaid.py
  nirman/agents/react_engine.py
```

This is the foundation. Once built, converting each agent is straightforward.

### Phase 2: Convert Agents (One by One)

```
Files to modify:
  nirman/agents/enhancer.py          → ReAct with [search_web, read_url]
  nirman/agents/analyzer.py          → ReAct with [search_web, read_url]
  nirman/agents/estimator.py         → ReAct with [python_repl, search_web]
  nirman/agents/generator.py         → ReAct with [search_web, read_url, python_repl, validate_mermaid]
  nirman/agents/architecture_enhancer.py → ReAct with [search_web, read_url, validate_mermaid]
```

### Phase 3: Expert Panel

```
Files to create:
  nirman/agents/expert_panel.py      → Multi-agent debate system
  nirman/agents/experts/security.py  → Security Architect persona
  nirman/agents/experts/database.py  → Database Engineer persona
  nirman/agents/experts/sre.py       → SRE / Infra Lead persona

Files to delete:
  nirman/agents/critic.py            → Replaced by expert panel
  nirman/agents/refiner.py           → Replaced by expert panel
```

### Phase 4: Rewire Workflow

```
Files to modify:
  nirman/workflow/graph.py           → Dynamic orchestration instead of rigid phases
  nirman/workflow/state.py           → Add research_context, expert_findings to state
```

---

## Expected Outcome

### Before (Pipeline)
- User says "Build LegalTrace" → Pipeline fills JSON schemas → Gets 81.55/100
- No research. No validation against real-world patterns. No expert debate.
- Every run produces similar quality regardless of domain complexity.

### After (Agentic)
- User says "Build LegalTrace" → Agents research legal tech, read AWS docs, calculate capacity with custom Python, design based on real patterns, three experts independently audit the design with evidence-based critiques
- Research-backed decisions. Validated math. Expert consensus.
- Complex domains get more research steps. Simple domains get fewer. The agents adapt autonomously.

### Quality Metrics Target

| Metric | Before (Pipeline) | After (Agentic) |
|:---|:---:|:---:|
| Critic Score | 78-91/100 | 88-95/100 |
| Research-Backed Decisions | 0 | 3-5 per run |
| Self-Validated Math | No | Yes (Python REPL) |
| Expert Perspectives | 1 (single critic) | 3 (security, DB, SRE) |
| Mermaid Syntax Errors | Occasional | 0 (pre-validated) |
| Adaptation to Domain | Fixed formula | Dynamic research |

---

## Technical Notes

### API Key Management
- Each ReAct agent may make 3-8 tool calls + 3-8 LLM reasoning calls per run
- With 7 agents × ~6 LLM calls each = ~42 Gemini calls per pipeline run
- Our 5-key rotation system handles ~50 calls before hitting 429s
- May need to add delays between agent runs or use Gemini's batch API

### Latency Budget
- Current pipeline: ~8 minutes (GPU inference dominates)
- Agentic pipeline: ~12-15 minutes (added research + debate steps)
- Tradeoff: Slower but dramatically higher quality and real-world grounding

### Fallback Strategy
- Every ReAct agent has a `max_steps` limit (default: 8-12)
- If tools fail (network error, rate limit), agent continues with available knowledge
- If agent can't produce output within max_steps, falls back to direct Gemini call
- The pipeline never crashes — graceful degradation at every level
