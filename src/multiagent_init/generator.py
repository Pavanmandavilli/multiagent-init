from __future__ import annotations

import re
from pathlib import Path

from .templates_data import (
    AUTOGEN_TOOL_WRAPPER,
    CONFIG_TEMPLATE,
    CREWAI_TOOL_WRAPPER,
    DOCKER_FILE,
    FRAMEWORK_FILES,
    LANGGRAPH_ORCHESTRATOR_TEMPLATES,
    NO_TOOL_SNIPPET,
    ORCHESTRATOR_TEMPLATES,
    PROVIDER_CLIENT_IMPORTS,
    PROVIDER_CLIENT_INIT,
    PROVIDER_CALL_SNIPPETS,
    PROVIDER_DEFAULT_MODELS,
    PROVIDER_DEPENDENCIES,
    PROVIDER_ENV_VARS,
    TEST_TEMPLATE,
    TOOL_FILE,
    TOOL_SEARCH_SNIPPET,
)

DEFAULT_AGENT_CLASSES = {
    "Researcher": "ResearcherAgent",
    "Writer": "WriterAgent",
    "Reviewer": "ReviewerAgent",
    "Planner": "PlannerAgent",
    "Executor": "ExecutorAgent",
}


def _safe_project_name(value: str) -> str:
    value = value.strip()

    if not value:
        raise ValueError("project name cannot be empty")

    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", value):
        raise ValueError("invalid project name")

    return value


def _safe_package_name(project_name: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_]", "_", project_name).lower()

    if value[0].isdigit():
        value = f"_{value}"

    return value


def agent_to_module(name: str) -> str:
    value = re.sub(r"[^A-Za-z0-9]+", "_", name.strip())
    value = re.sub(r"_+", "_", value).strip("_").lower()

    if not value:
        value = "agent"

    if value[0].isdigit():
        value = f"agent_{value}"

    return value


def agent_to_class(name: str) -> str:
    parts = re.findall(r"[A-Za-z0-9]+", name.strip())

    if not parts:
        return "Agent"

    class_name = "".join(part.capitalize() for part in parts)

    if class_name[0].isdigit():
        class_name = f"Agent{class_name}"

    return f"{class_name}Agent"


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _comment_block(block: str) -> str:
    """Prefix every non-blank line of an already-indented code block with '# '."""
    lines = block.rstrip("\n").split("\n")
    commented = []

    for line in lines:
        if not line.strip():
            commented.append("")
            continue

        stripped = line.lstrip(" ")
        indent = line[: len(line) - len(stripped)]
        commented.append(f"{indent}# {stripped}")

    return "\n".join(commented) + "\n"


def _wired_run_body(provider: str, agent_name: str, include_tools: bool) -> str:
    """The real LLM (+ optional tool) call for an agent's run(), 8-space indented.

    Assumes the provider client class and (if include_tools) WebSearchTool are
    already imported at the top of the file - no imports happen in here.
    """
    tool_snippet = TOOL_SEARCH_SNIPPET if include_tools else NO_TOOL_SNIPPET
    client_snippet = PROVIDER_CLIENT_INIT[provider]
    call_snippet = PROVIDER_CALL_SNIPPETS[provider].replace("{{AGENT_NAME}}", agent_name)

    return tool_snippet + client_snippet + call_snippet


def _llm_import_lines(
    package_name: str,
    provider: str,
    include_tools: bool,
    is_default: bool,
) -> list[str]:
    """Top-of-file imports for the LLM client (+ tool), live or commented out."""
    lines = [f"from {package_name} import config"]

    provider_import = PROVIDER_CLIENT_IMPORTS[provider]
    tool_import = f"from {package_name}.tools.web_search import WebSearchTool"

    if is_default:
        lines.append(provider_import)
        if include_tools:
            lines.append(tool_import)
    else:
        lines.append(f"# {provider_import}")
        if include_tools:
            lines.append(f"# {tool_import}")

    return lines


def _render_run_method_body(
    provider: str,
    agent_name: str,
    include_tools: bool,
    is_default: bool,
) -> str:
    wired_body = _wired_run_body(provider, agent_name, include_tools)

    if is_default:
        return wired_body

    note = (
        "        # TODO: connect this agent to your LLM/framework.\n"
        "        # Remove the '# ' below (and from the matching imports at the top\n"
        "        # of this file) to wire this agent to your configured provider"
        + (" and tools" if include_tools else "")
        + ".\n"
    )
    fallback = f'        return f"[{agent_name}] Completed: {{task}}"\n'

    return note + _comment_block(wired_body) + fallback


def _render_basic_agent(
    provider: str,
    package_name: str,
    agent_name: str,
    class_name: str,
    include_tools: bool,
    is_default: bool,
) -> str:
    run_body = _render_run_method_body(provider, agent_name, include_tools, is_default)
    imports = "\n".join(_llm_import_lines(package_name, provider, include_tools, is_default))

    return (
        f"{imports}\n"
        "\n"
        "\n"
        f"class {class_name}:\n"
        f'    """{agent_name} agent."""\n'
        "\n"
        f'    name = "{agent_name}"\n'
        "\n"
        "    def run(self, task: str) -> str:\n"
        f"{run_body}"
    )


def _render_langgraph_agent(
    provider: str,
    package_name: str,
    agent_name: str,
    class_name: str,
    include_tools: bool,
    is_default: bool,
) -> str:
    run_body = _render_run_method_body(provider, agent_name, include_tools, is_default)
    imports = "\n".join(_llm_import_lines(package_name, provider, include_tools, is_default))

    return (
        f"{imports}\n"
        "\n"
        "\n"
        f"class {class_name}:\n"
        f'    """{agent_name} node."""\n'
        "\n"
        f'    name = "{agent_name}"\n'
        "\n"
        "    def run(self, task: str) -> str:\n"
        f"{run_body}"
        "\n"
        "    def __call__(self, state: dict) -> dict:\n"
        '        """LangGraph node entry point - transforms and returns the graph state."""\n'
        '        state["result"] = self.run(state["task"])\n'
        '        state["task"] = state["result"]\n'
        '        state["completed"] = state.get("completed", 0) + 1\n'
        "        return state\n"
    )


def _render_crewai_agent(
    provider: str,
    package_name: str,
    agent_name: str,
    class_name: str,
    include_tools: bool,
    is_default: bool,
) -> str:
    llm_value = 'f"gemini/{config.MODEL_NAME}"' if provider == "google" else "config.MODEL_NAME"

    import_lines = [
        "from crewai import Agent, Crew, Task",
    ]

    if include_tools:
        import_lines.insert(1, "from crewai.tools import tool")

    import_lines += ["", f"from {package_name} import config"]

    if include_tools:
        import_lines.append(f"from {package_name}.tools.web_search import WebSearchTool")

    if is_default:
        init_extra = f"            llm={llm_value},\n"
        if include_tools:
            init_extra += "            tools=[web_search_tool],\n"
    else:
        comment_lines = [
            "            # Remove the '# ' below to wire this agent to an LLM"
            + (" and tools" if include_tools else "")
            + ".",
            f"            # llm={llm_value},",
        ]
        if include_tools:
            comment_lines.append("            # tools=[web_search_tool],")
        init_extra = "\n".join(comment_lines) + "\n"

    class_header = (
        f"class {class_name}:\n"
        f'    """{agent_name} agent."""\n'
        "\n"
        f'    name = "{agent_name}"\n'
        "\n"
        "    def __init__(self) -> None:\n"
        "        self.agent = Agent(\n"
        f'            role="{agent_name}",\n'
        f'            goal="Complete tasks assigned to the {agent_name} role.",\n'
        f'            backstory="An AI agent specialized in {agent_name} tasks.",\n'
        f"{init_extra}"
        "            allow_delegation=False,\n"
        "        )\n"
        "\n"
        "    def run(self, task: str) -> str:\n"
    )

    wired_run = (
        "        crew_task = Task(\n"
        "            description=task,\n"
        "            agent=self.agent,\n"
        '            expected_output="A completed response for the assigned step.",\n'
        "        )\n"
        "        return Crew(agents=[self.agent], tasks=[crew_task]).kickoff().raw\n"
    )

    if is_default:
        run_body = wired_run
    else:
        note = (
            "        # TODO: wrap `task` in a crewai.Task and execute it via a Crew.\n"
            "        # Remove the '# ' below to wire this agent's run() to a real Crew.\n"
        )
        fallback = f'        return f"[{agent_name}] Completed: {{task}}"\n'
        run_body = note + _comment_block(wired_run) + fallback

    parts = ["\n".join(import_lines)]

    if include_tools:
        parts.append(CREWAI_TOOL_WRAPPER)

    parts.append(class_header + run_body)

    return "\n\n".join(parts)


def _render_autogen_agent(
    provider: str,
    package_name: str,
    agent_name: str,
    class_name: str,
    include_tools: bool,
    is_default: bool,
) -> str:
    import_lines = ["from autogen_agentchat.agents import AssistantAgent", "", f"from {package_name} import config"]

    if include_tools:
        import_lines.append(f"from {package_name}.tools.web_search import WebSearchTool")

    provider_import = PROVIDER_CLIENT_IMPORTS[provider]
    import_lines.append(provider_import if is_default else f"# {provider_import}")

    if is_default:
        tools_extra = "            tools=[web_search],\n" if include_tools else ""
    else:
        tools_extra = "            # tools=[web_search],\n" if include_tools else ""

    build_method = (
        "    def build(self, model_client) -> AssistantAgent:\n"
        '        """Build a real AutoGen AssistantAgent once you have a model client."""\n'
        "        return AssistantAgent(\n"
        f'            name="{agent_name}",\n'
        "            model_client=model_client,\n"
        f'            system_message="You are the {agent_name} agent.",\n'
        f"{tools_extra}"
        "        )\n"
    )

    run_body = _render_run_method_body(provider, agent_name, include_tools, is_default)

    class_body = (
        f"class {class_name}:\n"
        f'    """{agent_name} agent."""\n'
        "\n"
        f'    name = "{agent_name}"\n'
        "\n"
        f"{build_method}"
        "\n"
        "    def run(self, task: str) -> str:\n"
        f"{run_body}"
    )

    parts = ["\n".join(import_lines)]

    if include_tools:
        parts.append(AUTOGEN_TOOL_WRAPPER)

    parts.append(class_body)

    return "\n\n".join(parts)


_AGENT_RENDERERS = {
    "basic": _render_basic_agent,
    "langgraph": _render_langgraph_agent,
    "crewai": _render_crewai_agent,
    "autogen": _render_autogen_agent,
}


def generate_project(config: dict) -> Path:
    project_name = _safe_project_name(config["project_name"])
    package_name = _safe_package_name(project_name)
    destination = Path.cwd() / project_name

    if destination.exists():
        if not destination.is_dir():
            raise FileExistsError(f"'{project_name}' already exists and is not a directory")

        if any(destination.iterdir()):
            raise FileExistsError(
                f"directory '{project_name}' already exists and is not empty"
            )
    else:
        destination.mkdir(parents=True)

    package_dir = destination / "src" / package_name

    provider = config["provider"]
    is_default = config["agent_mode"] == "default"

    framework_pyproject = FRAMEWORK_FILES[config["framework"]]
    framework_pyproject = framework_pyproject.replace("{{PROJECT_NAME}}", project_name)
    framework_pyproject = framework_pyproject.replace("{{PACKAGE_NAME}}", package_name)
    framework_pyproject = framework_pyproject.replace(
        "{{PROVIDER_DEPENDENCY}}", PROVIDER_DEPENDENCIES[provider]
    )

    _write(destination / "pyproject.toml", framework_pyproject)

    _write(
        destination / "README.md",
        _render_readme(config, package_name),
    )

    provider_env_var = PROVIDER_ENV_VARS[provider]
    default_model = PROVIDER_DEFAULT_MODELS[provider]

    _write(
        destination / ".env",
        f"MODEL_NAME={default_model}\n{provider_env_var}=\n",
    )

    _write(
        destination / ".gitignore",
        "__pycache__/\n*.py[cod]\n.venv/\n.env\n.pytest_cache/\n",
    )

    _write(package_dir / "__init__.py", '"""Generated package."""\n')

    config_content = CONFIG_TEMPLATE.replace("{{PROVIDER_ENV_VAR}}", provider_env_var)
    config_content = config_content.replace("{{PROVIDER}}", provider)
    config_content = config_content.replace("{{DEFAULT_MODEL}}", default_model)
    _write(package_dir / "config.py", config_content)

    render_agent = _AGENT_RENDERERS[config["framework"]]

    agent_files = []

    for agent_name in config["agent_names"]:
        module_name = agent_to_module(agent_name)
        class_name = agent_to_class(agent_name)

        agent_files.append(
            {
                "name": agent_name,
                "module": module_name,
                "class": class_name,
            }
        )

        content = render_agent(
            provider,
            package_name,
            agent_name,
            class_name,
            config["include_tools"],
            is_default,
        )

        _write(
            package_dir / "agents" / f"{module_name}.py",
            content,
        )

    _write(
        package_dir / "agents" / "__init__.py",
        '"""Generated agents."""\n',
    )

    imports = "\n".join(
        f"from {package_name}.agents.{item['module']} import {item['class']}"
        for item in agent_files
    )

    instances = ",\n        ".join(
        f"{item['class']}()"
        for item in agent_files
    )

    main_content = f"""from __future__ import annotations

import logging

{imports}

from {package_name} import config
from {package_name}.workflow.orchestrator import Orchestrator


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    config.validate()

    agents = [
        {instances}
    ]

    orchestrator = Orchestrator(agents)

    result = orchestrator.run(
        "Build a short report about multi-agent systems."
    )

    print("\\n=== Final result ===")
    print(result)


if __name__ == "__main__":
    main()
"""

    _write(destination / "main.py", main_content)

    _write(
        package_dir / "workflow" / "__init__.py",
        '"""Workflow and orchestration."""\n',
    )

    if config["framework"] == "langgraph":
        orchestrator_content = LANGGRAPH_ORCHESTRATOR_TEMPLATES[
            config.get("langgraph_orchestration", "sequential")
        ]
    else:
        orchestrator_content = ORCHESTRATOR_TEMPLATES[config["framework"]]

    _write(
        package_dir / "workflow" / "orchestrator.py",
        orchestrator_content,
    )

    if config["include_tools"]:
        _write(
            package_dir / "tools" / "__init__.py",
            '"""Tools available to agents."""\n',
        )
        _write(package_dir / "tools" / "web_search.py", TOOL_FILE)

    if config["include_tests"]:
        test_content = TEST_TEMPLATE.replace(
            "{{TEST_IMPORTS}}",
            "\n".join(
                f"from {package_name}.agents.{item['module']} import {item['class']}"
                for item in agent_files
            ),
        )

        assertions = "\n".join(
            f'        self.assertEqual({item["class"]}().name, "{item["name"]}")'
            for item in agent_files
        )

        test_content = test_content.replace("{{ASSERTIONS}}", assertions)

        _write(
            destination / "tests" / "test_agents.py",
            test_content,
        )

    if config["include_docker"]:
        docker_content = DOCKER_FILE.replace("{{PACKAGE_NAME}}", package_name)
        _write(destination / "Dockerfile", docker_content)

    print()
    print("Creating project...")
    print()
    print("✓ Agents")
    print("✓ Workflow")

    if config["include_tools"]:
        print("✓ Tools")

    print("✓ Configuration")

    if config["include_tests"]:
        print("✓ Tests")

    if config["include_docker"]:
        print("✓ Docker")

    print("✓ README")

    return destination


def _render_readme(config: dict, package_name: str) -> str:
    agents = "\n".join(
        f"- `{name}`"
        for name in config["agent_names"]
    )

    wiring_note = (
        "Every agent is pre-wired to call your configured model provider (and the "
        "web-search tool, if included) - just set your API key in `.env` and run."
        if config["agent_mode"] == "default"
        else (
            "Each agent ships with a ready-to-use LLM (and tool) call written out as "
            "a comment inside `run()`. Remove the leading `# ` on those lines (and "
            "the placeholder `return` below them) to wire it up."
        )
    )

    orchestration_line = ""
    if config["framework"] == "langgraph":
        mode = config.get("langgraph_orchestration", "sequential")
        orchestration_line = (
            f"- Orchestration: `{mode}`"
            + (
                " (fixed pipeline, agents run in order)"
                if mode == "sequential"
                else " (a supervisor node routes to the next agent at runtime)"
            )
            + "\n"
        )

    return f"""# {config["project_name"]}

Generated by **multiagent-init**.

## Configuration

- Framework: `{config["framework"]}`
- Model provider: `{config["provider"]}`
- Agent configuration: `{config["agent_mode"]}`
- Number of agents: `{config["agent_count"]}`
{orchestration_line}

## Agents

{agents}

## Structure

```text
src/{package_name}/
    agents/       Individual agents
    workflow/     Orchestration
    tools/        Optional tools
    config.py     Configuration
tests/            Optional tests
main.py           Entry point (python main.py)
```

## Run

```bash
pip install .
python main.py
```

Set your provider's API key in `.env` before running - `config.validate()` fails
fast with a clear error if it's missing.

{wiring_note}
"""
