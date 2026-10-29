"""
Tool Streaming Example - FIXED
===============================

Real-time tool call streaming with automatic execution.

Setup:
    pip install flowgate[all]
    export OPENAI_API_KEY="sk-..."

Run:
    python examples/streaming_tools.py

What You'll See:
    - Tool calls being parsed as JSON arrives
    - Automatic tool execution
    - Results fed back to the model for final answer

Documentation:
    📖 Streaming Guide: docs/guides/streaming.md#tool-streaming
    📖 Quick Start: docs/guides/quickstart.md
    📚 Examples README: examples/README.md
"""

import asyncio
import os

from flowgate import CascadeAgent, ModelConfig
from flowgate.streaming import ToolStreamEventType

# ═══════════════════════════════════════════════════════════════════════════
# STEP 1: Define Tools in Universal Format
# ═══════════════════════════════════════════════════════════════════════════
# IMPORTANT: Use "universal format" (not OpenAI format)
# This works with ALL providers (OpenAI, Anthropic, Groq, etc.)
#
# Universal format structure:
# {
#     "name": "function_name",           ← Direct property
#     "description": "what it does",     ← Direct property
#     "parameters": {JSON Schema}        ← Direct property
# }
#
# ❌ WRONG (OpenAI format - don't use this):
# {
#     "type": "function",                ← Extra wrapper
#     "function": {
#         "name": "...",
#         ...
#     }
# }
#
# flowgate converts universal format → provider format automatically

WEATHER_TOOL = [
    {
        "name": "get_weather",
        "description": "Get current weather for a location",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "City name (e.g., 'Paris', 'Tokyo')"},
                "unit": {
                    "type": "string",
                    "enum": ["celsius", "fahrenheit"],
                    "description": "Temperature unit",
                },
            },
            "required": ["location"],  # location is required, unit is optional
        },
    }
]


# ═══════════════════════════════════════════════════════════════════════════
# STEP 2: Implement Tool Function (Not used in this example)
# ═══════════════════════════════════════════════════════════════════════════
# Note: This example shows tool call STREAMING only.
# For actual tool EXECUTION, see examples/tool_execution.py
#
# In production, you would:
# 1. Create ToolConfig objects with function=your_function
# 2. Use ToolExecutor to execute tool calls
# 3. Feed results back to the model
#
# This example focuses on the STREAMING aspect (watching tool calls form)


def get_weather(location: str, unit: str = "celsius") -> str:
    """
    Mock weather function - for reference only.
    Not used in this streaming example.
    """
    weather = {
        "paris": {"temp_c": 15, "condition": "Partly cloudy"},
        "tokyo": {"temp_c": 22, "condition": "Sunny"},
        "london": {"temp_c": 12, "condition": "Rainy"},
        "new york": {"temp_c": 18, "condition": "Clear"},
    }

    city = location.lower()
    if city in weather:
        data = weather[city]
        temp = data["temp_c"]
        if unit.lower() == "fahrenheit":
            temp = int(temp * 9 / 5 + 32)
            unit_symbol = "°F"
        else:
            unit_symbol = "°C"
        return f"{location}: {temp}{unit_symbol}, {data['condition']}"
    else:
        return f"Weather data not available for {location}"


async def main():
    # ═══════════════════════════════════════════════════════════════════════
    # STEP 3: Check API Key
    # ═══════════════════════════════════════════════════════════════════════

    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Set OPENAI_API_KEY first: export OPENAI_API_KEY='sk-...'")
        return

    print("🔧 flowgate Tool Streaming\n")

    # ═══════════════════════════════════════════════════════════════════════
    # STEP 4: Setup Agent with Cascade (REQUIRED for streaming)
    # ═══════════════════════════════════════════════════════════════════════
    # ✅ FIX: Need 2+ models for streaming to work!

    agent = CascadeAgent(
        models=[
            ModelConfig(name="gpt-4o-mini", provider="openai", cost=0.00015),
            ModelConfig(name="gpt-4o", provider="openai", cost=0.00625),
        ]
    )

    # Streaming is automatically available with 2+ models
    print("✓ Agent ready with 2-model cascade")
    print("✓ Streaming enabled (text and tools)\n")

    # ═══════════════════════════════════════════════════════════════════════
    # EXAMPLE 1: Single Tool Call (Streaming Events)
    # ═══════════════════════════════════════════════════════════════════════
    # Watch tool calls being parsed in real-time
    # Note: execute_tools parameter doesn't actually execute in this example
    # It just shows the streaming events

    print("=" * 60)
    print("Example 1: Tool call streaming events\n")
    print("Q: What's the weather in Paris?\n")

    # ✅ FIX: Use stream_events() not agent.tool_streaming_manager.stream()
    async for event in agent.stream_events("What's the weather in Paris?", tools=WEATHER_TOOL):
        # ───────────────────────────────────────────────────────────────────
        # EVENT: CHUNK - Regular text output (deprecated in tool mode)
        # ───────────────────────────────────────────────────────────────────
        # May appear as ToolStreamEventType.TEXT_CHUNK

        if event.type == ToolStreamEventType.TEXT_CHUNK:
            print(event.content, end="", flush=True)

        # ───────────────────────────────────────────────────────────────────
        # EVENT: TOOL_CALL_START - Tool call detected
        # ───────────────────────────────────────────────────────────────────

        elif event.type == ToolStreamEventType.TOOL_CALL_START:
            print("\n🔧 Tool call starting...")

        # ───────────────────────────────────────────────────────────────────
        # EVENT: TOOL_CALL_COMPLETE - Tool call fully parsed
        # ───────────────────────────────────────────────────────────────────

        elif event.type == ToolStreamEventType.TOOL_CALL_COMPLETE:
            tool = event.data.get("tool_call", {})
            print(f"🔧 Tool: {tool.get('name')}({tool.get('arguments')})")

        # ───────────────────────────────────────────────────────────────────
        # EVENT: COMPLETE - All done
        # ───────────────────────────────────────────────────────────────────

        elif event.type == ToolStreamEventType.COMPLETE:
            print("\n✅ Streaming complete")

    # ═══════════════════════════════════════════════════════════════════════
    # EXAMPLE 2: Multiple Tool Calls
    # ═══════════════════════════════════════════════════════════════════════

    print("\n" + "=" * 60)
    print("Example 2: Multiple tool calls\n")
    print("Q: Compare weather in Paris and Tokyo\n")

    async for event in agent.stream_events(
        "Compare the weather in Paris and Tokyo. Which is warmer?", tools=WEATHER_TOOL
    ):
        if event.type == ToolStreamEventType.TEXT_CHUNK:
            print(event.content, end="", flush=True)

        elif event.type == ToolStreamEventType.TOOL_CALL_START:
            print("\n🔧 Tool call starting...")

        elif event.type == ToolStreamEventType.TOOL_CALL_COMPLETE:
            tool = event.data.get("tool_call", {})
            print(f"🔧 Tool: {tool.get('name')}({tool.get('arguments')})")

        elif event.type == ToolStreamEventType.COMPLETE:
            print("\n✅ Streaming complete")

    # ═══════════════════════════════════════════════════════════════════════
    # Summary - What You Learned
    # ═══════════════════════════════════════════════════════════════════════

    print("\n" + "=" * 60)
    print("\n✅ Done! Key takeaways:")
    print("\n  Tool Definition (Universal Format):")
    print("  ├─ Use direct properties: name, description, parameters")
    print("  ├─ Works with ALL providers (OpenAI, Anthropic, Groq)")
    print("  └─ DON'T wrap in {'type': 'function', 'function': {...}}")
    print("\n  Streaming Requirements:")
    print("  ├─ Need 2+ models for cascade")
    print("  └─ Use agent.stream() or agent.stream_events() for streaming")
    print("\n  Tool Events:")
    print("  ├─ TOOL_CALL_START: Tool call detected")
    print("  ├─ TOOL_CALL_COMPLETE: Full JSON parsed")
    print("  └─ TEXT_CHUNK: Regular text between tools")
    print("\n  IMPORTANT:")
    print("  ├─ This example shows STREAMING only (watching tool calls form)")
    print("  ├─ For actual tool EXECUTION, see examples/tool_execution.py")
    print("  └─ Need ToolConfig + ToolExecutor for real execution")

    print("\n📚 Learn more:")
    print("  • docs/guides/streaming.md - Full streaming guide")
    print("  • examples/tool_execution.py - Real tool execution")
    print("  • tests/test_tool_calling.py - Comprehensive tool tests\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        print("\n💡 Tip: Make sure OPENAI_API_KEY is set correctly")
