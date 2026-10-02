"""
NirmanAI - Comprehensive End-to-End Pipeline & Multi-Agent Test Suite
====================================================================
Validates all 5 specialized agents, Pydantic schemas, deterministic math,
Mermaid diagram generation, Critic 8-pillar audit, and Dossier generation.
"""

import os
import sys
import unittest
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from nirman.schemas.pipeline.analyzer import (
    RequirementSpec,
    DomainType,
    TargetScale,
    CloudEnvironment,
    ArchitecturalStyle,
)
from nirman.schemas.pipeline.estimator import CapacityMetrics
from nirman.schemas.pipeline.generator import SystemArchitecture
from nirman.schemas.legacy.critic import CriticScorecard, EvaluationPillar
from nirman.schemas.pipeline.dossier import ArchitectureDossier

from nirman.agents.pipeline.analyzer import RequirementAnalyzer
from nirman.agents.pipeline.estimator import CapacityEstimator
from nirman.agents.pipeline.generator import ArchitectureGenerator
from nirman.agents.legacy.critic import ArchitectureCritic
from nirman.agents.legacy.refiner import ArchitectureRefiner
from nirman.agents.core.orchestrator import NirmanOrchestrator


class TestRequirementAnalyzer(unittest.TestCase):
    def setUp(self):
        self.analyzer = RequirementAnalyzer()

    def test_domain_and_scale_extraction(self):
        spec = self.analyzer.analyze("Design a global payment gateway for Stripe handling 50M daily transactions on AWS")
        self.assertIsInstance(spec, RequirementSpec)
        self.assertEqual(spec.domain, DomainType.FINTECH)
        self.assertEqual(spec.target_dau, 50_000_000)
        self.assertEqual(spec.cloud_provider, CloudEnvironment.AWS)

    def test_ecommerce_gcp_extraction(self):
        spec = self.analyzer.analyze("Design an e-commerce prime shopping catalog for 10M users on GCP")
        self.assertEqual(spec.domain, DomainType.ECOMMERCE)
        self.assertEqual(spec.target_dau, 10_000_000)
        self.assertEqual(spec.cloud_provider, CloudEnvironment.GCP)

    def test_streaming_azure_extraction(self):
        spec = self.analyzer.analyze("Design a video streaming CDN like Netflix for 100M active viewers on Azure")
        self.assertEqual(spec.domain, DomainType.STREAMING)
        self.assertEqual(spec.target_dau, 100_000_000)
        self.assertEqual(spec.cloud_provider, CloudEnvironment.AZURE)


class TestCapacityEstimator(unittest.TestCase):
    def setUp(self):
        self.estimator = CapacityEstimator()
        self.analyzer = RequirementAnalyzer()

    def test_deterministic_math(self):
        spec = self.analyzer.analyze("Fintech app with 10M DAU")
        cap = self.estimator.estimate(spec)

        self.assertIsInstance(cap, CapacityMetrics)
        self.assertEqual(cap.traffic.dau, 10_000_000)
        # Avg QPS should be 10,000,000 / 86400 * 30 = 3472
        self.assertEqual(cap.traffic.avg_qps, 3472)
        # Peak QPS should be 3472 * 3.0 (peak factor) = 10416
        self.assertEqual(cap.traffic.peak_qps, 10416)
        # Bandwidth should be non-zero positive float
        self.assertGreater(cap.network.egress_bandwidth_gbps, 0.0)
        self.assertGreater(cap.network.ingress_bandwidth_gbps, 0.0)
        # 5-year storage
        self.assertGreater(cap.storage.five_year_storage_tb, 0.0)
        self.assertGreater(cap.storage.effective_5yr_storage_tb, cap.storage.five_year_storage_tb)
        # Cache RAM
        self.assertGreater(cap.cache.cache_memory_ram_gb, 0.0)
        self.assertGreater(cap.cache.recommended_nodes, 0)
        # Pods
        self.assertGreater(cap.recommended_compute_pods, 0)


class TestArchitectureGenerator(unittest.TestCase):
    def setUp(self):
        self.analyzer = RequirementAnalyzer()
        self.estimator = CapacityEstimator()
        self.generator = ArchitectureGenerator()

    def test_architecture_topology_and_mermaid(self):
        spec = self.analyzer.analyze("Design a payment gateway on AWS for 20M DAU")
        capacity = self.estimator.estimate(spec)
        arch = self.generator.generate(spec, capacity)

        self.assertIsInstance(arch, SystemArchitecture)
        self.assertGreater(len(arch.components), 4)
        self.assertGreater(len(arch.connections), 4)

        # Mermaid sanity checks
        mermaid = arch.mermaid_diagram.strip()
        self.assertTrue(any(mermaid.startswith(prefix) for prefix in ["graph TD", "flowchart TD", "flowchart LR", "graph LR"]))
        lines = mermaid.splitlines()
        # Verify diagram does not suffer from infinite loop truncation (must be compact & clean)
        self.assertLessEqual(len(lines), 75)
        self.assertGreaterEqual(len(lines), 20)


class TestArchitectureCritic(unittest.TestCase):
    def setUp(self):
        self.analyzer = RequirementAnalyzer()
        self.estimator = CapacityEstimator()
        self.generator = ArchitectureGenerator()
        self.critic = ArchitectureCritic()

    def test_8_pillar_audit(self):
        spec = self.analyzer.analyze("High scale chat app for 50M DAU on AWS")
        cap = self.estimator.estimate(spec)
        arch = self.generator.generate(spec, cap)

        scorecard = self.critic.audit(spec, cap, arch)
        self.assertIsInstance(scorecard, CriticScorecard)
        self.assertEqual(len(scorecard.pillar_breakdown), 8)

        # Assert total weights sum to 1.0 (allowing for small floating point tolerance)
        total_weight = sum(p.weight for p in scorecard.pillar_breakdown)
        self.assertAlmostEqual(total_weight, 1.0, places=3)

        # Assert scores are between 0 and 100
        self.assertGreaterEqual(scorecard.overall_score, 0.0)
        self.assertLessEqual(scorecard.overall_score, 100.0)
        for p in scorecard.pillar_breakdown:
            self.assertGreaterEqual(p.raw_score, 0.0)
            self.assertLessEqual(p.raw_score, 100.0)


class TestArchitectureRefiner(unittest.TestCase):
    def setUp(self):
        self.analyzer = RequirementAnalyzer()
        self.estimator = CapacityEstimator()
        self.generator = ArchitectureGenerator()
        self.critic = ArchitectureCritic()
        self.refiner = ArchitectureRefiner()

    def test_refinement_cycle(self):
        spec = self.analyzer.analyze("Design an inventory system for 5M DAU on AWS")
        cap = self.estimator.estimate(spec)
        arch = self.generator.generate(spec, cap)
        scorecard = self.critic.audit(spec, cap, arch)

        refined_arch, iter_log = self.refiner.refine(arch, scorecard, iteration_number=1)
        self.assertIsInstance(refined_arch, SystemArchitecture)


class TestNirmanOrchestrator(unittest.TestCase):
    def setUp(self):
        self.orchestrator = NirmanOrchestrator()

    def test_end_to_end_synthesis_and_deliverables(self):
        prompt = "Design a multi-region e-commerce marketplace for 25M daily shoppers on AWS"
        dossier = self.orchestrator.synthesize(prompt)

        self.assertIsInstance(dossier, ArchitectureDossier)
        self.assertEqual(dossier.domain, DomainType.ECOMMERCE.value)
        self.assertEqual(dossier.capacity_planning.traffic.dau, 25_000_000)

        # Test Markdown generation
        md_text = self.orchestrator.to_markdown(dossier)
        self.assertIn("# 🏛️", md_text)
        self.assertIn("Deterministic Capacity Planning Calculations", md_text)
        self.assertIn("```mermaid", md_text)
        self.assertIn("Critic Scorecard Audit", md_text)

        # Test HTML generation
        html_text = self.orchestrator.to_html(dossier)
        self.assertIn("<!DOCTYPE html>", html_text)
        self.assertIn("mermaid.initialize", html_text)
        self.assertIn(f"{dossier.final_scorecard.overall_score}", html_text)

        # Test Disk Save
        saved = self.orchestrator.save(dossier, output_dir="output_test")
        self.assertTrue(Path(saved["markdown"]).exists())
        self.assertTrue(Path(saved["html"]).exists())

        # Cleanup test directory
        try:
            Path(saved["markdown"]).unlink(missing_ok=True)
            Path(saved["html"]).unlink(missing_ok=True)
            Path("output_test").rmdir()
        except Exception:
            pass


if __name__ == "__main__":
    unittest.main()
