"""VULKRAN OS — Claude API bridge with tool-use support."""

import json
import logging

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"


async def call_claude(
    messages: list[dict],
    system: str | None = None,
    tools: list[dict] | None = None,
    model: str | None = None,
    max_tokens: int | None = None,
) -> dict:
    """Send a request to Claude API and return the raw response."""
    model = model or settings.default_model
    max_tokens = max_tokens or settings.max_tokens

    headers = {
        "x-api-key": settings.anthropic_api_key,
        "anthropic-version": API_VERSION,
        "content-type": "application/json",
    }

    payload: dict = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": messages,
    }
    if system:
        payload["system"] = system
    if tools:
        payload["tools"] = tools

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(API_URL, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()


def extract_text(response: dict) -> str:
    """Extract text content from Claude response."""
    for block in response.get("content", []):
        if block.get("type") == "text":
            return block["text"]
    return ""


def extract_tool_calls(response: dict) -> list[dict]:
    """Extract tool_use blocks from Claude response."""
    calls = []
    for block in response.get("content", []):
        if block.get("type") == "tool_use":
            calls.append({
                "id": block["id"],
                "name": block["name"],
                "input": block["input"],
            })
    return calls


def build_tool_result(tool_use_id: str, result: str | dict) -> dict:
    """Build a tool_result message block."""
    content = result if isinstance(result, str) else json.dumps(result)
    return {
        "type": "tool_result",
        "tool_use_id": tool_use_id,
        "content": content,
    }


async def chat_with_tools(
    messages: list[dict],
    system: str,
    tools: list[dict],
    tool_executor: callable,
    max_rounds: int = 10,
    model: str | None = None,
) -> tuple[str, list[dict]]:
    """Run a multi-turn tool-use loop until Claude gives a final text answer.

    Returns (final_text, all_tool_calls_made).
    """
    all_tool_calls = []
    working_messages = list(messages)

    for _ in range(max_rounds):
        response = await call_claude(
            messages=working_messages,
            system=system,
            tools=tools,
            model=model,
        )

        stop_reason = response.get("stop_reason")
        tool_calls = extract_tool_calls(response)

        if not tool_calls or stop_reason == "end_turn":
            return extract_text(response), all_tool_calls

        # Execute tools and build results
        all_tool_calls.extend(tool_calls)
        tool_results = []
        for call in tool_calls:
            logger.info("Tool call: %s(%s)", call["name"], call["input"])
            result = await tool_executor(call["name"], call["input"])
            tool_results.append(build_tool_result(call["id"], result))

        # Add assistant response + tool results to conversation
        working_messages.append({"role": "assistant", "content": response["content"]})
        working_messages.append({"role": "user", "content": tool_results})

    return extract_text(response), all_tool_calls
