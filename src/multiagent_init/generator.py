from __future__ import annotations

import re
from pathlib import Path

from .templates_data import (
    AGENT_TEMPLATES,
    CONFIG_TEMPLATE,
    DOCKER_FILE,
    FRAMEWORK_FILES,
    ORCHESTRATOR_TEMPLATES,
    PROVIDER_ENV_VARS,
    TEST_TEMPLATE,
    TOOL_FILE,
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

    class_name = "".join(part[:1].upper() + part[1:] for part in parts)

    if class_name[0].isdigit():
        class_name = f"Agent{class_name}"

    return f"{class_name}Agent"


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


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

    framework_pyproject = FRAMEWORK_FILES[config["framework"]]
    framework_pyproject = framework_pyproject.replace("{{PROJECT_NAME}}", project_name)
    framework_pyproject = framework_pyproject.replace("{{PACKAGE_NAME}}", package_name)

    _write(destination / "pyproject.toml", framework_pyproject)

    _write(
        destination / "README.md",
        _render_readme(config, package_name),
    )

    provider_env_var = PROVIDER_ENV_VARS[config["provider"]]

    _write(
        destination / ".env",
        f"MODEL_NAME=your-model\n{provider_env_var}=\n",
    )

    _write(
        destination / ".gitignore",
        "__pycache__/\n*.py[cod]\n.venv/\n.env\n.pytest_cache/\n",
    )

    _write(package_dir / "__init__.py", '"""Generated package."""\n')

    config_content = CONFIG_TEMPLATE.replace("{{PROVIDER_ENV_VAR}}", provider_env_var)
    config_content = config_content.replace("{{PROVIDER}}", config["provider"])
    _write(package_dir / "config.py", config_content)

    agent_template = AGENT_TEMPLATES.get(config["framework"], AGENT_TEMPLATES["basic"])
    orchestrator_template = ORCHESTRATOR_TEMPLATES.get(
        config["framework"], ORCHESTRATOR_TEMPLATES["basic"]
    )

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

        content = agent_template
        content = content.replace("{{AGENT_NAME}}", agent_name)
        content = content.replace("{{AGENT_CLASS}}", class_name)

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

    _write(
        package_dir / "workflow" / "orchestrator.py",
        orchestrator_template,
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
            f'        self.assertIn("{item["name"]}", {item["class"]}().run(task))'
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

    return f"""# {config["project_name"]}

Generated by **multiagent-init**.

## Configuration

- Framework: `{config["framework"]}`
- Model provider: `{config["provider"]}`
- Agent configuration: `{config["agent_mode"]}`
- Number of agents: `{config["agent_count"]}`

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

Replace the placeholder agent logic with your actual LLM/framework implementation.
"""
