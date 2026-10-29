"""
Text Streaming Example
======================

Real-time text streaming with cascade events.

Setup:
    pip install flowgate[all]
    export OPENAI_API_KEY="sk-..."

Run:
    python examples/streaming_text.py

What You'll See:
    - Tokens appearing in real-time (like ChatGPT)
    - Draft decisions (accepted = cheap, rejected = expensive)
    - Cost and speed metrics after each response

Documentation:
    📖 Streaming Guide: docs/guides/streaming.md#tool-streaming
    📖 Quick Start: docs/guides/quickstart.md
    📚 Examples README: examples/README.md
"""

import asyncio
import os

from flowgate import CascadeAgent, ModelConfig
from flowgate.streaming import StreamEventType


async def main():
    # ═══════════════════════════════════════════════════════════════════════
    # STEP 1: Check API Key
    # ═══════════════════════════════════════════════════════════════════════
    # Verify the OpenAI API key is set before we start

    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Set OPENAI_API_KEY first: export OPENAI_API_KEY='sk-...'")
        return

    print("🌊 flowgate Text Streaming\n")

    # ═══════════════════════════════════════════════════════════════════════
    # STEP 2: Setup Agent with Cascade
    # ═══════════════════════════════════════════════════════════════════════
    # Create agent with 2 models:
    # - Tier 1 (gpt-4o-mini): Fast & cheap, tries first
    # - Tier 2 (gpt-4o): Slower & expensive, only if needed
    #
    # This is called "cascading" - start cheap, escalate if needed

    agent = CascadeAgent(
        models=[
            ModelConfig(
                name="gpt-4o-mini", provider="openai", cost=0.00015  # ~$0.15 per 1M tokens
            ),
            ModelConfig(
                name="gpt-4o", provider="openai", cost=0.00625  # ~$6.25 per 1M tokens (40x more!)
            ),
        ]
    )

    # ═══════════════════════════════════════════════════════════════════════
    # STEP 3: Agent Ready
    # ═══════════════════════════════════════════════════════════════════════
    # The agent is configured with 2 models for cascading
    # Streaming is automatically available

    print("✓ Agent ready with 2-tier cascade")
    print("✓ Streaming enabled\n")

    # ═══════════════════════════════════════════════════════════════════════
    # EXAMPLE 1: Simple Query (Usually Stays on Tier 1)
    # ═══════════════════════════════════════════════════════════════════════
    # Simple questions usually get accepted by the cheap model
    # You'll see: draft accepted = verifier skipped = money saved!

    print("=" * 60)
    print("Example 1: Simple question (fast & cheap)\n")
    print("Q: What is Python?\nA: ", end="", flush=True)

    # Stream the response with real-time events
    async for event in agent.stream("What is Python? Answer in one sentence.", max_tokens=100):
        # ───────────────────────────────────────────────────────────────────
        # EVENT: CHUNK - New text token arrived
        # ───────────────────────────────────────────────────────────────────
        # This is fired for each piece of text (could be a word or character)
        # Print it immediately for real-time streaming effect

        if event.type == StreamEventType.CHUNK:
            print(event.content, end="", flush=True)

        # ───────────────────────────────────────────────────────────────────
        # EVENT: DRAFT_DECISION - Quality check complete
        # ───────────────────────────────────────────────────────────────────
        # After the draft finishes, flowgate checks quality:
        # - Accepted = Good enough! Skip expensive model (save money)
        # - Rejected = Not good enough, need better model (ensure quality)

        elif event.type == StreamEventType.DRAFT_DECISION:
            if event.data["accepted"]:
                # Draft passed quality check - we're done!
                confidence = event.data["confidence"]
                print(f"\n✓ Draft accepted ({confidence:.0%} confidence)")
                print("  → Verifier skipped (saved money!)")
            else:
                # Draft failed quality check - escalating to better model
                print("\n✗ Draft quality insufficient")
                print("  → Cascading to better model...")

        # ───────────────────────────────────────────────────────────────────
        # EVENT: COMPLETE - Stream finished
        # ───────────────────────────────────────────────────────────────────
        # All done! Show final statistics (cost, speed, model used)

        elif event.type == StreamEventType.COMPLETE:
            result = event.data["result"]
            print(f"💰 Cost: ${result['total_cost']:.6f}")
            print(f"⚡ Speed: {result['latency_ms']:.0f}ms")
            print(f"🎯 Model: {result['model_used']}")

    # ═══════════════════════════════════════════════════════════════════════
    # EXAMPLE 2: Complex Query (Usually Cascades to Tier 2)
    # ═══════════════════════════════════════════════════════════════════════
    # Complex questions often need the better model
    # You'll see: draft rejected → switch to verifier → better quality

    print("\n" + "=" * 60)
    print("Example 2: Complex question (may cascade)\n")
    print("Q: Explain quantum computing and its implications.\nA: ", end="", flush=True)

    # Stream with the same event handling
    async for event in agent.stream(
        "Explain quantum computing and its implications for cryptography.", max_tokens=200
    ):
        # ───────────────────────────────────────────────────────────────────
        # CHUNK Event - Print tokens in real-time
        # ───────────────────────────────────────────────────────────────────

        if event.type == StreamEventType.CHUNK:
            print(event.content, end="", flush=True)

        # ───────────────────────────────────────────────────────────────────
        # DRAFT_DECISION Event - Check if cascading happens
        # ───────────────────────────────────────────────────────────────────
        # For complex queries, you'll often see the draft get rejected
        # This means BOTH models run (costs more but ensures quality)

        elif event.type == StreamEventType.DRAFT_DECISION:
            if event.data["accepted"]:
                confidence = event.data["confidence"]
                print(f"\n✓ Draft accepted ({confidence:.0%})")
            else:
                # Draft rejected - now we'll see the SWITCH event next
                confidence = event.data["confidence"]
                reason = event.data.get("reason", "quality_insufficient")
                print(f"\n✗ Draft rejected ({confidence:.0%}): {reason}")

        # ───────────────────────────────────────────────────────────────────
        # SWITCH Event - Cascading to better model
        # ───────────────────────────────────────────────────────────────────
        # This only fires when draft is rejected
        # Shows which models are being used (tier 1 → tier 2)

        elif event.type == StreamEventType.SWITCH:
            from_model = event.data.get("from_model", "tier-1")
            to_model = event.data.get("to_model", "tier-2")
            print(f"⤴️  Cascading: {from_model} → {to_model}")
            print("A: ", end="", flush=True)  # Start new answer line

        # ───────────────────────────────────────────────────────────────────
        # COMPLETE Event - Show final stats
        # ───────────────────────────────────────────────────────────────────

        elif event.type == StreamEventType.COMPLETE:
            result = event.data["result"]
            print(f"\n💰 Cost: ${result['total_cost']:.6f}")
            print(f"⚡ Speed: {result['latency_ms']:.0f}ms")
            print(f"🎯 Model: {result['model_used']}")

    # ═══════════════════════════════════════════════════════════════════════
    # Summary - What You Learned
    # ═══════════════════════════════════════════════════════════════════════

    print("\n" + "=" * 60)
    print("\n✅ Done! Key takeaways:")
    print("\n  How Cascading Works:")
    print("  ├─ Simple queries → Draft accepted → Cheap & fast")
    print("  └─ Complex queries → Draft rejected → Expensive but quality")
    print("\n  Event Flow:")
    print("  ├─ CHUNK: New text arrives (print immediately)")
    print("  ├─ DRAFT_DECISION: Quality check (accepted or rejected)")
    print("  ├─ SWITCH: Cascading to better model (if rejected)")
    print("  └─ COMPLETE: All done (show stats)")
    print("\n  Cost Optimization:")
    print("  ├─ Accepted drafts: ~40x cheaper (gpt-4o-mini only)")
    print("  └─ Rejected drafts: Both models used (ensures quality)")

    print("\n📚 Learn more: docs/guides/streaming.md\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        print("💡 Tip: Make sure OPENAI_API_KEY is set correctly")
