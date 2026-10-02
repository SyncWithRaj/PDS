"""
NirmanAI - Tool System
======================
Base classes and exports for the agentic tool system.
Every tool follows a uniform interface: name, description, parameters, execute().
"""

from abc import ABC, abstractmethod
from typing import Dict, Any


class Tool(ABC):
    """Base class for all agent tools.
    
    Every tool has:
    - name: identifier the LLM uses to call it
    - description: human-readable explanation for the LLM's context
    - parameters: JSON Schema describing expected inputs
    - execute(): runs the tool and returns a string observation
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique tool identifier (e.g., 'search_web')."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description for the LLM."""
        ...

    @property
    @abstractmethod
    def parameters(self) -> Dict[str, Any]:
        """JSON Schema of expected input parameters."""
        ...

    @abstractmethod
    def execute(self, **kwargs) -> str:
        """Execute the tool and return a string observation."""
        ...

    def to_prompt_description(self) -> str:
        """Format this tool's info for inclusion in an LLM prompt."""
        params_str = ", ".join(
            f"{k}: {v.get('description', v.get('type', 'any'))}"
            for k, v in self.parameters.get("properties", {}).items()
        )
        return f"- **{self.name}**({params_str}): {self.description}"
