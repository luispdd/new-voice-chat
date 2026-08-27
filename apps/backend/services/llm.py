"""LLM service connecting to OpenAI-compatible APIs (LM Studio, Ollama, OpenRouter, OpenAI)."""

from typing import AsyncGenerator
from openai import AsyncOpenAI
from apps.backend.config import settings

_client: AsyncOpenAI | None = None

SYSTEM_PROMPT = """You are an intelligent, friendly, and helpful voice AI companion.
You communicate via a voice interface, so your responses must be optimized for natural speech synthesis:
- Speak directly, concisely, and naturally in conversational sentences.
- NEVER use emojis (e.g. 😊, 🚀, 👍) or ASCII emoticons (e.g. :), :-), xD, <3).
- NEVER use markdown formatting like asterisks (*, **), underscores (_), hashtags (#), backticks (`), bullet points, or markdown tables.
- NEVER output unreadable unicode characters, decorative symbols, or ASCII art.
- Avoid bulleted or numbered lists; express ideas naturally using spoken transitions.
- Avoid code blocks, URLs, and complex technical syntax unless explicitly requested by the user.
- Respond in plain, clear text that sounds natural when spoken aloud."""


def get_llm_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        print(f"🧠 Initializing LLM client ({settings.engine}) -> {settings.llm_base_url}")
        _client = AsyncOpenAI(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key or "not-needed",
        )
    return _client


async def stream_chat_completion(
    messages: list[dict[str, str]],
    system_prompt: str = SYSTEM_PROMPT,
    model: str | None = None,
) -> AsyncGenerator[str, None]:
    """
    Stream tokens from the LLM provider for the given conversation history.
    """
    client = get_llm_client()
    target_model = model or settings.llm_model

    formatted_messages = [{"role": "system", "content": system_prompt}]
    for msg in messages:
        formatted_messages.append({"role": msg["role"], "content": msg["text"]})

    try:
        response = await client.chat.completions.create(
            model=target_model,
            messages=formatted_messages,
            stream=True,
            temperature=0.7,
        )

        async for chunk in response:
            if chunk.choices and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                if delta.content:
                    yield delta.content

    except Exception as e:
        print(f"❌ Error communicating with LLM ({settings.engine}): {e}")
        yield f" [Error generating response: {str(e)}]"


async def generate_chat_completion(
    messages: list[dict[str, str]],
    system_prompt: str = SYSTEM_PROMPT,
    model: str | None = None,
) -> str:
    """
    Generate complete chat response non-streamed.
    """
    full_text = ""
    async for token in stream_chat_completion(messages, system_prompt, model):
        full_text += token
    return full_text.strip()
