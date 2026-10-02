"""
NirmanAI - Tool Registry
=========================
Central registry that manages tool instances. Agents request tools by name
from the registry. Provides formatted tool descriptions for LLM prompts.
"""

from typing import Dict, List, Optional
from nirman.tools import Tool


class ToolRegistry:
    """Central registry for all available agent tools.
    
    Usage:
        registry = ToolRegistry()
        registry.register(SearchWebTool())
        registry.register(PythonREPLTool())
        
        # Agent picks the tools it needs
        tools = registry.get_tools(["search_web", "python_repl"])
    """

    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Register a tool instance."""
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[Tool]:
        """Get a tool by name."""
        return self._tools.get(name)

    def get_tools(self, names: List[str]) -> Dict[str, Tool]:
        """Get multiple tools by name. Raises KeyError if any not found."""
        tools = {}
        for name in names:
            if name not in self._tools:
                raise KeyError(f"Tool '{name}' not found. Available: {list(self._tools.keys())}")
            tools[name] = self._tools[name]
        return tools

    def all_tools(self) -> Dict[str, Tool]:
        """Get all registered tools."""
        return dict(self._tools)

    def format_for_prompt(self, tool_names: Optional[List[str]] = None) -> str:
        """Format tool descriptions for inclusion in an LLM ReAct prompt."""
        tools = self.get_tools(tool_names) if tool_names else self._tools
        lines = ["You have access to the following tools:\n"]
        for tool in tools.values():
            lines.append(tool.to_prompt_description())
        return "\n".join(lines)


def build_default_registry() -> ToolRegistry:
    """Build a registry with all default NirmanAI tools."""
    from nirman.tools.research.search_web import SearchWebTool
    from nirman.tools.research.read_url import ReadURLTool
    from nirman.tools.execution.python_repl import PythonREPLTool
    from nirman.tools.validation.validate_mermaid import ValidateMermaidTool

    registry = ToolRegistry()
    registry.register(SearchWebTool())
    registry.register(ReadURLTool())
    registry.register(PythonREPLTool())
    registry.register(ValidateMermaidTool())
    return registry
