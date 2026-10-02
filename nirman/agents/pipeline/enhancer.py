"""
NirmanAI - Prompt Enhancer Agent (ReAct Agentic)
==================================================
TRUE AUTONOMOUS AGENT — NOT a wrapper.

This agent uses the ReAct (Reason + Act) loop to:
1. THINK about what the user's prompt really means
2. SEARCH the web for real-world architecture patterns in that domain
3. READ relevant documentation and blog posts
4. REFLECT on what features, SLAs, and compliance requirements are needed
5. PRODUCE a comprehensive enhanced prompt backed by research

The agent DECIDES its own next action. We don't hardcode the flow.
"""

import re
import logging
from typing import Dict, Any, List
from pydantic import BaseModel, Field

from nirman.agents.core.gemini_client import GeminiClient
from nirman.agents.core.react_engine import ReActEngine
from nirman.tools.registry import build_default_registry
from nirman.schemas.pipeline.analyzer import DomainType

logger = logging.getLogger("nirman.enhancer")


class EnhancedPromptSpec(BaseModel):
    """Structured output from the ReAct PromptEnhancer agent."""
    detected_domain: str = Field(
        ...,
        description="The TRUE domain — not surface-level keywords. E.g., 'Hyper-local Food Delivery & Real-Time Logistics' for 'Swiggy clone', 'Real-Time Video Conferencing with WebRTC/SFU' for 'Zoom alternative'"
    )
    detected_scale: str = Field(
        ...,
        description="Inferred scale. E.g., '10M DAU', '500K DAU', '100K concurrent connections'"
    )
    cloud_provider: str = Field(
        default="AWS",
        description="Target cloud platform (AWS, GCP, Azure)"
    )
    unstated_features: List[str] = Field(
        default_factory=list,
        description="5-8 features the user didn't mention but the domain REQUIRES. These must be researched, not guessed."
    )
    implicit_slas: List[str] = Field(
        default_factory=list,
        description="3-5 realistic SLAs with specific numbers, validated against industry benchmarks"
    )
    compliance_requirements: List[str] = Field(
        default_factory=list,
        description="Regulatory requirements (PCI-DSS, HIPAA, GDPR, SOC2, COPPA, etc.)"
    )
    enhanced_prompt: str = Field(
        ...,
        description="The final comprehensive 3-5 sentence prompt covering domain, scale, features, SLAs, and compliance"
    )


# === Persona for the ReAct Agent ===
ENHANCER_PERSONA = (
    "Principal Product Manager & Distributed Systems Analyst with 15+ years at FAANG. "
    "You deeply understand system architecture across every domain — fintech, healthcare, "
    "gaming, legal tech, logistics, social media, IoT, and more. You identify what users "
    "ACTUALLY need (not just what they say), research real-world patterns, and produce "
    "comprehensive architecture specifications that a Staff Engineer would respect."
)


class PromptEnhancerAgent:
    """ReAct-powered prompt enhancement agent.

    This agent autonomously:
    1. Researches the user's domain via web search
    2. Reads relevant architecture docs and blog posts
    3. Identifies mandatory features the user didn't mention
    4. Injects realistic SLAs backed by industry benchmarks
    5. Detects compliance requirements for the domain
    6. Produces a comprehensive enhanced prompt

    Falls back to rule-based enhancement if the ReAct loop fails.
    """

    # Rule-based fallback templates (used when Gemini/tools fail)
    DOMAIN_ENHANCEMENT_MAP = {
        DomainType.FINTECH: {
            "slas": "P99 < 10ms read latency, P99 < 50ms write latency, 99.999% availability, PCI-DSS compliance, strict ACID double-entry ledger guarantees.",
            "features": "Tokenized payment ingress, fraud detection pipeline, idempotent transaction processor, asynchronous settlement queues, polyglot persistence.",
        },
        DomainType.ECOMMERCE: {
            "slas": "P99 < 50ms product catalog reads, P99 < 120ms checkout, 99.99% availability, flash sale queue-based leveling.",
            "features": "Global edge caching, inventory reservation with distributed locking, shopping cart state management, payment gateway integration, order fulfillment event stream.",
        },
        DomainType.STREAMING: {
            "slas": "Sub-2s initial playback buffer, 99.99% availability, global CDN edge distribution, adaptive bitrate streaming (HLS/DASH).",
            "features": "Multi-tier CDN caching, metadata service with Redis cluster, video transcoding microservices, user watch-history state store, real-time recommendation feed.",
        },
        DomainType.SOCIAL: {
            "slas": "P99 < 30ms feed retrieval, sub-100ms message delivery, 99.99% availability, WebSocket connection pooling.",
            "features": "Persistent bi-directional WebSocket gateway, timeline fanout workers, distributed graph store for relationships, media object storage, push notification queues.",
        },
        DomainType.IOT: {
            "slas": "Sub-100ms telemetry ingestion, 99.95% availability, backpressure handling for sensor spikes, time-series retention policies.",
            "features": "MQTT / gRPC ingestion broker, Kafka telemetry streaming, hot time-series storage, geo-spatial query engine, fleet dispatch and alerting engine.",
        },
        DomainType.MLOPS: {
            "slas": "Sub-20ms model inference latency, high-throughput batch vector embedding, 99.9% uptime, GPU pod auto-scaling.",
            "features": "Model inference gateway, vector database for semantic similarity, feature store cache, asynchronous training data ingestion pipeline, model drift monitoring.",
        },
        DomainType.GAMING: {
            "slas": "Sub-25ms tick rate latency, UDP / WebSocket low-jitter communication, zero packet loss for matchmaking, DDoS mitigation at edge.",
            "features": "Dedicated game session manager, matchmaking queue, leaderboard cache with Redis sorted sets, stateful game server autoscaling, anti-cheat audit log.",
        },
    }

    def __init__(self, gemini_client=None):
        self.client = gemini_client or GeminiClient()
        self._registry = build_default_registry()

    def enhance(self, raw_prompt: str) -> Dict[str, Any]:
        """Enhance a raw user prompt using the ReAct autonomous loop.

        The agent will:
        1. Search the web for domain-specific architecture patterns
        2. Read relevant docs to understand the domain deeply
        3. Identify unstated features, SLAs, and compliance needs
        4. Produce a comprehensive enhanced prompt

        Falls back to rule-based enhancement on failure.
        """
        try:
            logger.info(f"🤖 PromptEnhancer ReAct Agent starting for: '{raw_prompt[:80]}...'")

            # Build the ReAct engine with search + read tools
            tools = self._registry.get_tools(["search_web", "read_url"])
            engine = ReActEngine(
                gemini_client=self.client,
                persona=ENHANCER_PERSONA,
                tools=tools,
                output_schema=EnhancedPromptSpec,
                max_steps=8,
            )

            # Define the goal
            goal = (
                f"Deeply analyze and enhance this user prompt for distributed system "
                f"architecture design. Research the domain, identify mandatory features, "
                f"realistic SLAs, and compliance requirements.\n\n"
                f"USER PROMPT: \"{raw_prompt}\"\n\n"
                f"INSTRUCTIONS:\n"
                f"1. First, SEARCH the web to understand what this domain really needs\n"
                f"2. If you find a relevant architecture blog or doc, READ it\n"
                f"3. Identify 5-8 features the user didn't mention but the domain REQUIRES\n"
                f"4. Determine realistic SLAs with specific latency and availability numbers\n"
                f"5. Identify any compliance/regulatory requirements\n"
                f"6. Produce your FINAL_ANSWER as an EnhancedPromptSpec"
            )

            # Run the autonomous agent
            result = engine.run(goal)
            spec: EnhancedPromptSpec = result.output

            logger.info(
                f"✅ ReAct PromptEnhancer completed in {result.total_steps} steps, "
                f"{len(result.tools_used)} tool calls | "
                f"domain='{spec.detected_domain}', scale={spec.detected_scale}, "
                f"{len(spec.unstated_features)} features, {len(spec.implicit_slas)} SLAs, "
                f"{len(spec.compliance_requirements)} compliance reqs"
            )

            # Map to return dict for backward compatibility
            features_str = ", ".join(spec.unstated_features) if spec.unstated_features else ""
            slas_str = ", ".join(spec.implicit_slas) if spec.implicit_slas else ""
            compliance_str = ", ".join(spec.compliance_requirements) if spec.compliance_requirements else ""
            if compliance_str:
                slas_str += f". Compliance: {compliance_str}"

            return {
                "original_prompt": raw_prompt,
                "detected_domain": spec.detected_domain,
                "detected_scale": spec.detected_scale,
                "cloud_provider": spec.cloud_provider,
                "key_features": features_str,
                "slas_and_constraints": slas_str,
                "enhanced_prompt": spec.enhanced_prompt,
            }

        except Exception as e:
            logger.warning(f"ReAct PromptEnhancer failed ({e}), falling back to rule-based.")
            return self._rule_based_fallback(raw_prompt)

    def _rule_based_fallback(self, raw_prompt: str) -> Dict[str, Any]:
        """Rule-based fallback when the ReAct loop fails (rate limits, network errors)."""
        prompt_lower = raw_prompt.lower()

        domain = DomainType.WEB
        if any(w in prompt_lower for w in ["pay", "bank", "settle", "wallet", "fintech", "stripe", "crypto", "trading"]):
            domain = DomainType.FINTECH
        elif any(w in prompt_lower for w in ["shop", "cart", "commerce", "store", "prime day", "sale", "retail", "amazon"]):
            domain = DomainType.ECOMMERCE
        elif any(w in prompt_lower for w in ["video", "stream", "media", "netflix", "youtube", "music", "audio", "spotify"]):
            domain = DomainType.STREAMING
        elif any(w in prompt_lower for w in ["chat", "social", "friend", "graph", "tweet", "message", "whatsapp", "feed"]):
            domain = DomainType.SOCIAL
        elif any(w in prompt_lower for w in ["iot", "sensor", "telemetry", "fleet", "vehicle", "device", "gps", "uber", "ride"]):
            domain = DomainType.IOT
        elif any(w in prompt_lower for w in ["ai", "ml", "inference", "rag", "llm", "embedding", "model"]):
            domain = DomainType.MLOPS
        elif any(w in prompt_lower for w in ["game", "multiplayer", "matchmaking", "lobby", "leaderboard"]):
            domain = DomainType.GAMING

        dau_str = "10M"
        match = re.search(r'(\d+(?:\.\d+)?\s*(?:m|million|k|thousand|b|billion))\b', prompt_lower)
        if match:
            dau_str = match.group(1).upper()

        cloud = "AWS"
        if "gcp" in prompt_lower or "google cloud" in prompt_lower:
            cloud = "GCP"
        elif "azure" in prompt_lower or "microsoft azure" in prompt_lower:
            cloud = "Azure"

        domain_info = self.DOMAIN_ENHANCEMENT_MAP.get(domain, {
            "slas": "P99 < 50ms read latency, 99.99% availability, multi-AZ redundancy.",
            "features": "API gateway with rate limiting, containerized microservices, distributed cache, relational database with read replicas, asynchronous event bus.",
        })

        enhanced_prompt = (
            f"Design a high-scale, production-grade {domain.value} system architecture targeting {dau_str} DAU on {cloud}. "
            f"The architecture must incorporate {domain_info['features']} "
            f"Strict non-functional SLAs include: {domain_info['slas']} "
            f"Ensure zero single points of failure, multi-AZ active-active failover, and end-to-end observability."
        )

        return {
            "original_prompt": raw_prompt,
            "detected_domain": domain.value,
            "detected_scale": dau_str,
            "cloud_provider": cloud,
            "key_features": domain_info["features"],
            "slas_and_constraints": domain_info["slas"],
            "enhanced_prompt": enhanced_prompt,
        }


# Alias for backward compatibility
PromptEnhancer = PromptEnhancerAgent
