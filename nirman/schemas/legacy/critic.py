"""
NirmanAI - Critic Schema
========================
Defines the 8-Pillar Quantitative Evaluation Rubric (0-100), single-point-of-failure
(SPOF) detection, vulnerability severity levels, and audit logs.
"""

from enum import Enum
from typing import List, Dict, Optional
from pydantic import BaseModel, Field


class EvaluationPillar(str, Enum):
    SCALABILITY = "Scalability & Throughput (15%)"
    LATENCY = "Latency & Performance SLAs (15%)"
    RELIABILITY = "Reliability & Fault Tolerance (15%)"
    CONSISTENCY = "Data Consistency & CAP Adherence (15%)"
    SECURITY = "Security, Compliance & Zero-Trust (10%)"
    COST = "Cost & Resource Efficiency (10%)"
    ML_RIGOR = "ML/Data Pipeline Rigor (10%)"
    ALIGNMENT = "Requirement & Constraint Alignment (10%)"


class VulnerabilitySeverity(str, Enum):
    CRITICAL = "CRITICAL (Immediate Failure / SPOF)"
    HIGH = "HIGH (SLA Violation under peak load)"
    MEDIUM = "MEDIUM (Suboptimal resource usage / minor latency spike)"
    LOW = "LOW (Cosmetic / Best practice recommendation)"


class DeficiencyFinding(BaseModel):
    id: str = Field(..., description="Unique issue identifier (e.g. DEF-01)")
    pillar: EvaluationPillar = Field(..., description="Which rubric pillar was violated")
    severity: VulnerabilitySeverity = Field(..., description="Risk severity rating")
    component_target: str = Field(..., description="Target node ID or section (e.g. 'DB_PRIMARY', 'PAYMENT_SVC')")
    flaw_description: str = Field(..., description="Exact architectural defect or vulnerability detected")
    failure_mode: str = Field(..., description="Real-world disaster scenario if left unaddressed")
    prescribed_patch: str = Field(..., description="Prescriptive remediation guidance for the Refiner Agent")


class PillarScore(BaseModel):
    pillar: EvaluationPillar = Field(..., description="Rubric pillar evaluated")
    weight: float = Field(..., description="Pillar weight percentage (e.g. 0.15)")
    raw_score: float = Field(..., description="Score awarded out of 100")
    weighted_score: float = Field(..., description="Calculated weighted contribution")
    passed: bool = Field(..., description="True if raw_score >= 80")
    audit_notes: str = Field(..., description="Specific engineering justifications for this score")


class CriticScorecard(BaseModel):
    overall_score: float = Field(..., description="Composite weighted score across all 8 pillars (0 - 100)")
    passing_threshold: float = Field(default=85.0, description="Minimum acceptable quality threshold")
    is_accepted: bool = Field(..., description="True if overall_score >= passing_threshold")
    spof_detected: bool = Field(default=False, description="True if any critical SPOF exists")
    spof_count: int = Field(default=0, description="Count of Single Points of Failure found")
    pillar_breakdown: List[PillarScore] = Field(default_factory=list, description="Scores per each of the 8 pillars")
    deficiency_log: List[DeficiencyFinding] = Field(default_factory=list, description="Detailed actionable vulnerabilities")
    executive_verdict: str = Field(..., description="High-level critic evaluation and verdict summary")
