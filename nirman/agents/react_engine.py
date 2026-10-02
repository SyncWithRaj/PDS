"""
NirmanAI - ReAct Engine
========================
The core autonomous agent loop. Every agentic component in NirmanAI
uses this engine to THINK → ACT → OBSERVE in a reasoning loop.

This is NOT a wrapper. This is an autonomous decision-making engine.
The agent decides its own next action based on its goal, history, and
available tools. It stops when it has enough information to answer.

Architecture:
    ReActEngine receives: goal, persona, tools, output_schema
    ReActEngine runs: autonomous loop (max_steps iterations)
    Each iteration: LLM decides → TOOL_CALL or FINAL_ANSWER
    On TOOL_CALL: execute tool, add observation to history, loop
    On FINAL_ANSWER: parse structured output, return
    On max_steps: force final answer from accumulated knowledge
"""

import re
import json
import logging
from typing import Dict, Any, Optional, List, Type
from pydantic import BaseModel

from nirman.tools import Tool
from nirman.agents.gemini_client import GeminiClient

logger = logging.getLogger("nirman.react")


# === ReAct Prompt Template ===
REACT_SYSTEM_TEMPLATE = """You are {persona}.

You are an autonomous AI agent that THINKS step-by-step, uses TOOLS to gather information, and provides a FINAL_ANSWER only when you have enough evidence.

YOUR GOAL:
{goal}

{tool_descriptions}

CONVERSATION HISTORY:
{history}

RULES:
1. THINK step-by-step about what you need to do next.
2. You MUST use at least 2 tools before providing your FINAL_ANSWER. This is NON-NEGOTIABLE.
3. On your FIRST step, you MUST use a tool (search_web or read_url) to research. Do NOT skip research.
4. DO NOT provide FINAL_ANSWER on your first step. Always research first.
5. If you need more information, use a tool. DO NOT GUESS — research first.
6. You may use tools multiple times. Each tool call gives you new observations.
7. When you have gathered ENOUGH information (after at least 2 tool uses), provide your FINAL_ANSWER.
8. Your FINAL_ANSWER must be valid JSON matching the required output schema.
9. Do NOT repeat the same tool call with the same input.

RESPONSE FORMAT — You MUST respond in EXACTLY one of these two formats:

FORMAT A (when you need to use a tool):
THOUGHT: [Your reasoning about what you need to do next and why]
ACTION: [tool_name]
ACTION_INPUT: [tool arguments as a JSON object]

FORMAT B (when you're ready to give the final answer):
THOUGHT: [Your reasoning about why you have enough information]
FINAL_ANSWER:
[Your complete JSON output matching the required schema]

OUTPUT SCHEMA (your FINAL_ANSWER must match this):
{output_schema}

IMPORTANT: Respond with ONLY Format A or Format B. Nothing else."""


class ReActStep(BaseModel):
    """A single step in the ReAct reasoning trace."""
    step: int
    thought: str
    action: Optional[str] = None
    action_input: Optional[Dict[str, Any]] = None
    observation: Optional[str] = None


class ReActResult(BaseModel):
    """The complete result of a ReAct agent run."""
    output: Any  # The parsed final answer
    steps: List[ReActStep]  # Full reasoning trace
    total_steps: int
    tools_used: List[str]
    forced_final: bool = False  # True if we hit max_steps and forced an answer


class ReActEngine:
    """
    Core autonomous agent loop.

    The engine sends the LLM a prompt with:
    - The agent's GOAL (what it needs to accomplish)
    - The agent's PERSONA (who it is)
    - Available TOOLS (with descriptions and parameter schemas)
    - Conversation HISTORY (previous thoughts, actions, observations)
    - Output SCHEMA (what the final answer must look like)

    The LLM responds with either:
    - THOUGHT + ACTION (use a tool) → engine executes tool, adds observation
    - THOUGHT + FINAL_ANSWER (structured output) → engine parses and returns it
    """

    def __init__(
        self,
        gemini_client: GeminiClient,
        persona: str,
        tools: Dict[str, Tool],
        output_schema: Type[BaseModel],
        max_steps: int = 10,
    ):
        self.client = gemini_client
        self.persona = persona
        self.tools = tools
        self.output_schema = output_schema
        self.max_steps = max_steps

    def run(self, goal: str) -> ReActResult:
        """Run the autonomous ReAct loop until the agent is satisfied or max_steps reached."""
        history: List[ReActStep] = []
        tools_used: List[str] = []

        logger.info(f"🤖 ReAct Agent starting | Persona: {self.persona[:50]}... | Max steps: {self.max_steps}")
        logger.info(f"   Goal: {goal[:100]}...")
        logger.info(f"   Tools available: {list(self.tools.keys())}")

        for step_num in range(1, self.max_steps + 1):
            # Build the prompt with current history
            prompt = self._build_prompt(goal, history)

            # Ask the LLM to THINK and decide next action
            logger.info(f"   Step {step_num}/{self.max_steps}: Thinking...")

            # Dynamic user prompt — force tool usage if agent hasn't used any yet
            if len(tools_used) == 0 and self.tools and step_num <= self.max_steps - 1:
                tool_names = list(self.tools.keys())
                user_msg = (
                    f"You MUST use a tool now. Pick one of: {tool_names}. "
                    f"Respond with:\nTHOUGHT: [your reasoning]\n"
                    f"ACTION: {tool_names[0]}\n"
                    f"ACTION_INPUT: {{\"query\": \"your search query\"}}"
                )
            else:
                user_msg = "Continue your analysis. What is your next step?"

            try:
                response_text = self.client.generate_text(
                    system_prompt=prompt,
                    user_prompt=user_msg,
                )
            except Exception as e:
                logger.warning(f"   Step {step_num}: LLM call failed: {e}")
                # Try to force a final answer with what we have
                return self._force_final_answer(goal, history, tools_used, reason=str(e))

            # Parse the LLM response — suppress implicit JSON as FINAL_ANSWER if no tools used
            parsed = self._parse_response(response_text, allow_implicit_final=(len(tools_used) >= 1 or step_num >= self.max_steps - 1))

            if parsed["type"] == "FINAL_ANSWER":
                # Enforce minimum tool usage — agents MUST research before answering
                min_tool_calls = 1  # At least 1 tool call
                if len(tools_used) < min_tool_calls and step_num < self.max_steps - 1 and self.tools:
                    logger.info(
                        f"   Step {step_num}: Agent tried FINAL_ANSWER too early "
                        f"({len(tools_used)}/{min_tool_calls} tools used). Redirecting to use tools."
                    )
                    # Pick the first available tool and suggest a reasonable query
                    first_tool = list(self.tools.keys())[0]
                    history.append(ReActStep(
                        step=step_num,
                        thought=(
                            f"I must use at least {min_tool_calls} tool(s) before answering. "
                            f"I will use the '{first_tool}' tool to research before giving my final answer."
                        ),
                    ))
                    continue

                logger.info(f"   Step {step_num}: Agent provided FINAL_ANSWER")
                thought = parsed.get("thought", "Ready to answer.")

                history.append(ReActStep(
                    step=step_num,
                    thought=thought,
                    action="FINAL_ANSWER",
                ))

                # Parse the final answer
                try:
                    # Check if the "final answer" is actually a disguised tool call
                    content = parsed["content"]
                    try:
                        maybe_json = json.loads(content) if isinstance(content, str) else content
                        if isinstance(maybe_json, dict) and ("action" in maybe_json or "tool_name" in maybe_json):
                            # It's a tool call in JSON format — execute it
                            tool_name = maybe_json.get("action") or maybe_json.get("tool_name", "")
                            tool_args = maybe_json.get("action_input") or maybe_json.get("tool_args", {})
                            if isinstance(tool_args, str):
                                tool_args = {"query": tool_args}
                            if tool_name in self.tools:
                                logger.info(f"   Step {step_num}: Detected tool call in FINAL_ANSWER → executing {tool_name}")
                                observation = self._execute_tool(tool_name, tool_args)
                                logger.info(f"   Step {step_num}: OBSERVE → {observation[:100]}...")
                                history[-1] = ReActStep(
                                    step=step_num,
                                    thought=maybe_json.get("thought", ""),
                                    action=tool_name,
                                    action_input=tool_args,
                                    observation=observation[:2000],
                                )
                                tools_used.append(tool_name)
                                continue
                    except (json.JSONDecodeError, TypeError):
                        pass

                    output = self._parse_final_answer(content)
                    logger.info(f"✅ ReAct Agent completed in {step_num} steps, {len(tools_used)} tool calls")
                    return ReActResult(
                        output=output,
                        steps=history,
                        total_steps=step_num,
                        tools_used=tools_used,
                        forced_final=False,
                    )
                except Exception as e:
                    logger.warning(f"   Failed to parse FINAL_ANSWER: {e}. Retrying...")
                    history.append(ReActStep(
                        step=step_num,
                        thought=f"My previous answer had a parsing error: {e}. Let me fix it.",
                    ))
                    continue

            elif parsed["type"] == "TOOL_CALL":
                tool_name = parsed["tool_name"]
                tool_args = parsed.get("tool_args", {})
                thought = parsed.get("thought", "Using a tool.")

                logger.info(f"   Step {step_num}: THINK → {thought[:80]}...")
                logger.info(f"   Step {step_num}: ACT → {tool_name}({json.dumps(tool_args)[:80]}...)")

                # Execute the tool
                observation = self._execute_tool(tool_name, tool_args)

                logger.info(f"   Step {step_num}: OBSERVE → {observation[:100]}...")

                history.append(ReActStep(
                    step=step_num,
                    thought=thought,
                    action=tool_name,
                    action_input=tool_args,
                    observation=observation[:2000],  # Truncate long observations
                ))
                tools_used.append(tool_name)

            else:
                # Couldn't parse the response
                if len(tools_used) == 0 and self.tools and step_num < self.max_steps - 1:
                    # Auto-trigger first tool with a query from the goal
                    first_tool_name = list(self.tools.keys())[0]
                    # Extract a short query from the goal (first 100 chars, cleaned)
                    goal_snippet = goal[:200].replace('\n', ' ').strip()
                    # Use a reasonable search query
                    auto_query = f"{goal_snippet[:100]} best practices architecture"
                    
                    logger.info(f"   Step {step_num}: Auto-triggering '{first_tool_name}' (LLM didn't use ACTION format)")
                    observation = self._execute_tool(first_tool_name, {"query": auto_query})
                    logger.info(f"   Step {step_num}: OBSERVE → {observation[:100]}...")
                    
                    history.append(ReActStep(
                        step=step_num,
                        thought=f"Auto-research: Using {first_tool_name} to gather domain knowledge.",
                        action=first_tool_name,
                        action_input={"query": auto_query},
                        observation=observation[:2000],
                    ))
                    tools_used.append(first_tool_name)
                else:
                    logger.warning(f"   Step {step_num}: Could not parse LLM response. Retrying...")
                    history.append(ReActStep(
                        step=step_num,
                        thought="(Agent response was unparseable. Retrying with clearer format.)",
                    ))

        # Max steps reached — force final answer
        logger.warning(f"⚠️ ReAct Agent hit max_steps ({self.max_steps}). Forcing final answer.")
        return self._force_final_answer(goal, history, tools_used)

    def _build_prompt(self, goal: str, history: List[ReActStep]) -> str:
        """Build the full ReAct prompt with history."""
        # Format tool descriptions
        tool_lines = []
        for tool in self.tools.values():
            tool_lines.append(tool.to_prompt_description())
        tool_desc = "AVAILABLE TOOLS:\n" + "\n".join(tool_lines) if tool_lines else "No tools available."

        # Format history
        if history:
            history_lines = []
            for step in history:
                history_lines.append(f"Step {step.step}:")
                history_lines.append(f"  THOUGHT: {step.thought}")
                if step.action and step.action != "FINAL_ANSWER":
                    history_lines.append(f"  ACTION: {step.action}")
                    if step.action_input:
                        history_lines.append(f"  ACTION_INPUT: {json.dumps(step.action_input)}")
                    if step.observation:
                        history_lines.append(f"  OBSERVATION: {step.observation}")
            history_str = "\n".join(history_lines)
        else:
            history_str = "(No previous steps. This is step 1.)"

        # Format output schema
        schema_str = json.dumps(self.output_schema.model_json_schema(), indent=2)

        return REACT_SYSTEM_TEMPLATE.format(
            persona=self.persona,
            goal=goal,
            tool_descriptions=tool_desc,
            history=history_str,
            output_schema=schema_str,
        )

    def _parse_response(self, text: str, allow_implicit_final: bool = True) -> Dict[str, Any]:
        """Parse LLM response into either TOOL_CALL or FINAL_ANSWER."""
        text = text.strip()

        # Try to detect FINAL_ANSWER
        final_match = re.search(
            r"FINAL_ANSWER\s*:\s*\n?(.*)",
            text,
            re.DOTALL | re.IGNORECASE,
        )
        if final_match:
            thought_match = re.search(
                r"THOUGHT\s*:\s*(.+?)(?=FINAL_ANSWER)",
                text,
                re.DOTALL | re.IGNORECASE,
            )
            thought = thought_match.group(1).strip() if thought_match else ""
            content = final_match.group(1).strip()
            return {"type": "FINAL_ANSWER", "thought": thought, "content": content}

        # Try to detect TOOL_CALL (ACTION + ACTION_INPUT)
        action_match = re.search(
            r"ACTION\s*:\s*(\w+)",
            text,
            re.IGNORECASE,
        )
        action_input_match = re.search(
            r"ACTION_INPUT\s*:\s*(\{.*?\}|\".+?\")",
            text,
            re.DOTALL | re.IGNORECASE,
        )
        thought_match = re.search(
            r"THOUGHT\s*:\s*(.+?)(?=ACTION\s*:)",
            text,
            re.DOTALL | re.IGNORECASE,
        )

        if action_match:
            tool_name = action_match.group(1).strip()
            thought = thought_match.group(1).strip() if thought_match else ""

            tool_args = {}
            if action_input_match:
                try:
                    raw = action_input_match.group(1).strip()
                    tool_args = json.loads(raw)
                    if isinstance(tool_args, str):
                        # Handle case where ACTION_INPUT is a plain string
                        tool_args = {"query": tool_args}
                except json.JSONDecodeError:
                    # Try to extract key-value pairs from malformed JSON
                    tool_args = {"query": action_input_match.group(1).strip().strip('"')}

            return {
                "type": "TOOL_CALL",
                "thought": thought,
                "tool_name": tool_name,
                "tool_args": tool_args,
            }

        # Check if the entire response is JSON (implicit FINAL_ANSWER)
        # Only allow this if the agent has used enough tools
        if allow_implicit_final:
            try:
                json_match = re.search(r'\{.*\}', text, re.DOTALL)
                if json_match:
                    json.loads(json_match.group())
                    return {"type": "FINAL_ANSWER", "thought": "", "content": json_match.group()}
            except (json.JSONDecodeError, AttributeError):
                pass

        return {"type": "UNPARSEABLE", "raw": text}

    def _execute_tool(self, tool_name: str, tool_args: Dict[str, Any]) -> str:
        """Execute a tool by name with given arguments."""
        tool = self.tools.get(tool_name)
        if not tool:
            available = list(self.tools.keys())
            return f"Error: Tool '{tool_name}' not found. Available tools: {available}"

        try:
            return tool.execute(**tool_args)
        except Exception as e:
            logger.warning(f"Tool '{tool_name}' execution failed: {e}")
            return f"Tool execution failed: {str(e)}. Try a different approach."

    def _parse_final_answer(self, content: str) -> BaseModel:
        """Parse FINAL_ANSWER content into the output schema."""
        # Try to extract JSON from the content
        content = content.strip()

        # Remove markdown code fences if present
        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?\s*\n?", "", content)
            content = re.sub(r"\n?```\s*$", "", content)

        # Find the JSON object
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if not json_match:
            raise ValueError(f"No JSON object found in FINAL_ANSWER: {content[:200]}...")

        data = json.loads(json_match.group())
        return self.output_schema.model_validate(data)

    def _force_final_answer(
        self,
        goal: str,
        history: List[ReActStep],
        tools_used: List[str],
        reason: str = "max steps reached",
    ) -> ReActResult:
        """Force the agent to produce a final answer from accumulated knowledge."""
        logger.info(f"   Forcing final answer ({reason})...")

        # Collect all observations from history
        observations = []
        for step in history:
            if step.observation:
                observations.append(f"From {step.action}: {step.observation[:500]}")

        observations_text = "\n".join(observations) if observations else "No observations gathered."

        # Ask LLM to produce final answer directly
        force_prompt = (
            f"You are {self.persona}.\n\n"
            f"GOAL: {goal}\n\n"
            f"You have gathered the following research:\n{observations_text}\n\n"
            f"Based on ALL the information above, produce your FINAL answer as JSON "
            f"matching this schema:\n{json.dumps(self.output_schema.model_json_schema(), indent=2)}\n\n"
            f"Respond with ONLY the JSON object. No explanation."
        )

        try:
            output = self.client.generate_structured(
                system_prompt=force_prompt,
                user_prompt="Produce your final structured answer now.",
                schema=self.output_schema,
            )
            return ReActResult(
                output=output,
                steps=history,
                total_steps=len(history),
                tools_used=tools_used,
                forced_final=True,
            )
        except Exception as e:
            logger.error(f"Failed to force final answer: {e}")
            raise RuntimeError(
                f"ReAct agent failed to produce output after {len(history)} steps: {e}"
            )
