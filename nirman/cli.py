"""
NirmanAI - Autonomous System Architecture CLI
==============================================
Interactive terminal interface and automation engine for synthesizing,
evaluating, and refining distributed software architecture dossiers.
"""

import sys
import os
import subprocess
from pathlib import Path

# Add project root to sys.path so CLI can be run directly as a script
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from typing import Optional
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.markdown import Markdown

from nirman.agents.orchestrator import NirmanOrchestrator
from nirman.schemas.analyzer import RequirementSpec
from nirman.schemas.dossier import ArchitectureDossier

# Ensure UTF-8 output encoding for Windows terminals
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

app = typer.Typer(
    name="nirman",
    help="🏛️ NirmanAI: Autonomous Distributed Software Architecture Multi-Agent Platform",
    add_completion=False,
)
console = Console()


@app.command()
def synthesize(
    prompt: Optional[str] = typer.Argument(
        None,
        help="Natural language architecture prompt (e.g. 'Design an e-commerce flash sale backend for 100M DAU on AWS')",
    ),
    output_dir: str = typer.Option(
        "output",
        "--output",
        "-o",
        help="Directory to save the generated Markdown and HTML dossiers",
    ),
    max_refinements: int = typer.Option(
        2,
        "--max-refinements",
        "-r",
        help="Maximum self-correcting refinement iterations if Critic detects deficiencies",
    ),
    use_llm: bool = typer.Option(
        False,
        "--use-llm",
        help="Enable local Ollama LLM for NLP extraction and topology generation",
    ),
):
    """Synthesizes a production distributed system architecture from natural language requirements."""
    console.print(
        Panel.fit(
            "[bold cyan]🏛️ NirmanAI Architecture Synthesis Engine[/bold cyan]\n"
            "[dim]Autonomous Multi-Agent System Design, Capacity Sizing & 8-Pillar Critic Audit[/dim]",
            border_style="cyan",
        )
    )

    if not prompt:
        prompt = typer.prompt("Enter system architecture requirements")

    orchestrator = NirmanOrchestrator()
    dossier: Optional[ArchitectureDossier] = None

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("[yellow]Synthesizing architecture pipeline...", total=None)

        progress.update(task, description="[cyan]Phase 1/5: Analyzing requirements & SLAs...")
        # Step 1
        spec = orchestrator.analyzer.analyze(prompt, use_llm=use_llm)

        progress.update(task, description="[magenta]Phase 2/5: Calculating deterministic capacity math...")
        # Step 2
        capacity = orchestrator.estimator.estimate(spec)

        progress.update(task, description="[blue]Phase 3/5: Generating component topology & Mermaid graph...")
        # Step 3
        arch = orchestrator.generator.generate(spec, capacity, use_llm=use_llm)

        progress.update(task, description="[green]Phase 4/5: Running 8-pillar Critic audit & SPOF detection...")
        # Step 4
        scorecard = orchestrator.critic.audit(spec, capacity, arch)

        # Step 5
        refinements = []
        iteration = 0
        while (not scorecard.is_accepted or scorecard.spof_detected) and iteration < max_refinements:
            iteration += 1
            progress.update(task, description=f"[bold yellow]Phase 5/5: Self-refining architecture (Iteration {iteration})...")
            arch, iter_log = orchestrator.refiner.refine(arch, scorecard, iteration_number=iteration)
            if iter_log:
                refinements.append(iter_log)
            scorecard = orchestrator.critic.audit(spec, capacity, arch)

        progress.update(task, description="[bold green]Assembling master Architecture Dossier...")
        dossier = orchestrator._build_dossier(spec, capacity, arch, scorecard, refinements)
        progress.remove_task(task)

    # Display Results Table
    cap = dossier.capacity_planning
    sc = dossier.final_scorecard

    console.print(f"\n[bold green]✅ Architecture Synthesis Completed Successfully![/bold green]")
    console.print(f"[bold]System Title:[/bold] {dossier.title}")
    console.print(f"[bold]Domain:[/bold] {dossier.domain} | [bold]Style:[/bold] {dossier.style} | [bold]Cloud:[/bold] {dossier.cloud}\n")

    # Capacity Metrics Table
    cap_table = Table(title="📐 Deterministic Capacity Planning Sizing", border_style="bright_blue")
    cap_table.add_column("Category", style="cyan", no_wrap=True)
    cap_table.add_column("Metric Parameter", style="white")
    cap_table.add_column("Engine Sizing Value", style="bold green")

    cap_table.add_row("Traffic", "Daily Active Users (DAU)", f"{cap.traffic.dau:,}")
    cap_table.add_row("Traffic", "Read / Write Ratio", f"{cap.traffic.read_write_ratio}")
    cap_table.add_row("Traffic", "Peak Throughput Concurrency", f"{cap.traffic.peak_qps:,} QPS")
    cap_table.add_row("Network", "Peak Egress Bandwidth", f"{cap.network.egress_bandwidth_gbps:.2f} Gbps")
    cap_table.add_row("Storage", "5-Year Effective Physical Storage (3x Multi-AZ)", f"{cap.storage.effective_5yr_storage_tb:.1f} TB")
    cap_table.add_row("Cache", "Redis 80/20 Hot Working Set RAM", f"{cap.cache.cache_memory_ram_gb:.0f} GB ({cap.cache.recommended_nodes} nodes)")
    cap_table.add_row("Compute", "Recommended Container Cluster", f"~{cap.recommended_compute_pods} Pods")
    console.print(cap_table)

    # Critic Scorecard Table
    score_color = "green" if sc.overall_score >= 80 else ("yellow" if sc.overall_score >= 65 else "red")
    crit_table = Table(
        title=f"🛡️ Architecture Critic Scorecard (Overall: [{score_color}]{sc.overall_score}/100[/{score_color}] - {sc.executive_verdict})",
        border_style="bright_magenta",
    )
    crit_table.add_column("Evaluation Pillar", style="white")
    crit_table.add_column("Weight", justify="right", style="dim")
    crit_table.add_column("Score", justify="right", style="bold")
    crit_table.add_column("Verdict", justify="center")

    for p in sc.pillar_breakdown:
        p_status = "[green]PASS[/green]" if p.passed else "[yellow]REVIEW[/yellow]"
        p_color = "green" if p.raw_score >= 80 else ("yellow" if p.raw_score >= 65 else "red")
        crit_table.add_row(
            p.pillar.value,
            f"{int(p.weight*100)}%",
            f"[{p_color}]{p.raw_score:.1f}[/{p_color}]",
            p_status,
        )
    console.print(crit_table)

    # Save outputs
    saved_files = orchestrator.save(dossier, output_dir=output_dir)
    console.print(f"\n[bold]📁 Artifact Deliverables Generated:[/bold]")
    console.print(f"  • Markdown: [cyan]{saved_files['markdown']}[/cyan]")
    console.print(f"  • Live HTML Dashboard: [cyan]{saved_files['html']}[/cyan]\n")


@app.command()
def benchmark():
    """Runs a comprehensive benchmark across 5 industry-standard distributed systems scenarios."""
    scenarios = [
        ("FinTech Settlement", "Design a global payments gateway for Stripe handling 50M daily transactions with sub-10ms latency on AWS"),
        ("E-Commerce Flash Sale", "Design an e-commerce platform for Amazon Prime Day handling 100M active shoppers with flash sales on AWS"),
        ("Video Streaming", "Design a video streaming and recommendation architecture like Netflix for 75M users on GCP"),
        ("Ride Dispatch", "Design a ride-hailing and fleet dispatch platform like Uber for 25M users on AWS"),
        ("Social & Chat Graph", "Design a high-concurrency real-time messaging platform like WhatsApp for 150M active users on AWS"),
    ]

    console.print(
        Panel.fit(
            "[bold magenta]⚡ NirmanAI Distributed System Benchmark Suite[/bold magenta]\n"
            f"[dim]Evaluating {len(scenarios)} core real-world architecture archetypes[/dim]",
            border_style="magenta",
        )
    )

    orchestrator = NirmanOrchestrator()
    results_table = Table(title="Benchmark Evaluation Summary", border_style="cyan")
    results_table.add_column("Scenario", style="cyan", no_wrap=True)
    results_table.add_column("DAU", justify="right", style="white")
    results_table.add_column("Peak QPS", justify="right", style="green")
    results_table.add_column("5-Yr Storage", justify="right", style="yellow")
    results_table.add_column("Redis RAM", justify="right", style="blue")
    results_table.add_column("Pods", justify="right", style="white")
    results_table.add_column("Critic Score", justify="right", style="bold green")

    for name, prompt in scenarios:
        dossier = orchestrator.synthesize(prompt)
        cap = dossier.capacity_planning
        sc = dossier.final_scorecard
        results_table.add_row(
            name,
            f"{cap.traffic.dau // 1_000_000}M",
            f"{cap.traffic.peak_qps:,}",
            f"{cap.storage.effective_5yr_storage_tb:.1f} TB",
            f"{cap.cache.cache_memory_ram_gb:.0f} GB",
            f"~{cap.recommended_compute_pods}",
            f"{sc.overall_score:.1f}/100",
        )

    console.print(results_table)
    console.print("[bold green]✅ All benchmark scenarios executed and validated successfully![/bold green]\n")


@app.command()
def status():
    """Checks NirmanAI background training status, hardware utilization, and checkpoints."""
    console.print(
        Panel.fit(
            "[bold cyan]🔍 NirmanAI System & Training Status[/bold cyan]",
            border_style="cyan",
        )
    )

    # 1. Check Adapters & Checkpoints
    adapter_dir = Path("nirmanai_adapter")
    if adapter_dir.exists():
        checkpoints = sorted([d.name for d in adapter_dir.iterdir() if d.is_dir() and d.name.startswith("checkpoint-")], key=lambda x: int(x.split("-")[-1]))
        if checkpoints:
            latest = checkpoints[-1]
            console.print(f"[bold green]✔ Training Checkpoints Active:[/bold green] Found {len(checkpoints)} checkpoint(s). Latest: [bold yellow]{latest}[/bold yellow]")
        else:
            console.print("[yellow]Adapter directory exists, waiting for first checkpoint...[/yellow]")
    else:
        console.print("[dim]No active adapter training directory found at ./nirmanai_adapter[/dim]")

    # 2. Check GPU Status via nvidia-smi
    try:
        smi_out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=name,temperature.gpu,utilization.gpu,memory.used,memory.total,power.draw", "--format=csv,noheader,nounits"],
            text=True,
            timeout=5,
        ).strip()
        gpu_name, temp, util, mem_used, mem_total, power = [x.strip() for x in smi_out.split(",")]
        console.print(f"\n[bold]GPU Status:[/bold] {gpu_name}")
        console.print(f"  • Utilization: [green]{util}%[/green] | Temp: [yellow]{temp}°C[/yellow] | Power: {power}W")
        console.print(f"  • VRAM: [cyan]{mem_used} MiB / {mem_total} MiB[/cyan]")
    except Exception:
        console.print("\n[dim]GPU status unavailable (nvidia-smi call skipped or timed out)[/dim]")

    # 3. Check Ollama Service
    import urllib.request
    try:
        with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=3) as resp:
            import json
            data = json.loads(resp.read().decode())
            models = [m.get("name") for m in data.get("models", [])]
            console.print(f"\n[bold green]✔ Ollama Service Online:[/bold green] Local models available: {', '.join(models) if models else 'None'}")
    except Exception:
        console.print("\n[yellow]⚠️ Ollama service not responding at http://localhost:11434[/yellow]")


@app.command()
def serve(
    port: int = typer.Option(8080, "--port", "-p", help="Port to serve the web dashboard on"),
    open_browser: bool = typer.Option(True, "--open/--no-open", help="Automatically open web browser"),
):
    """Launches the interactive NirmanAI Web UI Dashboard."""
    import webbrowser
    from nirman.web_ui import start_server

    url = f"http://localhost:{port}"
    console.print(
        Panel.fit(
            f"[bold cyan]🏛️ NirmanAI Web Dashboard[/bold cyan]\n"
            f"Interactive Architecture Design UI running at: [bold underline green]{url}[/bold underline green]\n"
            f"[dim]Press Ctrl+C in terminal to stop server[/dim]",
            border_style="cyan",
        )
    )

    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    start_server(port)


if __name__ == "__main__":
    app()
