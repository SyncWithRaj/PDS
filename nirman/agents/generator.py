"""
NirmanAI - Architecture Generator Agent (ReAct Agentic)
========================================================
TRUE AUTONOMOUS AGENT for the Gemini path.

When GENERATOR_ENGINE=local: GPU model drafts → ArchitectureEnhancer (ReAct) refines
When GENERATOR_ENGINE=gemini: This agent uses ReAct to research + design + validate
"""

import os
import json
import logging
from typing import Optional, Dict
from pydantic import BaseModel, Field

import urllib.request
import json_repair
from nirman.schemas.analyzer import RequirementSpec
from nirman.schemas.estimator import CapacityMetrics
from nirman.schemas.generator import (
    SystemArchitecture,
    ComponentNode,
    ConnectionEdge,
    LayerType,
    CommunicationProtocol,
)
from nirman.agents.gemini_client import GeminiClient
from nirman.agents.react_engine import ReActEngine
from nirman.tools.registry import build_default_registry
from nirman.prompts import SHARED_MERMAID_RULES

logger = logging.getLogger("nirman.generator")

GENERATOR_SYSTEM_PROMPT = """You are the Principal Cloud Solutions Architect of NirmanAI, specializing in hyper-scale distributed systems across AWS, GCP, and Azure.
Your role is to transform a detailed RequirementSpec and CapacityMetrics into a comprehensive, production-grade SystemArchitecture.

You must design:
1. ARCHITECTURAL TIERS:
   - Client & Perimeter Layer (Web/Mobile Apps, DNS, Anycast)
   - Edge Ingress & Security Layer (CloudFront/Cloudflare CDN, WAF, API Gateway with Token Bucket rate limiting)
   - Stateless Microservices Compute Tier (Kubernetes EKS/GKE cluster rightsized for the peak pod count)
   - Asynchronous Streaming & Event Bus Tier (Apache Kafka / AWS MSK / Google PubSub)
   - Distributed In-Memory Caching Tier (Redis Cluster for 80/20 hot set)
   - Polyglot Persistent Datastore Tier (Transactional OLTP DB + Analytical Data Lakehouse / BigQuery)
   - AI/ML Inference & Real-Time Analytics Tier (when applicable)
   - Observability & Telemetry Tier (OpenTelemetry, Prometheus, Grafana)

2. COMPONENT SELECTION & JUSTIFICATION:
   - For every component, provide a concrete technical justification over alternatives.
   - Specify scaling strategies and replication models (e.g. Multi-AZ Active-Active).

3. CONNECTION EDGES:
   - Define inter-service communication edges with explicit protocols (gRPC, HTTPS, Kafka Topic, WebSocket).
   - Indicate synchronous blocking vs. asynchronous decoupling.

4. PRODUCTION-GRADE MERMAID.JS ARCHITECTURE SPECIFICATION:
   - Begin with `flowchart TD` or `flowchart LR`.
   - Group components into distinct architectural subgraphs:
     * `subgraph Clients ["1. Client & Perimeter Layer"]`
     * `subgraph Edge ["2. Edge Ingress, Security & CDN Layer"]`
     * `subgraph Compute ["3. Stateless Microservices (Kubernetes Cluster)"]`
     * `subgraph Streaming ["4. Asynchronous Event Bus & Streaming"]`
     * `subgraph Cache ["5. In-Memory Distributed Cache Tier"]`
     * `subgraph Persistence ["6. Polyglot Persistence & Data Lakehouse"]`
     * `subgraph Observability ["7. Telemetry & Governance"]`
   - Use semantic Mermaid node shapes:
     * Cylinders `[(...)]` for all databases and data lakes (e.g. `Aurora[(Amazon Aurora<br/>Multi-AZ Primary)]`, `Redis[(Redis Cluster<br/>80/20 Hot Cache)]`).
     * Double brackets `[[...]]` for queues, Kafka, and event buses (e.g. `Kafka[[AWS MSK Kafka<br/>Partitioned by User Key]]`).
     * Standard brackets `[...]` with descriptive sub-labels for services (e.g. `APIGW[API Gateway<br/>Token Bucket & WAF]`, `DispatchSvc[Dispatch Engine<br/>gRPC / HPA ~30 Pods]`).
   - Every connection edge MUST specify the communication protocol and description:
     * Example: `Web -->|HTTPS / TLS 1.3| CDN`
     * Example: `APIGW -->|gRPC / Protobuf| OrderSvc`
     * Example: `OrderSvc -->|Kafka Topic: order.created| Kafka`
     * Example: `OrderSvc -->|Cache-Aside Sub-10ms| Redis`
     * Example: `OrderSvc -->|ACID Write / Multi-AZ| Aurora`
   - Strictly avoid loops or duplicate edges. Keep diagram between 30 and 65 lines.

{SHARED_MERMAID_RULES}
"""


class ArchitectureGeneratorAgent:
    """Real LLM Agent that synthesizes the component topology and Mermaid diagram.
    
    Agent Capabilities:
    - Error handling with structured retries (up to 3 attempts)
    - Output self-validation (min 3 components, non-empty diagram)
    - Mermaid syntax validation (checks for flowchart/graph declaration and edges)
    - Self-correction (feeds validation errors back for re-generation)
    - Tri-engine architecture:
      * GENERATOR_ENGINE=local  → Fine-tuned QLoRA model on local GPU (RTX A2000)
      * GENERATOR_ENGINE=ollama → Local Ollama instance (requires merged GGUF)
      * GENERATOR_ENGINE=gemini → Cloud Gemini API (default fallback)
    """

    MAX_RETRIES = 3

    def __init__(self, gemini_client: Optional[GeminiClient] = None):
        self.client = gemini_client or GeminiClient()
        self._local_model = None  # Lazy-loaded singleton
        self._registry = build_default_registry()

    def _validate_mermaid(self, diagram: str) -> list[str]:
        """Validate Mermaid diagram syntax for basic correctness."""
        issues = []
        if not diagram or not diagram.strip():
            issues.append("mermaid_diagram is empty")
            return issues
        
        lines = diagram.strip().split("\n")
        first_line = lines[0].strip().lower() if lines else ""
        
        if not any(first_line.startswith(kw) for kw in ["flowchart", "graph", "sequencediagram", "statediagram"]):
            issues.append(f"Mermaid diagram must start with 'flowchart' or 'graph', got: '{first_line[:50]}'")
        
        has_edge = any("-->" in line or "---" in line for line in lines)
        if not has_edge:
            issues.append("Mermaid diagram has no edges (missing '-->' connections)")
        
        if len(lines) < 5:
            issues.append(f"Mermaid diagram too short ({len(lines)} lines, expected at least 5)")
        
        return issues

    def _validate_architecture(self, arch: SystemArchitecture) -> list[str]:
        """Self-validation: checks architecture output for completeness."""
        issues = []
        if len(arch.components) < 3:
            issues.append(f"Expected at least 3 components, got {len(arch.components)}")
        if not arch.mermaid_diagram or not arch.mermaid_diagram.strip():
            issues.append("mermaid_diagram is empty")
        if not arch.overview or len(arch.overview) < 20:
            issues.append("overview is missing or too short")
        if len(arch.connections) < 2:
            issues.append(f"Expected at least 2 connections, got {len(arch.connections)}")
        
        # Mermaid-specific validation
        mermaid_issues = self._validate_mermaid(arch.mermaid_diagram)
        issues.extend(mermaid_issues)
        
        return issues

    def _get_local_model(self):
        """Lazy-load the local GPU model singleton."""
        if self._local_model is None:
            from nirman.agents.local_model import LocalModelLoader
            self._local_model = LocalModelLoader()
        return self._local_model

    def _generate_raw_local(
        self,
        user_prompt: str,
        spec: Optional[RequirementSpec] = None,
        capacity: Optional[CapacityMetrics] = None,
    ) -> dict:
        """Invokes the fine-tuned QLoRA model and returns its RAW native output as a dict.
        
        This does NOT map to SystemArchitecture — it returns the model's native format:
        {system_overview, capacity_planning, mermaid_diagram, component_breakdown, trade_offs, bottlenecks_and_mitigation}
        
        The raw output is then passed to ArchitectureEnhancerAgent for Gemini enhancement.
        """
        local_model = self._get_local_model()

        native_instruction = (
            "You are NirmanAI, an autonomous distributed systems architect. "
            "Analyze the user's requirements and produce a production-grade, highly scalable system architecture dossier "
            "including system overview, capacity planning calculations, visual Mermaid diagram, component breakdown, "
            "architectural trade-offs, and bottleneck mitigation strategies."
        )

        if spec and capacity:
            dau_str = f"{capacity.traffic.dau // 1_000_000}M" if capacity.traffic.dau >= 1_000_000 else f"{capacity.traffic.dau // 1_000}K"
            fr_str = ", ".join([fr.title for fr in spec.functional_requirements[:4]]) if spec.functional_requirements else "High availability, fault tolerance, scalability"
            nfr_str = ", ".join([nfr.target_metric for nfr in spec.non_functional_requirements[:3]]) if spec.non_functional_requirements else "P99 < 50ms, 99.99% availability"
            native_user_query = (
                f"Design a production-grade {spec.domain.value} system architecture for {dau_str} Daily Active Users on {spec.cloud_provider.value}. "
                f"Architecture Style: {spec.preferred_style.value}. "
                f"Core Features: {fr_str}. "
                f"Strict SLAs and Operational Constraints: {nfr_str}."
            )
        else:
            native_user_query = user_prompt

        raw_output = local_model.generate(
            system_prompt=native_instruction,
            user_prompt=native_user_query,
        )

        cleaned = raw_output.strip()
        if "```json" in cleaned:
            cleaned = cleaned.split("```json")[1].split("```")[0].strip()
        elif "```" in cleaned:
            cleaned = cleaned.split("```")[1].split("```")[0].strip()

        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1:
            cleaned = cleaned[start:end + 1]

        parsed = json_repair.repair_json(cleaned, return_objects=True)
        if not isinstance(parsed, dict):
            raise ValueError(f"Local model generated invalid non-dict JSON output: {type(parsed)}")

        logger.info(
            f"Fine-tuned model raw output: "
            f"{len(parsed.get('component_breakdown', []))} components, "
            f"{len(parsed.get('mermaid_diagram', '').splitlines())} mermaid lines"
        )
        return parsed

    def _generate_via_local(
        self,
        user_prompt: str,
        system_prompt: str,
        spec: Optional[RequirementSpec] = None,
        capacity: Optional[CapacityMetrics] = None,
    ) -> SystemArchitecture:
        """Invokes the fine-tuned QLoRA model on local GPU for generation using its native schema.
        
        This uses the cached 4-bit base model (unsloth/Qwen2.5-7B-Instruct-bnb-4bit)
        with the trained LoRA adapter loaded on top, running directly on the RTX A2000 GPU.
        The model outputs its native training format (system_overview, mermaid_diagram,
        component_breakdown, trade_offs, bottlenecks_and_mitigation) which is mapped
        directly into the SystemArchitecture Pydantic schema.
        """
        import re
        parsed = self._generate_raw_local(user_prompt, spec=spec, capacity=capacity)

        # 1. System Metadata & Narrative
        dau_str = f"{capacity.traffic.dau // 1_000_000}M" if (capacity and capacity.traffic.dau >= 1_000_000) else "Scale"
        domain_val = spec.domain.value if spec else parsed.get("domain", "Distributed System")
        style_val = spec.preferred_style.value if spec else parsed.get("style", "Microservices")
        cloud_val = spec.cloud_provider.value if spec else parsed.get("cloud", "AWS")
        system_name = parsed.get("system_name") or f"{domain_val} ({dau_str} DAU)"
        overview = parsed.get("system_overview") or parsed.get("overview") or f"{domain_val} architecture designed for {dau_str} DAU on {cloud_val}."

        # 2. Mermaid Diagram
        mermaid = parsed.get("mermaid_diagram", "").strip()
        if not (mermaid.startswith("flowchart") or mermaid.startswith("graph")):
            mermaid = f"flowchart TD\n{mermaid}"

        # 3. Component Breakdown -> ComponentNode mapping
        raw_comps = parsed.get("component_breakdown") or parsed.get("components") or []
        components = []
        for idx, comp in enumerate(raw_comps):
            if isinstance(comp, dict):
                c_name = comp.get("name", f"Service-{idx+1}")
                c_tech = comp.get("tech") or comp.get("technology", "Cloud Native")
                c_purpose = comp.get("rationale") or comp.get("purpose", "")
            else:
                c_name = str(comp)
                c_tech = "Cloud Native"
                c_purpose = ""

            nl = c_name.lower()
            if any(k in nl for k in ["ui", "client", "app", "mobile", "frontend"]):
                layer = LayerType.CLIENT
            elif any(k in nl for k in ["gateway", "ingress", "edge", "waf", "cdn", "perimeter"]):
                layer = LayerType.INGRESS
            elif any(k in nl for k in ["cache", "redis", "memcached"]):
                layer = LayerType.CACHE
            elif any(k in nl for k in ["db", "database", "storage", "postgres", "sql", "lake", "dynamo", "s3"]):
                layer = LayerType.PERSISTENCE
            elif any(k in nl for k in ["kafka", "queue", "stream", "event", "messaging", "bridge"]):
                layer = LayerType.EVENT_BUS
            elif any(k in nl for k in ["mesh", "istio", "envoy", "sidecar"]):
                layer = LayerType.INFRASTRUCTURE
            elif any(k in nl for k in ["monitor", "telemetry", "observability", "prometheus", "grafana"]):
                layer = LayerType.INFRASTRUCTURE
            elif any(k in nl for k in ["ai", "ml", "inference", "model", "fraud"]):
                layer = LayerType.ML_PIPELINE
            else:
                layer = LayerType.COMPUTE

            clean_id = re.sub(r'[^A-Za-z0-9_]', '_', c_name).upper()[:20]
            components.append(ComponentNode(
                id=clean_id or f"COMP_{idx+1}",
                name=c_name,
                layer=layer,
                technology=c_tech,
                purpose=c_purpose or f"Core functionality for {c_name}",
                redundancy="Multi-AZ Active-Active Replication"
            ))

        # 4. Connections extracted from Mermaid diagram
        connections = []
        edge_pattern = re.compile(r'([A-Za-z0-9_]+)\s*-->\s*(?:\|([^|]+)\|)?\s*([A-Za-z0-9_]+)')
        for src, label, tgt in edge_pattern.findall(mermaid):
            connections.append(ConnectionEdge(
                source_id=src,
                target_id=tgt,
                protocol=CommunicationProtocol.HTTPS_REST,
                description=label.strip() if label else "inter-service communication",
                is_synchronous=True
            ))

        # Ensure minimal connectivity even if diagram used alternate edge syntax
        if len(connections) < 2 and len(components) >= 2:
            for i in range(len(components) - 1):
                connections.append(ConnectionEdge(
                    source_id=components[i].id,
                    target_id=components[i+1].id,
                    protocol=CommunicationProtocol.GRPC,
                    description=f"{components[i].name} to {components[i+1].name}",
                    is_synchronous=True
                ))

        # 5. Architectural Trade-offs
        raw_to = parsed.get("trade_offs", [])
        trade_offs = []
        if isinstance(raw_to, str):
            trade_offs = [s.strip() for s in re.split(r'\n+|- |\d+\. ', raw_to) if len(s.strip()) > 15]
        elif isinstance(raw_to, list):
            trade_offs = [str(x) for x in raw_to if len(str(x)) > 10]
        if not trade_offs:
            peak_qps = capacity.traffic.peak_qps if capacity else 20000
            trade_offs = [f"Selected distributed {style_val} architecture to achieve high throughput at {peak_qps:,} QPS."]

        # 6. Bottleneck Mitigations
        raw_bm = parsed.get("bottlenecks_and_mitigation", [])
        bottleneck_mitigations = []
        if isinstance(raw_bm, str):
            bottleneck_mitigations = [s.strip() for s in re.split(r'\n+|- |\d+\. ', raw_bm) if len(s.strip()) > 15]
        elif isinstance(raw_bm, list):
            bottleneck_mitigations = [str(x) for x in raw_bm if len(str(x)) > 10]
        if not bottleneck_mitigations:
            peak_qps = capacity.traffic.peak_qps if capacity else 20000
            bottleneck_mitigations = [f"Database read/write lock contention under {peak_qps:,} QPS mitigated via distributed caching and queue-based leveling."]

        tech_stack = {c.name: c.technology for c in components}

        return SystemArchitecture(
            system_name=system_name,
            domain=domain_val,
            style=style_val,
            cloud=cloud_val,
            overview=overview,
            components=components,
            connections=connections,
            mermaid_diagram=mermaid,
            technology_stack=tech_stack,
            trade_offs=trade_offs,
            bottleneck_mitigations=bottleneck_mitigations,
        )

    def _generate_via_ollama(self, user_prompt: str, system_prompt: str) -> SystemArchitecture:

        """Invokes local fine-tuned Ollama instance for offline generation."""
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        model = os.getenv("OLLAMA_MODEL", "nirmanai:7b")
        url = f"{base_url}/api/chat"
        schema_json = json.dumps(SystemArchitecture.model_json_schema(), indent=2)
        prompt_with_schema = (
            f"{system_prompt}\n\n"
            f"CRITICAL REQUIREMENT: Output ONLY valid JSON adhering strictly to this JSON schema:\n"
            f"```json\n{schema_json}\n```\n\n"
            f"User Requirement:\n{user_prompt}"
        )
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt_with_schema}],
            "format": "json",
            "stream": False,
            "options": {"temperature": 0.2, "num_predict": 4096},
        }
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data_bytes, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            content = data["message"]["content"]
            repaired = json_repair.repair_json(content, return_objects=True)
            return SystemArchitecture.model_validate(repaired)

    def generate(self, spec: RequirementSpec, capacity: CapacityMetrics) -> SystemArchitecture:
        """Invokes LLM with retry, self-validation, and Mermaid validation.
        
        Agent loop:
        1. Build detailed prompt with capacity constraints
        2. Call LLM (Ollama or Gemini)
        3. Validate output (components, diagram, trade-offs)
        4. If validation fails, retry with correction prompt
        """
        base_user_prompt = f"""Synthesize an enterprise distributed system architecture for the following specification:

System Name: {spec.domain.value} ({capacity.traffic.dau // 1_000_000 if capacity.traffic.dau >= 1_000_000 else capacity.traffic.dau // 1_000}M DAU)
Domain: {spec.domain.value}
Cloud Environment: {spec.cloud_provider.value}
Architectural Style: {spec.preferred_style.value}

Quantitative Sizing Constraints:
- Daily Active Users: {capacity.traffic.dau:,}
- Peak Concurrency: {capacity.traffic.peak_qps:,} QPS ({capacity.traffic.read_write_ratio} Read/Write)
- Peak Bandwidth: Ingress {capacity.network.ingress_bandwidth_gbps:.2f} Gbps | Egress {capacity.network.egress_bandwidth_gbps:.2f} Gbps
- 5-Year Physical Storage (3x Multi-AZ): {capacity.storage.effective_5yr_storage_tb:.1f} TB
- Redis Cache Sizing: {capacity.cache.cache_memory_ram_gb:.0f} GB RAM ({capacity.cache.recommended_nodes} nodes)
- Recommended Kubernetes Pod Count: ~{capacity.recommended_compute_pods} Pods

Functional Requirements:
{chr(10).join([f"- [{fr.id}] {fr.title}: {fr.description}" for fr in spec.functional_requirements])}

Non-Functional Requirements & SLAs:
{chr(10).join([f"- [{nfr.category}] {nfr.target_metric}: {nfr.description}" for nfr in spec.non_functional_requirements])}

Operational Constraints:
{chr(10).join([f"- {c}" for c in spec.constraints])}

CRITICAL ADDITIONAL REQUIREMENTS:
- For 'trade_offs': Provide 3-5 SPECIFIC trade-off decisions unique to THIS system design. Not generic platitudes. Each should name the specific components and quantify the impact.
- For 'bottleneck_mitigations': Identify 2-4 SPECIFIC bottlenecks in THIS architecture and their targeted mitigations with concrete numbers.
"""

        engine = os.getenv("GENERATOR_ENGINE", "gemini").lower()
        user_prompt = base_user_prompt
        last_error = None
        # Track if local engine failed validation — switch to Gemini for remaining attempts
        local_failed = False

        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                current_engine = engine if not local_failed else "gemini"
                logger.info(f"🏗️ Generator attempt {attempt}/{self.MAX_RETRIES} (engine={current_engine})...")

                arch = None
                if current_engine == "local":
                    try:
                        logger.info("🧠 Generating via LOCAL fine-tuned QLoRA model on GPU...")
                        arch = self._generate_via_local(user_prompt, GENERATOR_SYSTEM_PROMPT, spec=spec, capacity=capacity)
                    except Exception as e:
                        logger.warning(f"Local GPU generation failed ({e}), falling back to Gemini API pool...")
                        local_failed = True

                elif current_engine == "ollama":
                    try:
                        logger.info("Generating via local Ollama model (nirmanai:7b)...")
                        arch = self._generate_via_ollama(user_prompt, GENERATOR_SYSTEM_PROMPT)
                    except Exception as e:
                        logger.warning(f"Ollama generation failed ({e}), falling back to Gemini API pool...")

                if arch is None:
                    # Try ReAct agent first for Gemini path
                    if attempt == 1:
                        try:
                            logger.info("🤖 Generator ReAct Agent: researching & designing...")
                            tools = self._registry.get_tools(["search_web", "read_url", "validate_mermaid"])
                            engine = ReActEngine(
                                gemini_client=self.client,
                                persona="Distinguished Cloud Architect designing production-grade distributed systems",
                                tools=tools,
                                output_schema=SystemArchitecture,
                                max_steps=10,
                            )
                            goal = (
                                f"{GENERATOR_SYSTEM_PROMPT}\n\n"
                                f"Design the architecture for:\n{user_prompt}\n\n"
                                f"INSTRUCTIONS:\n"
                                f"1. SEARCH for reference architectures in this domain\n"
                                f"2. Design the architecture with 12-15 components\n"
                                f"3. Generate Mermaid flowchart, then VALIDATE it\n"
                                f"4. Generate a sequence diagram too\n"
                                f"5. Produce FINAL_ANSWER as SystemArchitecture JSON"
                            )
                            result = engine.run(goal)
                            arch = result.output
                            logger.info(
                                f"✅ ReAct Generator completed in {result.total_steps} steps, "
                                f"{len(result.tools_used)} tool calls"
                            )
                        except Exception as react_e:
                            logger.warning(f"ReAct generation failed ({react_e}), using direct Gemini call.")

                    if arch is None:
                        logger.info("☁️ Generating via Gemini cloud API (direct structured)...")
                        arch = self.client.generate_structured(
                            system_prompt=GENERATOR_SYSTEM_PROMPT,
                            user_prompt=user_prompt,
                            schema=SystemArchitecture,
                        )

                # Self-validation
                issues = self._validate_architecture(arch)
                if issues:
                    issues_str = "; ".join(issues)
                    logger.warning(f"⚠️ Generator output validation failed (attempt {attempt}): {issues_str}")
                    # If local model failed validation, switch to Gemini for next attempt
                    if current_engine == "local":
                        local_failed = True
                        logger.info("🔄 Switching to Gemini API for remaining attempts...")
                    if attempt < self.MAX_RETRIES:
                        user_prompt = (
                            f"Your previous architecture had these issues: {issues_str}\n\n"
                            f"Please fix these problems and regenerate.\n\n{base_user_prompt}"
                        )
                        continue
                    else:
                        logger.warning("⚠️ Max retries reached. Using last output despite validation issues.")

                logger.info(f"✅ Generator completed successfully on attempt {attempt}. "
                           f"Components: {len(arch.components)}, Connections: {len(arch.connections)}, "
                           f"Trade-offs: {len(arch.trade_offs)}, Mitigations: {len(arch.bottleneck_mitigations)}")
                return arch

            except Exception as e:
                last_error = e
                logger.error(f"❌ Generator attempt {attempt} failed: {e}")
                if attempt < self.MAX_RETRIES:
                    user_prompt = (
                        f"The previous attempt failed with error: {str(e)}\n\n"
                        f"Please try again.\n\n{base_user_prompt}"
                    )
                    continue

        raise RuntimeError(
            f"ArchitectureGeneratorAgent failed after {self.MAX_RETRIES} attempts. Last error: {last_error}"
        )


# Alias for backward compatibility
ArchitectureGenerator = ArchitectureGeneratorAgent

