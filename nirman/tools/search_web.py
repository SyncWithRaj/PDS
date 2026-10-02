"""
NirmanAI - SearchWeb Tool
==========================
Searches the web using DuckDuckGo and returns top results.
No API key required. Agents use this to research architecture patterns,
compliance requirements, benchmarks, and best practices.
"""

import logging
from typing import Dict, Any
from nirman.tools import Tool

logger = logging.getLogger("nirman.tools.search")


class SearchWebTool(Tool):
    """Search the web for architecture patterns, benchmarks, and best practices."""

    @property
    def name(self) -> str:
        return "search_web"

    @property
    def description(self) -> str:
        return (
            "Search the web for a query. Returns top 5 results with titles, "
            "snippets, and URLs. Use this to research architecture patterns, "
            "compliance requirements, cloud service benchmarks, and best practices "
            "BEFORE making design decisions."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query (e.g., 'AWS RAG reference architecture 2024')"
                }
            },
            "required": ["query"]
        }

    def execute(self, **kwargs) -> str:
        """Execute web search and return formatted results."""
        query = kwargs.get("query", "")
        if not query:
            return "Error: No search query provided."

        try:
            try:
                from ddgs import DDGS
            except ImportError:
                from duckduckgo_search import DDGS

            logger.info(f"🔍 Searching: '{query}'")
            results = []
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=5):
                    results.append(r)

            if not results:
                return f"No results found for: '{query}'"

            formatted = []
            for i, r in enumerate(results, 1):
                title = r.get("title", "No title")
                snippet = r.get("body", "No snippet")
                url = r.get("href", "No URL")
                formatted.append(f"[{i}] {title}\n    {snippet}\n    URL: {url}")

            output = f"Search results for '{query}':\n\n" + "\n\n".join(formatted)
            logger.info(f"✅ Found {len(results)} results for '{query}'")
            return output

        except ImportError:
            return "Error: duckduckgo_search package not installed. Install with: pip install duckduckgo_search"
        except Exception as e:
            logger.warning(f"Search failed for '{query}': {e}")
            return f"Search failed: {str(e)}. Proceeding with existing knowledge."
