import unittest

from multiagent_init.wizard import _valid_agent_name, _valid_project_name


class ValidationTests(unittest.TestCase):
    def test_project_names(self):
        self.assertTrue(_valid_project_name("my-agent"))
        self.assertTrue(_valid_project_name("agent_app"))
        self.assertFalse(_valid_project_name("-bad"))
        self.assertFalse(_valid_project_name("bad name"))

    def test_agent_names(self):
        self.assertTrue(_valid_agent_name("Market Researcher"))
        self.assertTrue(_valid_agent_name("SQL Analyst"))
        self.assertTrue(_valid_agent_name("report-writer"))
        self.assertFalse(_valid_agent_name(""))
        self.assertFalse(_valid_agent_name("bad/name"))


if __name__ == "__main__":
    unittest.main()
