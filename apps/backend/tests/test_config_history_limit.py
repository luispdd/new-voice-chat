"""Unit tests for configurable LLM history context limit."""

import os
import unittest
from apps.backend.config import Settings, get_settings


class TestLLMHistoryLimitConfig(unittest.TestCase):
    def test_default_history_limit(self):
        settings = Settings()
        self.assertEqual(settings.llm_history_limit, 50)

    def test_custom_history_limit_in_settings(self):
        settings = Settings(llm_history_limit=80)
        self.assertEqual(settings.llm_history_limit, 80)


if __name__ == "__main__":
    unittest.main()
