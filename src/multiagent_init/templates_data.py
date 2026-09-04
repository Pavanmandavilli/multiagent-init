FRAMEWORK_FILES = {
    "basic": """[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "{{PROJECT_NAME}}"
version = "0.1.0"
description = "A multi-agent AI application."
requires-python = ">=3.9"
dependencies = []

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

CONFIG_TEMPLATE = """import os

MODEL_NAME = os.getenv("MODEL_NAME", "your-model")
{{PROVIDER_ENV_VAR}} = os.getenv("{{PROVIDER_ENV_VAR}}")


def validate() -> None:
    \"\"\"Fail fast if the required API key is missing.\"\"\"
    if not {{PROVIDER_ENV_VAR}}:
        raise RuntimeError(
            "Missing required environment variable '{{PROVIDER_ENV_VAR}}' for "
            "provider '{{PROVIDER}}'. Set it in your .env file."
        )
"""

AGENT_TEMPLATES = {
    "basic": """class {{AGENT_CLASS}}:
    \"\"\"{{AGENT_NAME}} agent.\"\"\"

    name = "{{AGENT_NAME}}"

    def run(self, task: str) -> str:
        # TODO: connect this agent to your LLM/framework.
        return f"[{{AGENT_NAME}}] Completed: {task}"
""",
    "langgraph": """class {{AGENT_CLASS}}:
    \"\"\"{{AGENT_NAME}} node.\"\"\"

    name = "{{AGENT_NAME}}"

    def run(self, task: str) -> str:
        # TODO: connect this node to your LLM/framework.
        return f"[{{AGENT_NAME}}] Completed: {task}"

    def __call__(self, state: dict) -> dict:
        \"\"\"LangGraph node entry point - transforms and returns the graph state.\"\"\"
        state["result"] = self.run(state["task"])
        state["task"] = state["result"]
        return state
""",
    "crewai": """from crewai import Agent


class {{AGENT_CLASS}}:
    \"\"\"{{AGENT_NAME}} agent.\"\"\"

    name = "{{AGENT_NAME}}"

    def __init__(self) -> None:
        self.agent = Agent(
            role="{{AGENT_NAME}}",
            goal="Complete tasks assigned to the {{AGENT_NAME}} role.",
            backstory="An AI agent specialized in {{AGENT_NAME}} tasks.",
            # TODO: configure an LLM, e.g. llm="gpt-4o-mini".
            allow_delegation=False,
        )

    def run(self, task: str) -> str:
        # TODO: wrap `task` in a crewai.Task and execute it via a Crew.
        return f"[{{AGENT_NAME}}] Completed: {task}"
""",
    "autogen": """from autogen_agentchat.agents import AssistantAgent


class {{AGENT_CLASS}}:
    \"\"\"{{AGENT_NAME}} agent.\"\"\"

    name = "{{AGENT_NAME}}"

    def build(self, model_client) -> AssistantAgent:
        \"\"\"Build a real AutoGen AssistantAgent once you have a model client.\"\"\"
        return AssistantAgent(
            name="{{AGENT_NAME}}",
            model_client=model_client,
            system_message="You are the {{AGENT_NAME}} agent.",
        )

    def run(self, task: str) -> str:
        # TODO: connect this agent to your LLM/framework.
        return f"[{{AGENT_NAME}}] Completed: {task}"
""",
}

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
    "langgraph": """from __future__ import annotations

import logging

from langgraph.graph import END, START, StateGraph

logger = logging.getLogger(__name__)


class AgentExecutionError(RuntimeError):
    \"\"\"Raised when the LangGraph execution fails.\"\"\"


class Orchestrator:
    \"\"\"LangGraph-based sequential multi-agent orchestrator.\"\"\"

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
        logger.info("Invoking LangGraph with %d node(s)", len(self.agents))

        try:
            final_state = self.graph.invoke({"task": task, "result": ""})
        except Exception as exc:
            logger.exception("LangGraph execution failed")
            raise AgentExecutionError(f"LangGraph execution failed: {exc}") from exc

        return final_state["result"]
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

TOOL_FILE = """class WebSearchTool:
    \"\"\"Placeholder for a web-search integration.\"\"\"

    def search(self, query: str) -> str:
        return f"Search provider placeholder: {query}"
"""

TEST_TEMPLATE = """import unittest

{{TEST_IMPORTS}}


class AgentTests(unittest.TestCase):
    def test_agents_return_output(self):
        task = "test task"
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
