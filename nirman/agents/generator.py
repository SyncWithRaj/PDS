"""
NirmanAI - Architecture Generator Agent (Gemini LLM)
====================================================
Real LLM reasoning agent acting as Principal Cloud Solutions Architect:
- Takes RequirementSpec and CapacityMetrics
- Synthesizes end-to-end multi-tier component topologies
- Selects cloud native datastores, queues, and compute tiers with technical rationale
- Authors clean, structured, non-looping Mermaid.js diagrams
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
   - Add modern dark-theme subgraph styles at the end of the diagram:
     * `style Clients fill:#0f172a,stroke:#38bdf8,stroke-width:1px,color:#f8fafc`
     * `style Edge fill:#1e293b,stroke:#0284c7,stroke-width:2px,color:#f8fafc`
     * `style Compute fill:#0c4a6e,stroke:#0369a1,stroke-width:2px,color:#f8fafc`
     * `style Streaming fill:#3b0764,stroke:#9333ea,stroke-width:2px,color:#f8fafc`
     * `style Cache fill:#701a75,stroke:#c026d3,stroke-width:2px,color:#f8fafc`
     * `style Persistence fill:#14532d,stroke:#16a34a,stroke-width:2px,color:#f8fafc`
   - Strictly avoid loops or duplicate edges. Keep diagram between 30 and 65 lines.
"""


class ArchitectureGeneratorAgent:
    """Real LLM Agent that synthesizes the component topology and Mermaid diagram."""

    def __init__(self, gemini_client: Optional[GeminiClient] = None):
        self.client = gemini_client or GeminiClient()

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
        """Invokes Fine-Tuned Ollama or Gemini LLM to synthesize the SystemArchitecture."""
        user_prompt = f"""Synthesize an enterprise distributed system architecture for the following specification:

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
"""

        engine = os.getenv("GENERATOR_ENGINE", "gemini").lower()
        if engine == "ollama":
            try:
                logger.info("Generating architecture via local fine-tuned Ollama model (nirmanai:7b)...")
                return self._generate_via_ollama(user_prompt, GENERATOR_SYSTEM_PROMPT)
            except Exception as e:
                logger.warning(f"Ollama generation failed ({e}), automatically falling back to Gemini API pool...")

        # Cloud Gemini Generation (with resilient 5-key pool fallback)
        arch: SystemArchitecture = self.client.generate_structured(
            system_prompt=GENERATOR_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            schema=SystemArchitecture,
        )

        return arch


# Alias for backward compatibility
ArchitectureGenerator = ArchitectureGeneratorAgent
