"""
NirmanAI - Web UI Prototype (LangGraph & Gemini)
================================================
Simple, clean HTML/CSS prototype for testing the LangGraph multi-agent architecture pipeline.
Features:
- Gemini API Key configuration
- Natural language prompt submission
- LangGraph execution across all 5 agents (Analyzer -> Generator -> Critic -> Refiner -> Synthesizer)
- Live Mermaid.js diagram rendering
- Quantitative capacity sizing table
- 8-pillar Critic scorecard display
- 1-click Markdown & HTML report downloads
"""

import os
import sys
import json
import urllib.parse
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from dotenv import load_dotenv

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from nirman.workflow import NirmanWorkflow
from nirman.agents.gemini_client import GeminiClient

load_dotenv()

PROTOTYPE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NirmanAI - LangGraph Architecture Prototype</title>
    <!-- Simple Tailwind CSS CDN for Prototype -->
    <script src="https://cdn.tailwindcss.com"></script>
    <!-- Mermaid.js CDN for dynamic visual diagram rendering -->
    <script type="module">
        import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
        mermaid.initialize({ startOnLoad: false, theme: 'dark' });
        window.mermaid = mermaid;
    </script>
    <style>
        body { background-color: #0f172a; color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
        .panel { background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; }
        .mermaid svg { max-width: 100% !important; height: auto !important; }
    </style>
</head>
<body class="p-6 max-w-7xl mx-auto space-y-6">

    <!-- Header -->
    <header class="panel p-5 flex flex-wrap justify-between items-center gap-4">
        <div>
            <h1 class="text-2xl font-bold text-sky-400">🏛️ NirmanAI Prototype</h1>
            <p class="text-xs text-slate-400 mt-0.5">LangGraph Multi-Agent Architecture Engine (Google Gemini Free Tier)</p>
        </div>
        <!-- .env Configuration Status Indicator -->
        <div class="flex items-center gap-2 text-xs">
            <span id="keyStatusBadge" class="px-3 py-1.5 rounded-full font-medium bg-slate-900 border border-slate-700 text-slate-300 flex items-center gap-2">
                <span id="keyDot" class="w-2 h-2 rounded-full bg-slate-500"></span>
                <span id="keyText">Checking .env...</span>
            </span>
        </div>
    </header>

    <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">

        <!-- Left Input Column (5 cols) -->
        <div class="lg:col-span-5 space-y-5">
            <div class="panel p-5 space-y-4">
                <label class="block text-sm font-semibold text-sky-400 uppercase tracking-wider">System Architecture Goal</label>
                <textarea id="promptInput" rows="5" class="w-full bg-slate-900 border border-slate-700 rounded p-3 text-sm focus:outline-none focus:border-sky-500 text-slate-100 resize-none" placeholder="e.g. Design a ride-sharing dispatch system like Uber for 30M daily users on AWS with low latency matching..."></textarea>

                <div class="space-y-1.5">
                    <span class="text-xs text-slate-400">Sample Templates:</span>
                    <div class="flex flex-wrap gap-1.5">
                        <button onclick="setPrompt('Design a ride-sharing dispatch and driver-rider matching system like Uber for 30M daily users on AWS')" class="text-xs px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300">🚗 Uber Dispatch</button>
                        <button onclick="setPrompt('Design an e-commerce flash sale platform for Amazon Prime Day handling 100M active shoppers on AWS')" class="text-xs px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300">🛒 Amazon Flash Sale</button>
                        <button onclick="setPrompt('Design a global payments gateway for Stripe handling 50M daily transactions with sub-10ms latency on AWS')" class="text-xs px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300">💳 Stripe Payments</button>
                        <button onclick="setPrompt('Design a video streaming and recommendation architecture like Netflix for 75M users on GCP')" class="text-xs px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300">🎬 Netflix Streaming</button>
                    </div>
                </div>

                <button id="runBtn" onclick="runLangGraph()" class="w-full py-2.5 rounded bg-sky-500 hover:bg-sky-400 text-slate-950 font-bold text-sm transition shadow-lg shadow-sky-500/20">
                    🚀 Run LangGraph Multi-Agent Workflow
                </button>
            </div>

            <!-- LangGraph Execution Lifecycle Stages -->
            <div class="panel p-5 space-y-3">
                <h3 class="text-xs font-bold text-slate-400 uppercase tracking-wider">LangGraph Agent Execution</h3>
                <div class="space-y-2 text-xs">
                    <div id="stage-analyzer" class="flex justify-between items-center p-2 rounded bg-slate-900 border border-slate-800">
                        <span>🔍 <strong>1. RequirementAnalyzer</strong> (Gemini LLM)</span>
                        <span class="status font-mono text-slate-500">Idle</span>
                    </div>
                    <div id="stage-generator" class="flex justify-between items-center p-2 rounded bg-slate-900 border border-slate-800">
                        <span>🏗️ <strong>2. ArchitectureGenerator</strong> (Gemini LLM)</span>
                        <span class="status font-mono text-slate-500">Idle</span>
                    </div>
                    <div id="stage-critic" class="flex justify-between items-center p-2 rounded bg-slate-900 border border-slate-800">
                        <span>🛡️ <strong>3. ArchitectureCritic</strong> (8 Pillars)</span>
                        <span class="status font-mono text-slate-500">Idle</span>
                    </div>
                    <div id="stage-refiner" class="flex justify-between items-center p-2 rounded bg-slate-900 border border-slate-800">
                        <span>🔧 <strong>4. RefinementAgent</strong> (Feedback Loop)</span>
                        <span class="status font-mono text-slate-500">Idle</span>
                    </div>
                    <div id="stage-synthesizer" class="flex justify-between items-center p-2 rounded bg-slate-900 border border-slate-800">
                        <span>📋 <strong>5. SynthesizerAgent</strong> (Dossier & Diagram)</span>
                        <span class="status font-mono text-slate-500">Idle</span>
                    </div>
                </div>
            </div>
        </div>

        <!-- Right Output Column (7 cols) -->
        <div class="lg:col-span-7 space-y-5">

            <!-- Empty State -->
            <div id="emptyView" class="panel p-12 text-center text-slate-400 space-y-2">
                <div class="text-4xl">🏛️</div>
                <div class="font-semibold text-slate-300">Architecture Prototype Output</div>
                <div class="text-xs">Enter your prompt on the left and run the LangGraph workflow to generate the visual diagram and capacity report.</div>
            </div>

            <!-- Results View -->
            <div id="resultView" class="space-y-5 hidden">

                <!-- Title & Scorecard Banner -->
                <div class="panel p-5 flex flex-wrap justify-between items-center gap-3">
                    <div>
                        <h2 id="outTitle" class="text-lg font-bold text-white">System Title</h2>
                        <div class="text-xs text-sky-400 mt-1" id="outMeta">Domain | Style | Cloud</div>
                    </div>
                    <div class="text-center px-4 py-2 rounded bg-slate-900 border border-slate-700">
                        <div id="outScore" class="text-2xl font-black text-emerald-400">--</div>
                        <div class="text-[10px] uppercase text-slate-400">Critic Score</div>
                    </div>
                </div>

                <!-- Capacity Stats -->
                <div class="grid grid-cols-2 sm:grid-cols-3 gap-3">
                    <div class="panel p-3 text-center">
                        <div class="text-[11px] text-slate-400 uppercase">DAU</div>
                        <div id="statDau" class="text-base font-bold text-white mt-0.5">--</div>
                    </div>
                    <div class="panel p-3 text-center">
                        <div class="text-[11px] text-slate-400 uppercase">Peak Throughput</div>
                        <div id="statPeak" class="text-base font-bold text-sky-400 mt-0.5">--</div>
                    </div>
                    <div class="panel p-3 text-center">
                        <div class="text-[11px] text-slate-400 uppercase">Peak Bandwidth</div>
                        <div id="statBw" class="text-base font-bold text-indigo-400 mt-0.5">--</div>
                    </div>
                    <div class="panel p-3 text-center">
                        <div class="text-[11px] text-slate-400 uppercase">5-Yr Multi-AZ Storage</div>
                        <div id="statStorage" class="text-base font-bold text-amber-400 mt-0.5">--</div>
                    </div>
                    <div class="panel p-3 text-center">
                        <div class="text-[11px] text-slate-400 uppercase">Redis 80/20 RAM</div>
                        <div id="statRam" class="text-base font-bold text-emerald-400 mt-0.5">--</div>
                    </div>
                    <div class="panel p-3 text-center">
                        <div class="text-[11px] text-slate-400 uppercase">Kubernetes Pods</div>
                        <div id="statPods" class="text-base font-bold text-white mt-0.5">--</div>
                    </div>
                </div>

                <!-- Visual Mermaid Diagram -->
                <div class="panel p-5 space-y-3">
                    <div class="flex justify-between items-center">
                        <h3 class="text-xs font-bold text-sky-400 uppercase tracking-wider">Visual Architecture Topology (Mermaid.js)</h3>
                        <span class="text-xs text-slate-400">Live Render</span>
                    </div>
                    <div id="diagramContainer" class="bg-slate-950 p-4 rounded border border-slate-800 overflow-x-auto min-h-[220px] flex items-center justify-center">
                        <div id="mermaidTarget" class="w-full text-center"></div>
                    </div>
                </div>

                <!-- 8-Pillar Scorecard -->
                <div class="panel p-5 space-y-3">
                    <h3 class="text-xs font-bold text-sky-400 uppercase tracking-wider">Critic 8-Pillar Audit Breakdown</h3>
                    <table class="w-full text-left text-xs">
                        <thead class="text-slate-400 border-b border-slate-800 uppercase">
                            <tr>
                                <th class="pb-2">Evaluation Pillar</th>
                                <th class="pb-2 text-right">Weight</th>
                                <th class="pb-2 text-right">Score</th>
                                <th class="pb-2 text-center">Status</th>
                            </tr>
                        </thead>
                        <tbody id="scorecardBody" class="divide-y divide-slate-800"></tbody>
                    </table>
                </div>

                <!-- Download Actions -->
                <div class="panel p-4 flex justify-between items-center">
                    <span class="text-xs text-slate-300 font-medium">Download Production Dossier:</span>
                    <div class="flex gap-2">
                        <a id="downloadMdLink" href="#" download class="px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs font-semibold text-slate-200">📄 Markdown (.md)</a>
                        <a id="downloadHtmlLink" href="#" download class="px-3 py-1.5 rounded bg-sky-600 hover:bg-sky-500 text-xs font-semibold text-white">🌐 Standalone HTML</a>
                    </div>
                </div>

            </div>

        </div>

    </div>

    <script>
        function setPrompt(text) {
            document.getElementById('promptInput').value = text;
        }

        async function checkKeyStatus() {
            try {
                const res = await fetch('/api/key_status');
                const data = await res.json();
                const dot = document.getElementById('keyDot');
                const text = document.getElementById('keyText');
                if (data.configured) {
                    dot.className = 'w-2 h-2 rounded-full bg-emerald-400 animate-pulse';
                    text.innerText = '.env: GEMINI_API_KEY Configured';
                } else {
                    dot.className = 'w-2 h-2 rounded-full bg-amber-400';
                    text.innerText = '.env: GEMINI_API_KEY Missing';
                }
            } catch (e) {}
        }

        function setStage(stage, status, isDone=false) {
            const el = document.getElementById('stage-' + stage);
            if (!el) return;
            const statusSpan = el.querySelector('.status');
            statusSpan.innerText = status;
            if (isDone) {
                statusSpan.className = 'status font-mono text-emerald-400 font-bold';
            } else {
                statusSpan.className = 'status font-mono text-amber-400 animate-pulse font-bold';
            }
        }

        async function runLangGraph() {
            const prompt = document.getElementById('promptInput').value.trim();
            if (!prompt) return alert('Please enter an architecture requirement.');

            const btn = document.getElementById('runBtn');
            btn.innerHTML = '<span>⚙️ Running LangGraph State Machine...</span>';
            btn.disabled = true;

            // Mark pipeline active
            ['analyzer', 'generator', 'critic', 'refiner', 'synthesizer'].forEach(s => setStage(s, 'Running...'));

            try {
                const res = await fetch('/api/run_workflow', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({prompt: prompt})
                });

                if (!res.ok) {
                    const errData = await res.json();
                    throw new Error(errData.detail || errData.error || 'Workflow execution failed');
                }

                const data = await res.json();

                // Mark stages completed
                ['analyzer', 'generator', 'critic', 'refiner', 'synthesizer'].forEach(s => setStage(s, 'Completed', true));

                // Populate UI
                document.getElementById('emptyView').classList.add('hidden');
                document.getElementById('resultView').classList.remove('hidden');

                const dossier = data.dossier;
                const sc = dossier.final_scorecard;
                const cap = dossier.capacity_planning;

                document.getElementById('outTitle').innerText = dossier.title;
                document.getElementById('outMeta').innerText = `${dossier.domain} | ${dossier.style} | ${dossier.cloud}`;
                document.getElementById('outScore').innerText = sc.overall_score;

                document.getElementById('statDau').innerText = cap.traffic.dau.toLocaleString();
                document.getElementById('statPeak').innerText = cap.traffic.peak_qps.toLocaleString() + ' QPS';
                document.getElementById('statBw').innerText = cap.network.egress_bandwidth_gbps.toFixed(2) + ' Gbps';
                document.getElementById('statStorage').innerText = cap.storage.effective_5yr_storage_tb.toFixed(1) + ' TB';
                document.getElementById('statRam').innerText = cap.cache.cache_memory_ram_gb.toFixed(0) + ' GB';
                document.getElementById('statPods').innerText = '~' + cap.recommended_compute_pods;

                // Render Scorecard
                const tbody = document.getElementById('scorecardBody');
                tbody.innerHTML = sc.pillar_breakdown.map(p => `
                    <tr>
                        <td class="py-2">${p.pillar}</td>
                        <td class="py-2 text-right font-mono">${Math.round(p.weight * 100)}%</td>
                        <td class="py-2 text-right font-mono font-bold ${p.raw_score >= 80 ? 'text-emerald-400' : 'text-amber-400'}">${p.raw_score.toFixed(1)}</td>
                        <td class="py-2 text-center"><span class="px-2 py-0.5 rounded text-[10px] font-bold ${p.passed ? 'bg-emerald-950 text-emerald-400 border border-emerald-800' : 'bg-amber-950 text-amber-400 border border-amber-800'}">${p.passed ? 'PASS' : 'REVIEW'}</span></td>
                    </tr>
                `).join('');

                // Render Mermaid Diagram
                const target = document.getElementById('mermaidTarget');
                target.innerHTML = '';
                const { svg } = await window.mermaid.render('mermaid-svg-' + Date.now(), dossier.mermaid_diagram);
                target.innerHTML = svg;

                // Setup Download links
                if (data.saved_files) {
                    document.getElementById('downloadMdLink').href = '/file?path=' + encodeURIComponent(data.saved_files.markdown);
                    document.getElementById('downloadHtmlLink').href = '/file?path=' + encodeURIComponent(data.saved_files.html);
                }

            } catch (err) {
                alert('LangGraph Error: ' + err.message);
                ['analyzer', 'generator', 'critic', 'refiner', 'synthesizer'].forEach(s => setStage(s, 'Error'));
            } finally {
                btn.innerHTML = '<span>🚀 Run LangGraph Multi-Agent Workflow</span>';
                btn.disabled = false;
            }
        }

        // Check key status on initial load
        checkKeyStatus();
    </script>
</body>
</html>
"""


class PrototypeRequestHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path in ["/", "/index.html"]:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(PROTOTYPE_HTML.encode("utf-8"))
            return

        elif parsed.path == "/api/key_status":
            load_dotenv(override=True)
            key = os.getenv("GEMINI_API_KEY", "")
            configured = bool(key and len(key.strip()) > 10)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"configured": configured}).encode("utf-8"))
            return

        elif parsed.path == "/file":
            qs = urllib.parse.parse_qs(parsed.query)
            file_path = qs.get("path", [None])[0]
            if file_path and os.path.exists(file_path):
                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Content-Disposition", f"attachment; filename={os.path.basename(file_path)}")
                self.end_headers()
                with open(file_path, "rb") as f:
                    self.wfile.write(f.read())
                return
            else:
                self.send_response(404)
                self.end_headers()
                return

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len).decode("utf-8")
        payload = json.loads(body) if body else {}

        if parsed.path == "/api/run_workflow":
            load_dotenv(override=True)
            prompt = payload.get("prompt", "")
            if not os.getenv("GEMINI_API_KEY"):
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "error": "GEMINI_API_KEY is not set in .env! Please add: GEMINI_API_KEY=your_key to your .env file."
                }).encode("utf-8"))
                return

            try:
                workflow = NirmanWorkflow()
                result = workflow.run(prompt, max_iterations=2)

                dossier_dict = result["dossier"].model_dump()
                response_data = {
                    "dossier": dossier_dict,
                    "saved_files": result["saved_files"],
                    "iterations": result["iterations"],
                }

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(response_data, default=str).encode("utf-8"))
                return
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
                return

        self.send_response(404)
        self.end_headers()

    def log_message(self, format, *args):
        pass


def start_prototype_server(port: int = 8080):
    try:
        if sys.stdout and hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    server = ThreadingHTTPServer(("0.0.0.0", port), PrototypeRequestHandler)
    print("=" * 80)
    print(f"[NirmanAI] Prototype UI (LangGraph + Gemini) running at: http://localhost:{port}")
    print("=" * 80)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.server_close()


if __name__ == "__main__":
    start_prototype_server(8080)
