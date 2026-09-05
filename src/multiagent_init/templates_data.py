FRAMEWORK_FILES = {
    "basic": """[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "{{PROJECT_NAME}}"
version = "0.1.0"
description = "A multi-agent AI application."
requires-python = ">=3.9"
dependencies = [
  "{{PROVIDER_DEPENDENCY}}",
]

[tool.setuptools]
package-dir = {"" = "src"}

[tool.setuptools.packages.find]
where = ["src"]
""",
    "langgraph": """[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "{{PROJECT_NAME}}"
version = "0.1.0"
description = "A LangGraph multi-agent AI application."
requires-python = ">=3.9"
dependencies = [
  "langgraph>=0.2",
  "{{PROVIDER_DEPENDENCY}}",
]

[tool.setuptools]
package-dir = {"" = "src"}

[tool.setuptools.packages.find]
where = ["src"]
""",
    "crewai": """[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "{{PROJECT_NAME}}"
version = "0.1.0"
description = "A CrewAI multi-agent AI application."
requires-python = ">=3.9"
dependencies = [
  "crewai>=0.80",
]

[tool.setuptools]
package-dir = {"" = "src"}

[tool.setuptools.packages.find]
where = ["src"]
""",
    "autogen": """[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "{{PROJECT_NAME}}"
version = "0.1.0"
description = "An AutoGen multi-agent AI application."
requires-python = ">=3.9"
dependencies = [
  "autogen-agentchat>=0.4",
  "{{PROVIDER_DEPENDENCY}}",
]

[tool.setuptools]
package-dir = {"" = "src"}

[tool.setuptools.packages.find]
where = ["src"]
""",
}

PROVIDER_ENV_VARS = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "google": "GOOGLE_API_KEY",
}

# Raw pip dependency needed to talk to each provider's SDK directly
# (used by the basic/langgraph/autogen agent wiring below).
PROVIDER_DEPENDENCIES = {
    "openai": "openai>=1.40",
    "anthropic": "anthropic>=0.34",
    "google": "google-genai>=0.3",
}

# A sensible default model per provider, so a freshly generated project
# can make a real call without the user having to look up a model id first.
PROVIDER_DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "anthropic": "claude-3-5-sonnet-20241022",
    "google": "gemini-1.5-flash",
}

CONFIG_TEMPLATE = """import os

MODEL_NAME = os.getenv("MODEL_NAME", "{{DEFAULT_MODEL}}")
{{PROVIDER_ENV_VAR}} = os.getenv("{{PROVIDER_ENV_VAR}}")


def validate() -> None:
    \"\"\"Fail fast if the required API key is missing.\"\"\"
    if not {{PROVIDER_ENV_VAR}}:
        raise RuntimeError(
            "Missing required environment variable '{{PROVIDER_ENV_VAR}}' for "
            "provider '{{PROVIDER}}'. Set it in your .env file."
        )
"""

# ---------------------------------------------------------------------------
# Building blocks for wiring a real LLM call into the "basic" / "langgraph" /
# "autogen" agent templates. The generator places PROVIDER_CLIENT_IMPORTS at
# the top of the file (with the other imports) and PROVIDER_CLIENT_INIT /
# PROVIDER_CALL_SNIPPETS inside the method body (8 spaces = class body +
# method body) - no imports ever live inline in the code.
# ---------------------------------------------------------------------------

PROVIDER_CLIENT_IMPORTS = {
    "openai": "from openai import OpenAI",
    "anthropic": "from anthropic import Anthropic",
    "google": "from google import genai",
}

PROVIDER_CLIENT_INIT = {
    "openai": "        client = OpenAI(api_key=config.OPENAI_API_KEY)\n",
    "anthropic": "        client = Anthropic(api_key=config.ANTHROPIC_API_KEY)\n",
    "google": "        client = genai.Client(api_key=config.GOOGLE_API_KEY)\n",
}

# Uses a locally-scoped `client` and `prompt`. {{AGENT_NAME}} is substituted
# by the generator before use.
PROVIDER_CALL_SNIPPETS = {
    "openai": (
        "        response = client.chat.completions.create(\n"
        "            model=config.MODEL_NAME,\n"
        "            messages=[\n"
        '                {"role": "system", "content": "You are the {{AGENT_NAME}} agent."},\n'
        '                {"role": "user", "content": prompt},\n'
        "            ],\n"
        "        )\n"
        "        return response.choices[0].message.content\n"
    ),
    "anthropic": (
        "        response = client.messages.create(\n"
        "            model=config.MODEL_NAME,\n"
        "            max_tokens=1024,\n"
        '            system="You are the {{AGENT_NAME}} agent.",\n'
        '            messages=[{"role": "user", "content": prompt}],\n'
        "        )\n"
        "        return response.content[0].text\n"
    ),
    "google": (
        "        response = client.models.generate_content(\n"
        "            model=config.MODEL_NAME,\n"
        '            contents=f"You are the {{AGENT_NAME}} agent.\\n\\n{prompt}",\n'
        "        )\n"
        "        return response.text\n"
    ),
}

# WebSearchTool is imported at the top of the file by the generator.
TOOL_SEARCH_SNIPPET = (
    "        results = WebSearchTool().search(task)\n"
    '        prompt = f"{task}\\n\\nRelevant search results:\\n{results}"\n'
)

NO_TOOL_SNIPPET = "        prompt = task\n"

# ---------------------------------------------------------------------------
# CrewAI / AutoGen wire the LLM through their own framework abstractions
# instead of a raw provider SDK call, so they only need a tool wrapper.
# The generator prepends the required imports (WebSearchTool, `tool`) itself.
# ---------------------------------------------------------------------------

CREWAI_TOOL_WRAPPER = '''@tool("Web Search")
def web_search_tool(query: str) -> str:
    """Search the web for the given query."""
    return WebSearchTool().search(query)
'''

AUTOGEN_TOOL_WRAPPER = '''def web_search(query: str) -> str:
    """Search the web for the given query."""
    return WebSearchTool().search(query)
'''

ORCHESTRATOR_TEMPLATES = {
    "basic": """from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class AgentExecutionError(RuntimeError):
    \"\"\"Raised when an agent fails during orchestration.\"\"\"


class Orchestrator:
    \"\"\"Simple sequential multi-agent orchestrator.\"\"\"

    def __init__(self, agents):
        self.agents = list(agents)

    def run(self, task: str) -> str:
        current = task

        for agent in self.agents:
            logger.info("Running agent: %s", agent.name)

            try:
                current = agent.run(current)
            except Exception as exc:
                logger.exception("Agent '%s' failed", agent.name)
                raise AgentExecutionError(f"Agent '{agent.name}' failed: {exc}") from exc

        return current
""",
    "crewai": """from __future__ import annotations

import logging

from crewai import Crew, Task

logger = logging.getLogger(__name__)


class AgentExecutionError(RuntimeError):
    \"\"\"Raised when an agent fails during orchestration.\"\"\"


class Orchestrator:
    \"\"\"CrewAI-based multi-agent orchestrator.\"\"\"

    def __init__(self, agents):
        self.agents = list(agents)

    def build_crew(self, task: str) -> Crew:
        \"\"\"Build a real CrewAI Crew for the given task.

        Once your agents have an LLM configured, use
        `orchestrator.build_crew(task).kickoff()` instead of `run()`.
        \"\"\"
        tasks = [
            Task(
                description=task,
                agent=agent.agent,
                expected_output="A completed response for the assigned step.",
            )
            for agent in self.agents
        ]

        return Crew(agents=[agent.agent for agent in self.agents], tasks=tasks)

    def run(self, task: str) -> str:
        current = task

        for agent in self.agents:
            logger.info("Running agent: %s", agent.name)

            try:
                current = agent.run(current)
            except Exception as exc:
                logger.exception("Agent '%s' failed", agent.name)
                raise AgentExecutionError(f"Agent '{agent.name}' failed: {exc}") from exc

        return current
""",
    "autogen": """from __future__ import annotations

import logging

from autogen_agentchat.teams import RoundRobinGroupChat

logger = logging.getLogger(__name__)


class AgentExecutionError(RuntimeError):
    \"\"\"Raised when an agent fails during orchestration.\"\"\"


class Orchestrator:
    \"\"\"AutoGen-based multi-agent orchestrator.\"\"\"

    def __init__(self, agents):
        self.agents = list(agents)

    def build_team(self, model_client) -> RoundRobinGroupChat:
        \"\"\"Build a real AutoGen team once you have a model client.

        Once your agents have an LLM configured, run the team with
        `await team.run(task=...)` instead of `run()`.
        \"\"\"
        participants = [agent.build(model_client) for agent in self.agents]

        return RoundRobinGroupChat(participants)

    def run(self, task: str) -> str:
        current = task

        for agent in self.agents:
            logger.info("Running agent: %s", agent.name)

            try:
                current = agent.run(current)
            except Exception as exc:
                logger.exception("Agent '%s' failed", agent.name)
                raise AgentExecutionError(f"Agent '{agent.name}' failed: {exc}") from exc

        return current
""",
}

# LangGraph is the one framework where "how agents are wired together" is a
# real architectural choice, so it gets its own orchestrator per style
# instead of a single fixed one.
LANGGRAPH_ORCHESTRATOR_TEMPLATES = {
    "sequential": """from __future__ import annotations

import logging

from langgraph.graph import END, START, StateGraph

logger = logging.getLogger(__name__)


class AgentExecutionError(RuntimeError):
    \"\"\"Raised when the LangGraph execution fails.\"\"\"


class Orchestrator:
    \"\"\"LangGraph-based sequential multi-agent orchestrator.

    Agents run one after another in a fixed pipeline: node_0 -> node_1 -> ...
    \"\"\"

    def __init__(self, agents):
        self.agents = list(agents)
        self.graph = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(dict)

        previous = START
        for index, agent in enumerate(self.agents):
            node_id = f"node_{index}"
            graph.add_node(node_id, agent)
            graph.add_edge(previous, node_id)
            previous = node_id

        graph.add_edge(previous, END)

        return graph.compile()

    def run(self, task: str) -> str:
        logger.info("Invoking LangGraph with %d node(s) (sequential)", len(self.agents))

        try:
            final_state = self.graph.invoke({"task": task, "result": ""})
        except Exception as exc:
            logger.exception("LangGraph execution failed")
            raise AgentExecutionError(f"LangGraph execution failed: {exc}") from exc

        return final_state["result"]
""",
    "dynamic": """from __future__ import annotations

import logging

from langgraph.graph import END, START, StateGraph

logger = logging.getLogger(__name__)


class AgentExecutionError(RuntimeError):
    \"\"\"Raised when the LangGraph execution fails.\"\"\"


class Orchestrator:
    \"\"\"LangGraph-based dynamic multi-agent orchestrator.

    Instead of a fixed pipeline, every agent routes back through a
    `supervisor` node that decides which agent runs next (or whether to
    finish) via `add_conditional_edges`. Customize `_route` below to make
    that decision from the task, the latest result, an LLM call, etc.
    \"\"\"

    def __init__(self, agents):
        self.agents = list(agents)
        self._node_ids = [f"node_{index}" for index in range(len(self.agents))]
        self.graph = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(dict)

        for node_id, agent in zip(self._node_ids, self.agents):
            graph.add_node(node_id, agent)
            graph.add_edge(node_id, "supervisor")

        graph.add_node("supervisor", self._supervisor)
        graph.add_edge(START, "supervisor")

        path_map = {node_id: node_id for node_id in self._node_ids}
        path_map["FINISH"] = END
        graph.add_conditional_edges("supervisor", self._route, path_map)

        return graph.compile()

    def _supervisor(self, state: dict) -> dict:
        \"\"\"Does no work itself - `_route` reads the state it returns to
        decide which agent runs next.\"\"\"
        return state

    def _route(self, state: dict) -> str:
        \"\"\"Pick the next agent node to run, or 'FINISH'.

        TODO: replace this with your real routing logic (e.g. inspect
        `state["result"]`, branch on task type, ask an LLM which agent
        should go next...). The default below just runs every agent once,
        in order, then finishes.
        \"\"\"
        completed = state.get("completed", 0)

        if completed < len(self._node_ids):
            return self._node_ids[completed]

        return "FINISH"

    def run(self, task: str) -> str:
        logger.info("Invoking LangGraph with %d agent(s) (dynamic routing)", len(self.agents))

        try:
            final_state = self.graph.invoke({"task": task, "result": "", "completed": 0})
        except Exception as exc:
            logger.exception("LangGraph execution failed")
            raise AgentExecutionError(f"LangGraph execution failed: {exc}") from exc

        return final_state["result"]
""",
}

TOOL_FILE = """class WebSearchTool:
    \"\"\"Placeholder for a web-search integration.\"\"\"

    def search(self, query: str) -> str:
        return f"Search provider placeholder: {query}"
"""

TEST_TEMPLATE = """import unittest

{{TEST_IMPORTS}}


class AgentTests(unittest.TestCase):
    def test_agents_have_expected_names(self):
{{ASSERTIONS}}


if __name__ == "__main__":
    unittest.main()
"""

DOCKER_FILE = """FROM python:3.12-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir .

CMD ["python", "-m", "{{PACKAGE_NAME}}"]
"""
