"""
NirmanAI - Prompt Enhancer Agent
================================
Transforms concise or underspecified natural language user ideas into
rich, production-grade distributed architecture specifications prior to synthesis.
"""

import re
from typing import Dict, Any, Optional
from nirman.schemas.analyzer import DomainType, CloudEnvironment


class PromptEnhancer:
    """Intelligent prompt expansion agent that elevates simple prompts into comprehensive architectural specs."""

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

    def enhance(self, raw_prompt: str) -> Dict[str, Any]:
        """Expands a raw prompt into a rich specification."""
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
