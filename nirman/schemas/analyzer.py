"""
NirmanAI - Analyzer Schema
==========================
Defines data structures for requirement extraction, domain classification,
SLAs, and system constraints.
"""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class DomainType(str, Enum):
    WEB = "Web & Mobile Application"
    STREAMING = "Real-Time Streaming & Media"
    FINTECH = "FinTech & Payment Settlement"
    ECOMMERCE = "E-Commerce & High-Concurrency Retail"
    SOCIAL = "Social Media & Distributed Graph"
    MLOPS = "AI/ML Inference & Data Science Platform"
    BIGDATA = "Big Data Lakehouse & Analytics"
    IOT = "IoT & Edge Sensor Ingestion"
    GAMING = "Real-Time Multiplayer Gaming"
    DEFENSE = "Mission-Critical Defense & Telemetry"


class TargetScale(str, Enum):
    STARTUP = "Startup (10k - 100k DAU)"
    MIDSCALE = "Mid-Scale (100k - 1M DAU)"
    ENTERPRISE = "Enterprise (1M - 25M DAU)"
    HYPERSCALE = "Hyper-Scale (25M - 100M+ DAU)"


class CloudEnvironment(str, Enum):
    AWS = "AWS"
    GCP = "GCP"
    AZURE = "Azure"
    MULTI_CLOUD = "Multi-Cloud"
    HYBRID_CLOUD = "Hybrid Cloud"
    ON_PREMISES = "On-Premises"


class ArchitecturalStyle(str, Enum):
    MICROSERVICES = "Microservices"
    EVENT_DRIVEN = "Event-Driven"
    CQRS = "CQRS"
    SERVERLESS = "Serverless"
    MODULAR_MONOLITH = "Modular Monolith"
    DATA_MESH = "Data Mesh"
    ZERO_TRUST = "Zero-Trust Architecture"
    HEXAGONAL = "Hexagonal Architecture"


class FunctionalRequirement(BaseModel):
    id: str = Field(..., description="Unique FR identifier (e.g. FR-01)")
    title: str = Field(..., description="Short title of the requirement")
    description: str = Field(..., description="Detailed feature requirement description")
    priority: str = Field(default="High", description="High / Medium / Low priority")


class NonFunctionalRequirement(BaseModel):
    category: str = Field(..., description="Latency, Availability, Consistency, Security, etc.")
    target_metric: str = Field(..., description="e.g. p99 < 50ms, 99.99% uptime, RPO < 1m")
    description: str = Field(..., description="Justification and context for the requirement")


class RequirementSpec(BaseModel):
    raw_prompt: str = Field(..., description="Original user natural language input")
    domain: DomainType = Field(default=DomainType.WEB, description="Classified system domain")
    target_scale: TargetScale = Field(default=TargetScale.ENTERPRISE, description="Target operational scale")
    cloud_provider: CloudEnvironment = Field(default=CloudEnvironment.AWS, description="Target deployment environment")
    preferred_style: ArchitecturalStyle = Field(default=ArchitecturalStyle.MICROSERVICES, description="Architectural paradigm")
    target_dau: int = Field(default=10_000_000, description="Estimated Daily Active Users")
    peak_factor: float = Field(default=3.0, description="Peak to average traffic ratio multiplier")
    functional_requirements: List[FunctionalRequirement] = Field(default_factory=list, description="Extracted core features")
    non_functional_requirements: List[NonFunctionalRequirement] = Field(default_factory=list, description="Extracted SLAs & NFRs")
    constraints: List[str] = Field(default_factory=list, description="Strict operational constraints (e.g. Zero Trust, Active-Active)")
