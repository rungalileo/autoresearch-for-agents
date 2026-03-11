#!/usr/bin/env python3
"""
run_agent.py - Calls the support agent LLM (Claude Sonnet) with the system prompt,
policies, tool definitions, and a test case, then parses the tool call response.
"""

import asyncio
import json
import sys
from pathlib import Path

from dotenv import load_dotenv
import anthropic

BASE_DIR = Path(__file__).parent
ROOT_DIR = BASE_DIR.parent
load_dotenv(ROOT_DIR / ".env")


def _load_file(filename: str) -> str:
    """Load a text file from the autosupport directory."""
    return (BASE_DIR / filename).read_text(encoding="utf-8")


def _load_json(filename: str):
    """Load a JSON file from the autosupport directory."""
    with open(BASE_DIR / filename, encoding="utf-8") as f:
        return json.load(f)


MAX_SYSTEM_PROMPT_CHARS = 1000


def _build_system_prompt() -> str:
    """Combine system_prompt.md and policies.md into a single system prompt."""
    system_prompt = _load_file("system_prompt.md")
    char_count = len(system_prompt)
    if char_count >= MAX_SYSTEM_PROMPT_CHARS:
        excess = char_count - MAX_SYSTEM_PROMPT_CHARS + 1
        raise ValueError(
            f"system_prompt.md is {char_count} chars, must be under {MAX_SYSTEM_PROMPT_CHARS}. "
            f"Reduce by at least {excess} chars."
        )
    policies = _load_file("policies.md")
    return f"{system_prompt}\n\n---\n\n# Support Policies\n\n{policies}"


def _build_user_message(user_message: str, account_context: dict) -> str:
    """Format the user message and account context into a single user turn."""
    context_json = json.dumps(account_context, indent=2)
    return (
        f"<account_context>\n{context_json}\n</account_context>\n\n"
        f"<user_message>\n{user_message}\n</user_message>"
    )


def _load_tools():
    """Load tool definitions from tools_schema.json for the Claude API tools parameter."""
    return _load_json("tools_schema.json")


def _parse_tool_response(response):
    """
    Parse the Claude API response to extract all tool calls.
    Returns a list of dicts, each with "tool" and "args" keys.
    If no tool_use block is found, returns a single no_action call.
    """
    tool_calls = []
    for block in response.content:
        if block.type == "tool_use":
            tool_calls.append({"tool": block.name, "args": block.input})

    if not tool_calls:
        text_parts = [b.text for b in response.content if b.type == "text"]
        return [{
            "tool": "no_action",
            "args": {"message": " ".join(text_parts) if text_parts else "No tool called"},
        }]

    return tool_calls


async def run_test_case(user_message: str, account_context: dict):
    """
    Run a single test case through the support agent.

    Returns:
        List of dicts, each with "tool" and "args" keys.
    """
    try:
        client = anthropic.AsyncAnthropic()

        system_prompt = _build_system_prompt()
        tools = _load_tools()
        formatted_message = _build_user_message(user_message, account_context)

        response = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4000,
            temperature=0,
            system=system_prompt,
            tools=tools,
            messages=[
                {"role": "user", "content": formatted_message}
            ],
        )

        return _parse_tool_response(response)

    except Exception as e:
        return [{"tool": "error", "args": {"message": str(e)}}]


def _load_test_suite():
    """Load all test cases from tests/ directory."""
    tests_dir = ROOT_DIR / "tests"
    cases = []
    if not tests_dir.is_dir():
        print("Error: tests/ directory not found.", file=sys.stderr)
        sys.exit(1)
    for path in sorted(tests_dir.glob("*.json"), key=lambda p: int(p.stem)):
        with open(path, encoding="utf-8") as f:
            cases.append(json.load(f))
    return cases


async def _run_cli(test_case_id=None):
    """CLI mode: run a specific test case or all cases."""
    test_suite = _load_test_suite()

    if test_case_id:
        # Find the specific test case
        case = None
        for tc in test_suite:
            if tc["id"] == test_case_id:
                case = tc
                break
        if not case:
            print(f"Error: Test case '{test_case_id}' not found.", file=sys.stderr)
            sys.exit(1)
        cases = [case]
    else:
        cases = test_suite[:1]  # Default: run just the first case

    for case in cases:
        print(f"Running test case: {case['id']}")
        print(f"  Category: {case.get('category', 'unknown')}")
        print(f"  User message: {case['user_message'][:80]}...")

        actual_calls = await run_test_case(case["user_message"], case["account_context"])
        expected_calls = case["expected_tool_calls"]

        print(f"  Expected ({len(expected_calls)} calls):")
        for i, ec in enumerate(expected_calls):
            print(f"    [{i}] {ec['tool']}({json.dumps(ec.get('args', {}))})")
        print(f"  Actual ({len(actual_calls)} calls):")
        for i, ac in enumerate(actual_calls):
            print(f"    [{i}] {ac['tool']}({json.dumps(ac.get('args', {}))})")
        print()


if __name__ == "__main__":
    test_id = sys.argv[1] if len(sys.argv) > 1 else None
    asyncio.run(_run_cli(test_id))
