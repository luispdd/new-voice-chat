"""Unit tests for configurable LLM history context limit and LLM settings endpoints."""

import unittest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from apps.backend.config import Settings, get_settings
from apps.backend.server import app

client = TestClient(app)


class TestLLMHistoryLimitConfig(unittest.TestCase):
    def test_default_history_limit_and_llm_defaults(self):
        cfg = get_settings([])
        self.assertEqual(cfg.llm_history_limit, 100)
        self.assertEqual(cfg.engine, "openai")
        self.assertEqual(cfg.llm_base_url, "http://127.0.0.1:8888/v1")
        self.assertEqual(cfg.llm_model, "unsloth/qwen3.5-4B-GGUF")
        self.assertFalse(cfg.cli_llm_override)

    def test_cli_overrides_defaults(self):
        cfg = get_settings(
            [
                "--engine",
                "ollama",
                "--base-url",
                "http://127.0.0.1:11434/v1",
                "--model",
                "llama3",
            ]
        )
        self.assertEqual(cfg.engine, "ollama")
        self.assertEqual(cfg.llm_base_url, "http://127.0.0.1:11434/v1")
        self.assertEqual(cfg.llm_model, "llama3")
        self.assertTrue(cfg.cli_llm_override)

    def test_custom_history_limit_in_settings(self):
        s = Settings(llm_history_limit=80)
        self.assertEqual(s.llm_history_limit, 80)

    @patch("apps.backend.server.check_llm_auth_status", new_callable=AsyncMock)
    @patch("apps.backend.server.save_llm_settings", new_callable=AsyncMock)
    def test_get_and_put_llm_settings_never_exposes_api_key(self, mock_save, mock_auth):
        mock_auth.return_value = {"auth_error": False, "auth_message": None}
        mock_save.return_value = {
            "_id": "llm_config",
            "engine": "openai",
            "base_url": "http://127.0.0.1:8888/v1",
            "model": "unsloth/qwen3.5-4B-GGUF",
            "api_key": "super-secret-key",
        }
        put_res = client.put(
            "/api/settings/llm",
            json={
                "engine": "openai",
                "base_url": "http://127.0.0.1:8888/v1",
                "model": "unsloth/qwen3.5-4B-GGUF",
                "api_key": "super-secret-key",
            },
        )
        self.assertEqual(put_res.status_code, 200)
        put_data = put_res.json()
        self.assertNotIn("api_key", put_data)
        self.assertTrue(put_data["has_api_key"])
        self.assertEqual(put_data["model"], "unsloth/qwen3.5-4B-GGUF")

        get_res = client.get("/api/settings/llm")
        self.assertEqual(get_res.status_code, 200)
        get_data = get_res.json()
        self.assertNotIn("api_key", get_data)
        self.assertTrue(get_data["has_api_key"])


if __name__ == "__main__":
    unittest.main()
