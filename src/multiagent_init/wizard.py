from __future__ import annotations

import re

import questionary
from questionary import Style

NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
AGENT_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9 _-]*$")

STYLE = Style(
    [
        ("qmark", "fg:cyan bold"),
        ("question", "bold"),
        ("answer", "fg:cyan"),
        ("pointer", "fg:cyan bold"),
        ("highlighted", "fg:cyan bold"),
    ]
)


def _valid_project_name(value: str) -> bool:
    return bool(NAME_PATTERN.fullmatch(value.strip()))


def _valid_agent_name(value: str) -> bool:
    return bool(AGENT_PATTERN.fullmatch(value.strip()))


def _ask_agent_names(count: int) -> list[str]:
    names = []

    for index in range(1, count + 1):
        name = questionary.text(
            f"Agent {index} name:",
            validate=lambda value: (
                True
                if _valid_agent_name(value)
                else "Use letters, numbers, spaces, '-' or '_'."
            ),
            style=STYLE,
        ).ask()

        if name is None:
            raise KeyboardInterrupt

        names.append(name.strip())

    return names


def run_wizard() -> dict:
    print()
    print("🚀 MultiAgent Init")
    print()

    project_name = questionary.text(
        "Project name:",
        validate=lambda value: (
            True
            if _valid_project_name(value)
            else "Use letters, numbers, '-' or '_' and start with a letter/number."
        ),
        style=STYLE,
    ).ask()

    if project_name is None:
        raise KeyboardInterrupt

    framework = questionary.select(
        "Select a framework:",
        choices=[
            questionary.Choice("Basic", value="basic"),
            questionary.Choice("LangGraph", value="langgraph"),
            questionary.Choice("CrewAI", value="crewai"),
            questionary.Choice("AutoGen", value="autogen"),
        ],
        default="basic",
        style=STYLE,
    ).ask()

    provider = questionary.select(
        "Select model provider:",
        choices=[
            questionary.Choice("OpenAI", value="openai"),
            questionary.Choice("Anthropic", value="anthropic"),
            questionary.Choice("Google", value="google"),
        ],
        default="openai",
        style=STYLE,
    ).ask()

    agent_count_choice = questionary.select(
        "Number of agents:",
        choices=["3", "2", "4", "5", "Custom"],
        default="3",
        style=STYLE,
    ).ask()

    if agent_count_choice == "Custom":
        agent_count = questionary.text(
            "How many agents?",
            default="6",
            validate=lambda value: (
                True
                if value.isdigit() and 1 <= int(value) <= 50
                else "Enter a number between 1 and 50."
            ),
            style=STYLE,
        ).ask()

        if agent_count is None:
            raise KeyboardInterrupt

        agent_count = int(agent_count)
    else:
        agent_count = int(agent_count_choice)

    agent_mode = questionary.select(
        "Agent configuration:",
        choices=[
            questionary.Choice("Default agents", value="default"),
            questionary.Choice("Custom agents", value="custom"),
        ],
        default="default",
        style=STYLE,
    ).ask()

    default_names = [
        "Researcher",
        "Writer",
        "Reviewer",
        "Planner",
        "Executor",
    ]

    if agent_mode == "default":
        if agent_count <= len(default_names):
            agent_names = default_names[:agent_count]
        else:
            agent_names = default_names[:]
            for index in range(len(default_names) + 1, agent_count + 1):
                agent_names.append(f"Agent {index}")
    else:
        agent_names = _ask_agent_names(agent_count)

    include_tools = questionary.confirm(
        "Include tools?",
        default=True,
        style=STYLE,
    ).ask()

    include_tests = questionary.confirm(
        "Include tests?",
        default=True,
        style=STYLE,
    ).ask()

    include_docker = questionary.confirm(
        "Include Docker?",
        default=False,
        style=STYLE,
    ).ask()

    return {
        "project_name": project_name.strip(),
        "framework": framework,
        "provider": provider,
        "agent_count": agent_count,
        "agent_mode": agent_mode,
        "agent_names": agent_names,
        "include_tools": include_tools,
        "include_tests": include_tests,
        "include_docker": include_docker,
    }
