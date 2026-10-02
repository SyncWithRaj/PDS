"""
NirmanAI - Prompt Enhancer Agent (LLM-Powered)
===============================================
Transforms concise or underspecified natural language user ideas into
rich, production-grade distributed architecture specifications prior to synthesis.

Uses Gemini LLM as a "Principal Product Manager & Systems Analyst" to deeply
understand user intent, inject domain-specific features, SLAs, and compliance
requirements. Falls back to rule-based enhancement if Gemini is unavailable.
"""

import re
import logging
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from nirman.schemas.analyzer import DomainType, CloudEnvironment
from nirman.agents.gemini_client import GeminiClient

logger = logging.getLogger('nirman.enhancer')


ENHANCER_SYSTEM_PROMPT = """You are a Principal Product Manager & Distributed Systems Analyst with 15+ years of experience designing systems at FAANG-scale.

Your task is to take a concise or underspecified natural language prompt from a user and deeply understand the TRUE intent behind it, then produce a comprehensive architecture specification.

ANALYSIS STEPS:
1. DOMAIN RECOGNITION - Identify the ACTUAL domain (not surface-level keywords):
   - "Build me a Swiggy clone" = Hyper-local Food Delivery & Real-Time Logistics (NOT just e-commerce)
   - "Build Zoom alternative" = Real-Time Video Conferencing with WebRTC/SFU (NOT video streaming)
   - "Hospital management system" = Healthcare EHR with HL7/FHIR Interoperability (NOT generic web app)
   - "Build a platform like Codeforces" = Competitive Programming with Sandboxed Code Execution
   - "Supply chain platform" = IoT-Driven Supply Chain with Blockchain Provenance

2. SCALE INFERENCE - Extract or infer realistic scale:
   - If user says "100K DAU", use that exactly
   - If user says "like WhatsApp", infer 500M+ DAU
   - If no scale mentioned, infer from domain (fintech=5M, social=10M, enterprise=500K)

3. FEATURE INJECTION - Identify 5-8 features the user DIDN'T mention but the domain REQUIRES:
   - Food delivery: Geospatial rider allocation, surge pricing engine, real-time ETA prediction
   - Payments: Idempotent transaction processing, double-entry ledger, fraud ML pipeline
   - Healthcare: Patient data encryption, audit trail, HL7/FHIR APIs, role-based access
   - Chat: WebSocket connection pooling, message persistence, read receipts, typing indicators

4. SLA INJECTION - Provide 3-5 SPECIFIC, QUANTITATIVE SLAs:
   - Include exact latency targets (P50, P99)
   - Include availability targets (99.9%, 99.99%, 99.999%)
   - Include throughput targets based on scale

5. COMPLIANCE DETECTION - Identify regulatory requirements:
   - Payments/Banking → PCI-DSS Level 1, SOX
   - Healthcare → HIPAA, HITECH
   - EU users → GDPR, Data Residency
   - Children → COPPA
   - Government → FedRAMP, SOC2 Type II

6. COMPREHENSIVE PROMPT - Generate a rich, professional prompt that covers ALL the above.
   The enhanced prompt should be 3-5 sentences, technically precise, and include specific
   technology hints, SLA targets, and compliance requirements.
"""


class EnhancedPromptSpec(BaseModel):
    """Structured output from the LLM-based PromptEnhancer."""
    detected_domain: str = Field(..., description="The TRUE domain, e.g. 'Hyper-local Food Delivery & Real-Time Logistics'")
    detected_scale: str = Field(..., description="Inferred scale, e.g. '10M DAU' or '500K DAU'")
    cloud_provider: str = Field(default="AWS", description="Target cloud platform (AWS, GCP, Azure)")
    unstated_features: List[str] = Field(
        default_factory=list,
        description="5-8 features the user didn't mention but the domain REQUIRES (e.g., 'Geospatial rider tracking', 'Idempotent payment processing')"
    )
    implicit_slas: List[str] = Field(
        default_factory=list,
        description="3-5 realistic SLAs with specific numbers (e.g., 'P99 < 50ms for live tracking', '99.999% availability for payment gateway')"
    )
    compliance_requirements: List[str] = Field(
        default_factory=list,
        description="Regulatory requirements (e.g., 'PCI-DSS Level 1', 'HIPAA', 'GDPR')"
    )
    enhanced_prompt: str = Field(
        ...,
        description="The final comprehensive 3-5 sentence prompt covering domain, scale, features, SLAs, and compliance"
    )


class PromptEnhancerAgent:
    """LLM-powered prompt expansion agent that elevates simple prompts into comprehensive architectural specs.
    
    Uses Gemini as a 'Principal Product Manager' to deeply understand user intent,
    inject mandatory domain features, realistic SLAs, and compliance requirements.
    Falls back to rule-based keyword matching if Gemini is unavailable.
    """

    # Rule-based fallback domain templates
    DOMAIN_ENHANCEMENT_MAP = {
        DomainType.FINTECH: {
            "slas": "P99 < 10ms read latency, P99 < 50ms write latency, 99.999% availability, Zero-Trust mTLS, PCI-DSS compliance, strict ACID double-entry ledger guarantees, multi-region active-active disaster recovery.",
            "features": "Tokenized payment ingress, fraud detection pipeline, idempotent transaction processor, asynchronous settlement queues, polyglot persistence.",
        },
        DomainType.ECOMMERCE: {
            "slas": "P99 < 50ms product catalog reads, P99 < 120ms checkout, 99.99% availability, flash sale queue-based leveling, dynamic read-replicas, elastic auto-scaling.",
            "features": "Global edge caching, inventory reservation with distributed locking, shopping cart state management, payment gateway integration, order fulfillment event stream.",
        },
        DomainType.STREAMING: {
            "slas": "Sub-2s initial playback buffer, 99.99% availability, global CDN edge distribution, adaptive bitrate streaming (HLS/DASH), low-latency chunked ingestion.",
            "features": "Multi-tier CDN caching, metadata service with Redis cluster, video transcoding microservices, user watch-history state store, real-time recommendation feed.",
        },
        DomainType.SOCIAL: {
            "slas": "P99 < 30ms feed retrieval, sub-100ms message delivery, 99.99% availability, eventual consistency fanout-on-write model, WebSocket connection pooling.",
            "features": "Persistent bi-directional WebSocket gateway, timeline fanout workers, distributed graph store for relationships, media object storage, push notification queues.",
        },
        DomainType.IOT: {
            "slas": "Sub-100ms telemetry ingestion, 99.95% availability, backpressure handling for sensor spikes, time-series retention policies, edge gateway authentication.",
            "features": "MQTT / gRPC ingestion broker, Kafka telemetry streaming, hot time-series storage, geo-spatial query engine, fleet dispatch and alerting engine.",
        },
        DomainType.MLOPS: {
            "slas": "Sub-20ms model inference latency, high-throughput batch vector embedding, 99.9% uptime, GPU pod auto-scaling, dynamic batching.",
            "features": "Model inference gateway, vector database for semantic similarity, feature store cache, asynchronous training data ingestion pipeline, model drift monitoring.",
        },
        DomainType.GAMING: {
            "slas": "Sub-25ms tick rate latency, UDP / WebSocket low-jitter communication, zero packet loss for matchmaking, DDoS mitigation at edge.",
            "features": "Dedicated game session manager, matchmaking queue, leaderboard cache with Redis sorted sets, stateful game server autoscaling, anti-cheat audit log.",
        },
    }

    def __init__(self, gemini_client=None):
        self.client = gemini_client or GeminiClient()

    def enhance(self, raw_prompt: str) -> Dict[str, Any]:
        """Expands a raw prompt into a rich specification using Gemini LLM.
        
        Agent loop:
        1. Send user prompt to Gemini with Principal PM persona
        2. Gemini returns EnhancedPromptSpec with domain, features, SLAs, compliance
        3. Map to return dict for backward compatibility
        4. On any failure, fall back to rule-based enhancement
        """
        try:
            logger.info("LLM-based prompt enhancement via Gemini...")
            
            result: EnhancedPromptSpec = self.client.generate_structured(
                system_prompt=ENHANCER_SYSTEM_PROMPT,
                user_prompt=f"Analyze and enhance this user prompt for distributed system architecture design:\n\n\"{raw_prompt}\"",
                schema=EnhancedPromptSpec,
            )

            features_str = ", ".join(result.unstated_features) if result.unstated_features else ""
            slas_str = ", ".join(result.implicit_slas) if result.implicit_slas else ""
            compliance_str = ", ".join(result.compliance_requirements) if result.compliance_requirements else ""
            
            if compliance_str:
                slas_str += f". Compliance: {compliance_str}"

            logger.info(
                f"LLM enhancement complete: domain='{result.detected_domain}', "
                f"scale={result.detected_scale}, "
                f"{len(result.unstated_features)} features injected, "
                f"{len(result.implicit_slas)} SLAs, "
                f"{len(result.compliance_requirements)} compliance reqs"
            )

            return {
                "original_prompt": raw_prompt,
                "detected_domain": result.detected_domain,
                "detected_scale": result.detected_scale,
                "cloud_provider": result.cloud_provider,
                "key_features": features_str,
                "slas_and_constraints": slas_str,
                "enhanced_prompt": result.enhanced_prompt,
            }

        except Exception as e:
            logger.warning(f"Gemini enhancement failed ({e}), falling back to rule-based.")
            return self._rule_based_fallback(raw_prompt)

    def _rule_based_fallback(self, raw_prompt: str) -> Dict[str, Any]:
        """Rule-based fallback when Gemini is unavailable (rate-limited, etc.)."""
        prompt_lower = raw_prompt.lower()

        # 1. Detect Domain
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

        # 2. Extract or Default DAU
        dau_str = "10M"
        match = re.search(r'(\d+(?:\.\d+)?\s*(?:m|million|k|thousand|b|billion))\b', prompt_lower)
        if match:
            dau_str = match.group(1).upper()

        # 3. Detect Cloud
        cloud = "AWS"
        if "gcp" in prompt_lower or "google cloud" in prompt_lower:
            cloud = "GCP"
        elif "azure" in prompt_lower or "microsoft azure" in prompt_lower:
            cloud = "Azure"

        domain_info = self.DOMAIN_ENHANCEMENT_MAP.get(
            domain,
            {
                "slas": "P99 < 50ms read latency, P99 < 150ms write latency, 99.99% availability, multi-AZ redundancy.",
                "features": "API gateway with rate limiting, containerized microservices, distributed cache, relational database with read replicas, asynchronous event bus.",
            }
        )

        enhanced_prompt = (
            f"Design a high-scale, production-grade {domain.value} system architecture targeting {dau_str} Daily Active Users deployed on {cloud}. "
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
