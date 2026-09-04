# 🚀 MultiAgent Init

[![PyPI version](https://img.shields.io/pypi/v/multiagent-init.svg)](https://pypi.org/project/multiagent-init/)
[![Python versions](https://img.shields.io/pypi/pyversions/multiagent-init.svg)](https://pypi.org/project/multiagent-init/)
[![Tests](https://github.com/Pavanmandavilli/multiagent-init/actions/workflows/test.yml/badge.svg)](https://github.com/Pavanmandavilli/multiagent-init/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Interactive CLI for generating a clean multi-agent AI project.

## Install

```bash
pip install multiagent-init
```

## Run

```bash
multiagent-init
```

## Wizard

The CLI asks for:

1. Project name
2. Framework
3. Model provider
4. Number of agents
5. Default or custom agents
6. Optional tools
7. Optional tests
8. Optional Docker

### Example

```text
🚀 MultiAgent Init

? Project name: research-team

? Select a framework:
❯ Basic
  LangGraph
  CrewAI
  AutoGen

? Select model provider:
❯ OpenAI
  Anthropic
  Google

? Number of agents:
❯ 3
  2
  4
  5
  Custom

? Agent configuration:
❯ Default agents
  Custom agents

? Agent 1 name: Market Researcher
? Agent 2 name: Data Analyst
? Agent 3 name: Report Writer

? Include tools? Yes
? Include tests? Yes
? Include Docker? No

Creating project...

✓ Agents
✓ Workflow
✓ Tools
✓ Configuration
✓ Tests
✓ README

🎉 Done!
```

## Generated project

Custom agent names are converted into safe Python filenames and class names.

Example:

```text
Market Researcher → market_researcher.py → MarketResearcherAgent
Data Analyst      → data_analyst.py      → DataAnalystAgent
Report Writer     → report_writer.py     → ReportWriterAgent
```

## Execution

```text
cd "project-name"
python3 -m venv .venv
source .venv/bin/activate
pip install .
python main.py
```

## License

MIT © [Pavan Sekhar Mandavilli](https://github.com/Pavanmandavilli)
