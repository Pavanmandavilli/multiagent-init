import tempfile
import unittest
from pathlib import Path
import os

from multiagent_init.generator import (
    agent_to_class,
    agent_to_module,
    generate_project,
)


class GeneratorTests(unittest.TestCase):
    def test_name_conversion(self):
        self.assertEqual(agent_to_module("Market Researcher"), "market_researcher")
        self.assertEqual(agent_to_class("Market Researcher"), "MarketResearcherAgent")
        self.assertEqual(agent_to_module("SQL Analyst"), "sql_analyst")
        self.assertEqual(agent_to_class("SQL Analyst"), "SqlAnalystAgent")

    def test_custom_agents_are_generated(self):
        with tempfile.TemporaryDirectory() as temp:
            old = Path.cwd()
            os.chdir(temp)

            try:
                config = {
                    "project_name": "demo",
                    "framework": "basic",
                    "provider": "openai",
                    "agent_count": 3,
                    "agent_mode": "custom",
                    "agent_names": [
                        "Market Researcher",
                        "Data Analyst",
                        "Report Writer",
                    ],
                    "include_tools": True,
                    "include_tests": True,
                    "include_docker": True,
                }

                destination = generate_project(config)
                package_dir = destination / "src" / "demo"

                self.assertTrue(
                    (package_dir / "agents" / "market_researcher.py").exists()
                )
                self.assertTrue(
                    (package_dir / "agents" / "data_analyst.py").exists()
                )
                self.assertTrue(
                    (package_dir / "agents" / "report_writer.py").exists()
                )

                main = (destination / "main.py").read_text(encoding="utf-8")

                self.assertIn("MarketResearcherAgent", main)
                self.assertIn("DataAnalystAgent", main)
                self.assertIn("ReportWriterAgent", main)

                self.assertTrue((package_dir / "config.py").exists())
                self.assertTrue((destination / "Dockerfile").exists())
                self.assertTrue((destination / "tests" / "test_agents.py").exists())
            finally:
                os.chdir(old)

    def test_refuses_non_empty_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            old = Path.cwd()
            os.chdir(temp)

            try:
                destination = Path(temp) / "existing"
                destination.mkdir()
                (destination / "important.txt").write_text("do not overwrite")

                config = {
                    "project_name": "existing",
                    "framework": "basic",
                    "provider": "openai",
                    "agent_count": 1,
                    "agent_mode": "custom",
                    "agent_names": ["Researcher"],
                    "include_tools": False,
                    "include_tests": False,
                    "include_docker": False,
                }

                with self.assertRaises(FileExistsError):
                    generate_project(config)
            finally:
                os.chdir(old)


if __name__ == "__main__":
    unittest.main()
