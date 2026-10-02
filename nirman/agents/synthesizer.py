"""
NirmanAI - Synthesizer Agent
============================
Compiles the accepted SystemArchitecture and Critic evaluation into a
comprehensive production-grade System Architecture Dossier, Markdown report,
and interactive HTML dashboard with live Mermaid.js.
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional

from nirman.schemas.analyzer import RequirementSpec
from nirman.schemas.estimator import CapacityMetrics
from nirman.schemas.generator import SystemArchitecture
from nirman.schemas.critic import CriticScorecard
from nirman.schemas.refiner import RefinementIteration
from nirman.schemas.dossier import (
    ArchitectureDossier,
    ComponentDetailItem,
    TradeOffItem,
    BottleneckMitigationItem,
)


class SynthesizerAgent:
    """Deliverable Compiler Agent assembling final production deliverables.
    
    Dynamically extracts trade-offs and bottleneck mitigations from the actual
    LLM-generated SystemArchitecture rather than using hardcoded boilerplate.
    """

    def synthesize(
        self,
        spec: RequirementSpec,
        capacity: CapacityMetrics,
        arch: SystemArchitecture,
        scorecard: CriticScorecard,
        refinements: Optional[List[RefinementIteration]] = None,
    ) -> ArchitectureDossier:
        """Assembles the final validated ArchitectureDossier with DYNAMIC content."""
        refinements = refinements or []

        components_detail = [
            ComponentDetailItem(
                name=c.name,
                tech=c.technology,
                rationale=c.purpose,
            )
            for c in arch.components
        ]

        # DYNAMIC trade-offs from LLM-generated architecture (NOT hardcoded)
        trade_offs = []
        if arch.trade_offs:
            # Use actual LLM-generated trade-offs specific to this architecture
            for i, to_text in enumerate(arch.trade_offs):
                trade_offs.append(
                    TradeOffItem(
                        decision=f"Architecture Decision #{i+1}",
                        option_chosen=to_text.split(".")[0] if "." in to_text else to_text[:80],
                        option_discarded="Alternative approach",
                        trade_off_rationale=to_text,
                    )
                )
        else:
            # Fallback: generate semi-dynamic defaults using actual architecture data
            trade_offs = [
                TradeOffItem(
                    decision=f"Persistence Strategy for {arch.system_name}",
                    option_chosen=f"{arch.technology_stack.get('Primary Database', 'OLTP Store')} + In-Memory Cache",
                    option_discarded="Single Monolithic Database",
                    trade_off_rationale=(
                        f"Separating transactional persistence from an in-memory cache holding the 80/20 hot set "
                        f"({capacity.cache.cache_memory_ram_gb:.0f} GB RAM) achieves sub-10ms read latency at {capacity.traffic.read_peak_qps:,} read QPS."
                    ),
                ),
            ]

        # DYNAMIC bottleneck mitigations from LLM-generated architecture (NOT hardcoded)
        mitigations = []
        if arch.bottleneck_mitigations:
            # Use actual LLM-generated mitigations specific to this architecture
            for bm_text in arch.bottleneck_mitigations:
                # Split "Bottleneck: ... Mitigation: ..." if present
                if "mitigation" in bm_text.lower():
                    parts = bm_text.split("Mitigation:", 1) if "Mitigation:" in bm_text else bm_text.split("mitigation:", 1)
                    bottleneck_desc = parts[0].replace("Bottleneck:", "").strip().rstrip(".")
                    mitigation_desc = parts[1].strip() if len(parts) > 1 else bm_text
                else:
                    bottleneck_desc = bm_text[:80]
                    mitigation_desc = bm_text

                mitigations.append(
                    BottleneckMitigationItem(
                        bottleneck_description=bottleneck_desc,
                        mitigation_strategy=mitigation_desc,
                    )
                )
        else:
            # Fallback: generate semi-dynamic defaults using actual architecture data
            mitigations = [
                BottleneckMitigationItem(
                    bottleneck_description=f"Traffic Surges Exceeding Peak Concurrency ({capacity.traffic.peak_qps:,} QPS)",
                    mitigation_strategy=(
                        f"Horizontal Pod Autoscaling (HPA) targeting ~{capacity.recommended_compute_pods} pods, "
                        f"backed by edge rate limiting at the API Gateway."
                    ),
                ),
            ]

        # Also incorporate deficiency log from critic if available
        if scorecard.deficiency_log:
            for deficiency in scorecard.deficiency_log[:3]:  # Top 3 deficiencies
                mitigations.append(
                    BottleneckMitigationItem(
                        bottleneck_description=f"[{deficiency.id}] {deficiency.flaw_description}",
                        mitigation_strategy=deficiency.prescribed_patch,
                    )
                )

        title = f"{spec.domain.value} System Architecture ({capacity.traffic.dau // 1_000_000 if capacity.traffic.dau >= 1_000_000 else capacity.traffic.dau // 1_000}M DAU)"

        return ArchitectureDossier(
            title=title,
            domain=spec.domain.value,
            style=spec.preferred_style.value,
            cloud=spec.cloud_provider.value,
            system_overview=arch.overview,
            capacity_planning=capacity,
            mermaid_diagram=arch.mermaid_diagram,
            sequence_diagram=arch.sequence_diagram if arch.sequence_diagram else "",
            component_breakdown=components_detail,
            trade_offs=trade_offs,
            bottlenecks_and_mitigation=mitigations,
            final_scorecard=scorecard,
            refinement_history=refinements,
        )

    def to_markdown(self, dossier: ArchitectureDossier) -> str:
        """Renders the master ArchitectureDossier into a production Markdown document."""
        cap = dossier.capacity_planning
        sc = dossier.final_scorecard

        md = []
        md.append(f"# 🏛️ {dossier.title}")
        md.append(f"**Domain:** {dossier.domain} | **Style:** {dossier.style} | **Cloud Platform:** {dossier.cloud}\n")

        md.append("## 1. Executive Summary & System Overview")
        md.append(dossier.system_overview + "\n")

        md.append("## 2. Capacity Planning & Quantitative Sizing")
        md.append("| Metric Category | Parameter | Sized Value |")
        md.append("| :--- | :--- | :--- |")
        md.append(f"| **Traffic** | Daily Active Users (DAU) | **{cap.traffic.dau:,}** |")
        md.append(f"| **Traffic** | Read / Write Ratio | **{cap.traffic.read_write_ratio}** |")
        md.append(f"| **Traffic** | Average Throughput | **{cap.traffic.avg_qps:,} QPS** |")
        md.append(f"| **Traffic** | Peak Concurrency | **{cap.traffic.peak_qps:,} QPS** |")
        md.append(f"| **Network** | Peak Ingress Bandwidth | **{cap.network.ingress_bandwidth_gbps:.3f} Gbps** |")
        md.append(f"| **Network** | Peak Egress Bandwidth | **{cap.network.egress_bandwidth_gbps:.3f} Gbps** |")
        md.append(f"| **Storage** | Daily Raw Growth | **{cap.storage.daily_storage_gb:.2f} GB/day** |")
        md.append(f"| **Storage** | 5-Year Net Data Footprint | **{cap.storage.five_year_storage_tb:.2f} TB** |")
        md.append(f"| **Storage** | 5-Year Physical (3x Multi-AZ) | **{cap.storage.effective_5yr_storage_tb:.2f} TB** |")
        md.append(f"| **Cache** | Redis 80/20 Hot Set RAM | **{cap.cache.cache_memory_ram_gb:.1f} GB** ({cap.cache.recommended_nodes} nodes) |")
        md.append(f"| **Compute** | Recommended Kubernetes Cluster | **~{cap.recommended_compute_pods} Pods** |\n")

        md.append("## 3. Visual System Architecture Diagram")
        md.append("```mermaid")
        md.append(dossier.mermaid_diagram.strip())
        md.append("```\n")

        if dossier.sequence_diagram and dossier.sequence_diagram.strip():
            md.append("## 3.1 Critical Path Sequence Diagram")
            md.append("```mermaid")
            md.append(dossier.sequence_diagram.strip())
            md.append("```\n")

        md.append("## 4. Component Topology Breakdown")
        md.append("| Component Tier | Selected Technology | Purpose & Rationale |")
        md.append("| :--- | :--- | :--- |")
        for c in dossier.component_breakdown:
            md.append(f"| **{c.name}** | `{c.tech}` | {c.rationale} |")
        md.append("")

        md.append("## 5. Architectural Trade-Off Analysis")
        for t in dossier.trade_offs:
            md.append(f"### • Decision: {t.decision}")
            md.append(f"- **Option Chosen:** `{t.option_chosen}`")
            md.append(f"- **Option Discarded:** `{t.option_discarded}`")
            md.append(f"- **Engineering Rationale:** {t.trade_off_rationale}\n")

        md.append("## 6. Bottleneck Identification & Mitigation Strategies")
        for b in dossier.bottlenecks_and_mitigation:
            md.append(f"- **Bottleneck:** {b.bottleneck_description}")
            md.append(f"  ↳ **Mitigation:** {b.mitigation_strategy}\n")

        md.append("## 7. Critic Scorecard Audit (8-Pillar Evaluation)")
        md.append(f"**Overall Score:** **{sc.overall_score} / 100** | **Verdict:** {sc.executive_verdict}\n")
        md.append("| Evaluation Pillar | Weight | Score | Status |")
        md.append("| :--- | :--- | :--- | :--- |")
        for p in sc.pillar_breakdown:
            status = "✅ PASS" if p.passed else "⚠️ REVIEW"
            md.append(f"| {p.pillar.value} | {int(p.weight*100)}% | **{p.raw_score}** | {status} |")
        md.append("")

        if dossier.refinement_history:
            md.append("## 8. Refinement Changelog")
            for ref in dossier.refinement_history:
                md.append(f"- **Iteration {ref.iteration_number}:** Starting Score: {ref.starting_score} -> Applied {len(ref.patches_applied)} patch(es):")
                for patch in ref.patches_applied:
                    md.append(f"  - `{patch.action_type.value}`: {patch.modification_summary}")

        return "\n".join(md)

    def to_html(self, dossier: ArchitectureDossier) -> str:
        """Renders the master ArchitectureDossier into an interactive HTML dashboard with live Mermaid.js."""
        cap = dossier.capacity_planning
        sc = dossier.final_scorecard

        score_color = "#10b981" if sc.overall_score >= 80 else ("#f59e0b" if sc.overall_score >= 65 else "#ef4444")

        components_rows = "".join(
            f"<tr><td><strong>{c.name}</strong></td><td><code>{c.tech}</code></td><td>{c.rationale}</td></tr>"
            for c in dossier.component_breakdown
        )

        pillars_rows = "".join(
            f"<tr><td>{p.pillar.value}</td><td>{int(p.weight*100)}%</td>"
            f"<td><strong>{p.raw_score}</strong></td>"
            f"<td><span class='badge {'badge-pass' if p.passed else 'badge-review'}'>{'PASS' if p.passed else 'REVIEW'}</span></td>"
            f"<td><div class='progress-bar'><div class='progress-fill' style='width: {p.raw_score}%;'></div></div></td></tr>"
            for p in sc.pillar_breakdown
        )

        tradeoffs_html = "".join(
            f"<div class='card trade-card'><h4>{t.decision}</h4>"
            f"<p><strong>Chosen:</strong> <code class='tech-tag'>{t.option_chosen}</code> &nbsp;|&nbsp; "
            f"<strong>Discarded:</strong> <code>{t.option_discarded}</code></p>"
            f"<p class='rationale-text'>{t.trade_off_rationale}</p></div>"
            for t in dossier.trade_offs
        )

        mitigations_html = "".join(
            f"<div class='card mit-card'><h4>⚠️ {b.bottleneck_description}</h4>"
            f"<p class='rationale-text'><strong>Mitigation Strategy:</strong> {b.mitigation_strategy}</p></div>"
            for b in dossier.bottlenecks_and_mitigation
        )

        refinements_html = ""
        if dossier.refinement_history:
            ref_items = []
            for ref in dossier.refinement_history:
                patches_str = "".join(
                    f"<li><code>{patch.action_type.value}</code>: {patch.modification_summary}</li>"
                    for patch in ref.patches_applied
                )
                ref_items.append(
                    f"<div class='card ref-card'><h4>Iteration {ref.iteration_number} (Score: {ref.starting_score} → {sc.overall_score})</h4>"
                    f"<ul>{patches_str}</ul></div>"
                )
            refinements_html = f"<section><h2>Refinement History & Self-Correction</h2>{''.join(ref_items)}</section>"

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{dossier.title} - NirmanAI Architecture Dossier</title>
    <script type="module">
        import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
        mermaid.initialize({{ startOnLoad: true, theme: 'dark' }});
    </script>
    <style>
        :root {{
            --bg-color: #0b1120;
            --card-bg: #151f38;
            --border-color: #263558;
            --text-main: #f1f5f9;
            --text-muted: #94a3b8;
            --accent-blue: #38bdf8;
            --accent-emerald: #10b981;
            --font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background-color: var(--bg-color);
            color: var(--text-main);
            font-family: var(--font-family);
            line-height: 1.6;
            padding: 2rem;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        header {{
            background: linear-gradient(135deg, #1e293b, #0f172a);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 2rem;
            margin-bottom: 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 1.5rem;
        }}
        .header-title h1 {{ font-size: 1.85rem; color: #fff; margin-bottom: 0.5rem; }}
        .tags {{ display: flex; gap: 0.6rem; flex-wrap: wrap; }}
        .tag {{
            background: #1e3a8a;
            color: #93c5fd;
            font-size: 0.85rem;
            font-weight: 600;
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            border: 1px solid #3b82f6;
        }}
        .score-box {{
            text-align: center;
            background: #0f172a;
            border: 2px solid {score_color};
            border-radius: 12px;
            padding: 1rem 1.75rem;
        }}
        .score-val {{ font-size: 2.5rem; font-weight: 800; color: {score_color}; }}
        .score-label {{ font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-muted); }}
        section {{ margin-bottom: 2.5rem; }}
        h2 {{ font-size: 1.4rem; color: var(--accent-blue); margin-bottom: 1rem; border-bottom: 1px solid var(--border-color); padding-bottom: 0.5rem; }}
        .overview-box {{
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 1.25rem 1.5rem;
            font-size: 1.05rem;
            color: #cbd5e1;
        }}
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 1rem;
            margin-bottom: 1.5rem;
        }}
        .kpi-card {{
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 1rem;
            text-align: center;
        }}
        .kpi-title {{ font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; margin-bottom: 0.35rem; }}
        .kpi-value {{ font-size: 1.35rem; font-weight: 700; color: #fff; }}
        .diagram-card {{
            background: #0d1527;
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 1.5rem;
            overflow-x: auto;
            text-align: center;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background: var(--card-bg);
            border-radius: 10px;
            overflow: hidden;
            margin-top: 0.75rem;
        }}
        th, td {{
            padding: 0.85rem 1rem;
            border-bottom: 1px solid var(--border-color);
            text-align: left;
            font-size: 0.92rem;
        }}
        th {{ background: #0f172a; color: var(--text-muted); font-weight: 600; text-transform: uppercase; font-size: 0.75rem; }}
        code {{ background: #1e293b; color: #38bdf8; padding: 0.2rem 0.45rem; border-radius: 4px; font-size: 0.88rem; }}
        .badge {{ padding: 0.2rem 0.6rem; border-radius: 4px; font-size: 0.75rem; font-weight: 700; }}
        .badge-pass {{ background: #064e3b; color: #34d399; border: 1px solid #059669; }}
        .badge-review {{ background: #78350f; color: #fbbf24; border: 1px solid #d97706; }}
        .progress-bar {{ background: #1e293b; border-radius: 9999px; height: 8px; width: 100px; overflow: hidden; }}
        .progress-fill {{ background: var(--accent-emerald); height: 100%; }}
        .card {{
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 1.25rem;
            margin-bottom: 1rem;
        }}
        .card h4 {{ color: #e2e8f0; margin-bottom: 0.5rem; }}
        .rationale-text {{ color: #94a3b8; font-size: 0.92rem; }}
        ul {{ margin-left: 1.5rem; color: #cbd5e1; }}
        footer {{ text-align: center; color: var(--text-muted); font-size: 0.85rem; padding: 2rem 0; border-top: 1px solid var(--border-color); margin-top: 3rem; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="header-title">
                <h1>🏛️ {dossier.title}</h1>
                <div class="tags">
                    <span class="tag">{dossier.domain}</span>
                    <span class="tag">{dossier.style}</span>
                    <span class="tag">{dossier.cloud}</span>
                </div>
            </div>
            <div class="score-box">
                <div class="score-val">{sc.overall_score}</div>
                <div class="score-label">Critic Score (8 Pillars)</div>
            </div>
        </header>

        <section>
            <h2>1. System Overview</h2>
            <div class="overview-box">{dossier.system_overview}</div>
        </section>

        <section>
            <h2>2. Quantitative Capacity Sizing</h2>
            <div class="kpi-grid">
                <div class="kpi-card">
                    <div class="kpi-title">Daily Active Users</div>
                    <div class="kpi-value">{cap.traffic.dau:,}</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-title">Peak Concurrency</div>
                    <div class="kpi-value">{cap.traffic.peak_qps:,} QPS</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-title">Peak Bandwidth</div>
                    <div class="kpi-value">{cap.network.egress_bandwidth_gbps:.2f} Gbps</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-title">5-Year Physical Storage</div>
                    <div class="kpi-value">{cap.storage.effective_5yr_storage_tb:.1f} TB</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-title">Redis 80/20 RAM</div>
                    <div class="kpi-value">{cap.cache.cache_memory_ram_gb:.0f} GB</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-title">Compute Cluster</div>
                    <div class="kpi-value">~{cap.recommended_compute_pods} Pods</div>
                </div>
            </div>
        </section>

        <section>
            <h2>3. System Architecture (Mermaid.js)</h2>
            <div class="diagram-card">
                <pre class="mermaid">
{dossier.mermaid_diagram.strip()}
                </pre>
            </div>
        </section>

        {f'''
        <section>
            <h2>3.1 Critical Path Sequence Diagram</h2>
            <div class="diagram-card">
                <pre class="mermaid">
{dossier.sequence_diagram.strip()}
                </pre>
            </div>
        </section>
        ''' if dossier.sequence_diagram and dossier.sequence_diagram.strip() else ''}

        <section>
            <h2>4. Component Topology Breakdown</h2>
            <table>
                <thead>
                    <tr>
                        <th>Component Tier</th>
                        <th>Selected Technology</th>
                        <th>Architectural Rationale</th>
                    </tr>
                </thead>
                <tbody>
                    {components_rows}
                </tbody>
            </table>
        </section>

        <section>
            <h2>5. Architectural Trade-Off Analysis</h2>
            {tradeoffs_html}
        </section>

        <section>
            <h2>6. Bottleneck Identification & Mitigation Strategies</h2>
            {mitigations_html}
        </section>

        <section>
            <h2>7. Critic Scorecard Audit (8 Pillars)</h2>
            <table>
                <thead>
                    <tr>
                        <th>Pillar Name</th>
                        <th>Weight</th>
                        <th>Score</th>
                        <th>Verdict</th>
                        <th>Progress</th>
                    </tr>
                </thead>
                <tbody>
                    {pillars_rows}
                </tbody>
            </table>
        </section>

        {refinements_html}

        <footer>
            Generated autonomously by <strong>NirmanAI</strong> • LangGraph Multi-Agent Architecture Engine
        </footer>
    </div>
</body>
</html>
"""
        return html_content

    def save(self, dossier: ArchitectureDossier, output_dir: str = "output") -> Dict[str, str]:
        """Saves both Markdown and interactive HTML dossiers to disk."""
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        clean_title = re.sub(r'[^a-zA-Z0-9_\-\s]', '', dossier.title).strip()
        filename_base = re.sub(r'\s+', '_', clean_title).lower()

        md_file = out_path / f"{filename_base}.md"
        html_file = out_path / f"{filename_base}.html"

        md_content = self.to_markdown(dossier)
        html_content = self.to_html(dossier)

        with open(md_file, "w", encoding="utf-8") as f:
            f.write(md_content)

        with open(html_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        return {
            "markdown": str(md_file.resolve()),
            "html": str(html_file.resolve()),
        }
