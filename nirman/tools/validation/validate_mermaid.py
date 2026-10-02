"""
NirmanAI - ValidateMermaid Tool
================================
Parses and validates Mermaid diagram syntax. Returns "valid" or error details.
Agents use this to self-check their generated diagrams before submitting.
"""

import re
import logging
from typing import Dict, Any
from nirman.tools import Tool

logger = logging.getLogger("nirman.tools.validate_mermaid")


class ValidateMermaidTool(Tool):
    """Parse and validate Mermaid diagram syntax."""

    @property
    def name(self) -> str:
        return "validate_mermaid"

    @property
    def description(self) -> str:
        return (
            "Parse a Mermaid diagram string and check for syntax errors. "
            "Returns 'valid' with node/edge counts, or error details with line numbers. "
            "Use this AFTER generating a Mermaid diagram to self-check before submitting."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "diagram": {
                    "type": "string",
                    "description": "Mermaid diagram code to validate"
                }
            },
            "required": ["diagram"]
        }

    def execute(self, **kwargs) -> str:
        """Validate Mermaid diagram syntax."""
        diagram = kwargs.get("diagram", "")
        if not diagram:
            return "Error: No diagram provided."

        logger.info("🔍 Validating Mermaid diagram...")
        errors = []
        lines = diagram.strip().splitlines()

        if not lines:
            return "Error: Empty diagram."

        # Check diagram type declaration
        first_line = lines[0].strip().lower()
        valid_types = ["flowchart", "graph", "sequencediagram", "classDiagram",
                       "statediagram", "erdiagram", "sequencediagram"]
        has_type = any(first_line.startswith(t.lower()) for t in valid_types)
        if not has_type:
            errors.append(f"Line 1: Missing or invalid diagram type. Got: '{lines[0].strip()}'. "
                         f"Expected: flowchart TD, sequenceDiagram, classDiagram, etc.")

        # Track bracket balance
        open_brackets = 0
        open_quotes = 0
        node_ids = set()
        edge_count = 0
        subgraph_count = 0

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # Skip empty lines and comments
            if not stripped or stripped.startswith("%%"):
                continue

            # Check for unicode dashes (common LLM error)
            if "\u2011" in stripped or "\u2013" in stripped or "\u2014" in stripped:
                errors.append(f"Line {i}: Unicode dash detected. Use ASCII hyphens (-) only.")

            # Track subgraphs
            if stripped.startswith("subgraph"):
                subgraph_count += 1
                open_brackets += 1
            elif stripped == "end":
                open_brackets -= 1
                if open_brackets < 0:
                    errors.append(f"Line {i}: Unexpected 'end' without matching 'subgraph'.")

            # Track brackets in node labels
            for char in stripped:
                if char == '[':
                    open_quotes += 1
                elif char == ']':
                    open_quotes -= 1
                    if open_quotes < 0:
                        errors.append(f"Line {i}: Unmatched closing bracket ']'.")
                        open_quotes = 0

            # Check for unquoted special characters in node labels
            bracket_match = re.search(r'\[([^\]"]+)\]', stripped)
            if bracket_match:
                label = bracket_match.group(1)
                if any(c in label for c in ['(', ')', '&', '<', '>']):
                    errors.append(
                        f"Line {i}: Special characters in unquoted label: '{label}'. "
                        f"Wrap in quotes: [\"{label}\"]"
                    )

            # Count edges (arrows)
            if "-->" in stripped or "-.->'" in stripped or "-.->" in stripped or "==>" in stripped:
                edge_count += 1

            # Extract node IDs from definitions
            node_match = re.match(r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*[\[\({"]', stripped)
            if node_match:
                node_ids.add(node_match.group(1))

        # Check for unclosed brackets
        if open_quotes != 0:
            errors.append(f"Unclosed brackets detected ({open_quotes} unclosed).")

        # Check for unclosed subgraphs
        if open_brackets > 0:
            errors.append(f"{open_brackets} unclosed subgraph(s) — missing 'end' statement(s).")

        if errors:
            result = f"INVALID — {len(errors)} error(s) found:\n"
            for err in errors:
                result += f"  ❌ {err}\n"
            return result
        else:
            result = (
                f"VALID — Diagram looks correct.\n"
                f"  Nodes detected: {len(node_ids)}\n"
                f"  Edges detected: {edge_count}\n"
                f"  Subgraphs: {subgraph_count}\n"
                f"  Total lines: {len(lines)}"
            )
            logger.info(f"✅ Mermaid valid: {len(node_ids)} nodes, {edge_count} edges")
            return result
