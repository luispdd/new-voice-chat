"""Unit tests for LLM exception diagnostics across all providers."""

import unittest
import httpx
from openai import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    NotFoundError,
    RateLimitError,
    PermissionDeniedError,
    BadRequestError,
    InternalServerError,
    APIStatusError,
)
from apps.backend.services.llm import format_llm_exception


class TestLLMExceptionFormatting(unittest.TestCase):
    def test_lmstudio_connection_error(self):
        dummy_req = httpx.Request("POST", "http://127.0.0.1:1234/v1/chat/completions")
        err = APIConnectionError(request=dummy_req)
        formatted = format_llm_exception(
            err,
            engine="lmstudio",
            base_url="http://127.0.0.1:1234/v1",
            model="google/gemma-3-4b-it-qat",
        )
        self.assertEqual(formatted, "[Error: Unable to connect to LM Studio]")

    def test_ollama_connection_error(self):
        dummy_req = httpx.Request("POST", "http://127.0.0.1:11434/v1/chat/completions")
        err = APIConnectionError(request=dummy_req)
        formatted = format_llm_exception(
            err,
            engine="ollama",
            base_url="http://127.0.0.1:11434/v1",
            model="llama3",
        )
        self.assertEqual(formatted, "[Error: Unable to connect to Ollama]")

    def test_openai_connection_error(self):
        dummy_req = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
        err = APIConnectionError(request=dummy_req)
        formatted = format_llm_exception(
            err,
            engine="openai",
            base_url="https://api.openai.com/v1",
            model="gpt-4o-mini",
        )
        self.assertEqual(formatted, "[Error: Unable to connect to OpenAI]")

    def test_openrouter_connection_error(self):
        dummy_req = httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")
        err = APIConnectionError(request=dummy_req)
        formatted = format_llm_exception(
            err,
            engine="openrouter",
            base_url="https://openrouter.ai/api/v1",
            model="meta-llama/llama-3.3-70b-instruct",
        )
        self.assertEqual(formatted, "[Error: Unable to connect to OpenRouter]")

    def test_authentication_error(self):
        dummy_response = httpx.Response(
            status_code=401,
            request=httpx.Request("POST", "https://api.openai.com/v1/chat/completions"),
        )
        err = AuthenticationError("Invalid API key", response=dummy_response, body={"error": "invalid_api_key"})
        formatted = format_llm_exception(
            err,
            engine="openai",
            base_url="https://api.openai.com/v1",
            model="gpt-4o-mini",
        )
        self.assertEqual(formatted, "[Error: Authentication failed for OpenAI]")

    def test_not_found_error(self):
        dummy_response = httpx.Response(
            status_code=404,
            request=httpx.Request("POST", "http://127.0.0.1:1234/v1/chat/completions"),
        )
        err = NotFoundError("Model not loaded", response=dummy_response, body={"error": "model_not_found"})
        formatted = format_llm_exception(
            err,
            engine="lmstudio",
            base_url="http://127.0.0.1:1234/v1",
            model="custom-model-x",
        )
        self.assertEqual(formatted, "[Error: Model not found on LM Studio]")

    def test_rate_limit_error(self):
        dummy_response = httpx.Response(
            status_code=429,
            request=httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions"),
        )
        err = RateLimitError("Quota exceeded", response=dummy_response, body={"error": "rate_limit"})
        formatted = format_llm_exception(
            err,
            engine="openrouter",
            base_url="https://openrouter.ai/api/v1",
            model="meta-llama/llama-3.3-70b-instruct",
        )
        self.assertEqual(formatted, "[Error: Rate limit or quota exceeded for OpenRouter]")

    def test_timeout_error(self):
        dummy_req = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
        err = APITimeoutError(request=dummy_req)
        formatted = format_llm_exception(
            err,
            engine="openai",
            base_url="https://api.openai.com/v1",
            model="gpt-4o-mini",
        )
        self.assertEqual(formatted, "[Error: Connection timed out for OpenAI]")

    def test_permission_denied_error(self):
        dummy_response = httpx.Response(
            status_code=403,
            request=httpx.Request("POST", "https://api.openai.com/v1/chat/completions"),
        )
        err = PermissionDeniedError("Forbidden", response=dummy_response, body=None)
        formatted = format_llm_exception(
            err,
            engine="openai",
            base_url="https://api.openai.com/v1",
            model="gpt-4o-mini",
        )
        self.assertEqual(formatted, "[Error: Access denied for OpenAI]")

    def test_internal_server_error(self):
        dummy_response = httpx.Response(
            status_code=500,
            request=httpx.Request("POST", "https://api.openai.com/v1/chat/completions"),
        )
        err = InternalServerError("Internal server error", response=dummy_response, body=None)
        formatted = format_llm_exception(
            err,
            engine="openai",
            base_url="https://api.openai.com/v1",
            model="gpt-4o-mini",
        )
        self.assertEqual(formatted, "[Error: Server error from OpenAI]")


if __name__ == "__main__":
    unittest.main()
