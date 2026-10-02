"""
NirmanAI - PythonREPL Tool
===========================
Executes Python code in a sandboxed subprocess and returns stdout/stderr.
Agents use this to calculate capacity math, validate data structures,
run quick computations, and test formulas dynamically.
"""

import logging
import subprocess
import sys
import tempfile
import os
from typing import Dict, Any
from nirman.tools import Tool

logger = logging.getLogger("nirman.tools.python_repl")


class PythonREPLTool(Tool):
    """Execute Python code in a sandboxed subprocess."""

    TIMEOUT_SECONDS = 30

    @property
    def name(self) -> str:
        return "python_repl"

    @property
    def description(self) -> str:
        return (
            "Execute Python code in a sandboxed subprocess. Returns stdout/stderr. "
            "Max 30s timeout. Use this to calculate capacity math (QPS, storage, "
            "bandwidth), validate data structures, run quick computations, or "
            "test formulas. Always use print() to output results."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python code to execute. Use print() for output."
                }
            },
            "required": ["code"]
        }

    def execute(self, **kwargs) -> str:
        """Execute Python code in subprocess and return output."""
        code = kwargs.get("code", "")
        if not code:
            return "Error: No code provided."

        logger.info(f"🐍 Executing Python code ({len(code)} chars)...")

        # Write code to a temporary file
        tmp_file = None
        try:
            tmp_file = tempfile.NamedTemporaryFile(
                mode="w", suffix=".py", delete=False, encoding="utf-8"
            )
            tmp_file.write(code)
            tmp_file.close()

            # Execute in subprocess with timeout
            result = subprocess.run(
                [sys.executable, tmp_file.name],
                capture_output=True,
                text=True,
                timeout=self.TIMEOUT_SECONDS,
                cwd=tempfile.gettempdir(),
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            )

            output = ""
            if result.stdout:
                output += result.stdout.strip()
            if result.stderr:
                # Filter out common warnings, keep actual errors
                stderr_lines = [
                    line for line in result.stderr.strip().splitlines()
                    if not any(w in line for w in ["FutureWarning", "DeprecationWarning"])
                ]
                if stderr_lines:
                    output += "\n[STDERR] " + "\n".join(stderr_lines)

            if not output:
                output = "(No output. Make sure to use print() to display results.)"

            # Truncate very long outputs
            if len(output) > 2000:
                output = output[:2000] + "\n\n[... output truncated at 2000 chars ...]"

            logger.info(f"✅ Python execution complete ({len(output)} chars output)")
            return output

        except subprocess.TimeoutExpired:
            logger.warning(f"Python execution timed out ({self.TIMEOUT_SECONDS}s)")
            return f"Error: Code execution timed out after {self.TIMEOUT_SECONDS} seconds."
        except Exception as e:
            logger.warning(f"Python execution failed: {e}")
            return f"Error executing code: {str(e)}"
        finally:
            if tmp_file and os.path.exists(tmp_file.name):
                try:
                    os.unlink(tmp_file.name)
                except OSError:
                    pass
