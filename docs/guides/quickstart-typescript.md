# flowgate Quick Start Guide (TypeScript)

Get started with flowgate in TypeScript/JavaScript in 5 minutes. This guide walks you through the basics of intelligent model cascading.

---

## 📚 Table of Contents

- [What is flowgate?](#what-is-flowgate)
- [Installation](#installation)
- [Your First Cascade](#your-first-cascade)
- [How It Works](#how-it-works)
- [Understanding Costs](#understanding-costs)
- [Configuration Options](#configuration-options)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)
- [Next Steps](#next-steps)

---

## What is flowgate?

**flowgate** is an intelligent model router that saves you 40-60% on AI costs by automatically using cheaper models when possible and only escalating to expensive models when needed.

### The Problem

Using GPT-4o for everything is expensive:
```
10,000 queries/month × $0.005/query = $50/month
```

But using GPT-4o-mini for everything sacrifices quality.

### The Solution

flowgate tries the cheap model first, checks quality, and only uses the expensive model if needed:

```
Simple query → GPT-4o-mini ✅ (draft accepted) → Cost: $0.0004
Complex query → GPT-4o-mini ❌ (draft rejected) → GPT-4o ✅ → Cost: $0.006
```

**Result:** 40-60% savings while maintaining quality!

---

## Installation

### Step 1: Install flowgate

```bash
npm install @flowgate/core
```

### Step 2: Install Provider SDKs

Install the SDK for your chosen provider:

```bash
# OpenAI (most common)
npm install openai

# Anthropic
npm install @anthropic-ai/sdk

# Groq
npm install groq-sdk
```

### Step 3: Set Up API Key

```bash
# OpenAI
export OPENAI_API_KEY="sk-..."

# Or add to your .env file
echo "OPENAI_API_KEY=sk-..." >> .env
```

### Step 4: Verify Installation

```bash
node -e "import('@flowgate/core').then(m => console.log('✅ Installed'))"
```

---

## Your First Cascade

Create a file called `my-first-cascade.ts`:

```typescript
import { CascadeAgent, ModelConfig } from '@flowgate/core';

async function main() {
  // Configure cascade with two tiers
  const agent = new CascadeAgent({
    models: [
      // Tier 1: Cheap model (tries first)
      {
        name: 'gpt-4o-mini',
        provider: 'openai',
        cost: 0.000375,  // $0.375 per 1M tokens (blended)
      },

      // Tier 2: Expensive model (only if needed)
      {
        name: 'gpt-4o',
        provider: 'openai',
        cost: 0.00625,  // $6.25 per 1M tokens (blended)
      },
    ],
  });
  // Quality validation uses default cascade-optimized config (0.7 threshold)
  // See "Configuration Options" section below to customize

  // Try a simple query
  const result = await agent.run('What color is the sky?');

  console.log(`Response: ${result.content}`);
  console.log(`Model used: ${result.modelUsed}`);
  console.log(`Cost: $${result.totalCost.toFixed(6)}`);
  console.log(`Draft accepted: ${result.draftAccepted}`);
}

main().catch(console.error);
```

Run it:
```bash
npx tsx my-first-cascade.ts
```

Expected output:
```
Response: The sky is typically blue during the day.
Model used: gpt-4o-mini
Cost: $0.000081
Draft accepted: true
```

**What happened?**
1. Query sent to GPT-4o-mini (cheap)
2. Response passed quality check
3. GPT-4o was NOT called (saved money!)

---

## How It Works

### The Cascade Process

```
┌─────────────────┐
│  Your Query     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Complexity     │ ─────► Simple/Moderate/Complex
│  Detection      │
└────────┬────────┘
         │
         ▼
   ┌─────────────┐
   │ Direct to   │ ───► Very simple → GPT-4o-mini only
   │ GPT-4o-mini?│ ───► Very complex → GPT-4o directly
   └──────┬──────┘
          │ Maybe cascade
          ▼
┌─────────────────┐
│ GPT-4o-mini     │ ────► Generate response
│ Draft           │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Quality Check   │ ────► Confidence > threshold?
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
  PASS      FAIL
    │         │
    │    ┌────────────────┐
    │    │  GPT-4o Verify │
    │    └────────┬───────┘
    │             │
    └─────────────┘
         │
         ▼
   ┌──────────────┐
   │  Final       │
   │  Response    │
   └──────────────┘
```

### Key Concepts

#### 1. Draft Model
- **Purpose:** Try to answer with cheap model
- **Cost:** Low (~$0.000375 per 1K tokens)
- **Speed:** Fast
- **Quality:** Good for simple queries

#### 2. Verifier Model
- **Purpose:** Verify draft or handle complex queries
- **Cost:** Higher (~$0.00625 per 1K tokens)
- **Speed:** Slower
- **Quality:** Best quality

#### 3. Quality Check
- **Checks:** Confidence score, alignment, coherence
- **Threshold:** Configurable (default: 0.7)
- **Result:** Pass → use draft, Fail → use verifier

#### 4. Draft Accepted vs Rejected

**Draft Accepted** ✅
- Cheap model response is good enough
- Verifier is NOT called
- Cost = cheap model only
- **This is where you save money!**

**Draft Rejected** ❌
- Cheap model response not good enough
- BOTH models are called
- Cost = cheap + expensive
- Quality is ensured

---

## Understanding Costs

### Token-Based Pricing

flowgate uses **actual token-based pricing**, not flat rates:

```typescript
// Your query
const query = "What is TypeScript?";  // ~4 tokens

// Model's response
const response = "TypeScript is a programming language...";  // ~50 tokens

// Total tokens
const total = 4 (input) + 50 (output) = 54 tokens

// Cost calculation (GPT-4o-mini example)
const inputCost  = (4 / 1000) × $0.00015 = $0.0000006
const outputCost = (50 / 1000) × $0.0006 = $0.000030
const totalCost  = $0.0000306
```

### Cost Breakdown by Scenario

#### Scenario 1: Draft Accepted (Best Case)
```
Query → GPT-4o-mini ✅ (accepted)

Costs:
  GPT-4o-mini: $0.000031
  GPT-4o:      $0.000000 (not called)
  ─────────────────
  Total:       $0.000031

Savings: ~95% vs GPT-4o only
```

#### Scenario 2: Draft Rejected (Worst Case)
```
Query → GPT-4o-mini ❌ (rejected) → GPT-4o ✅

Costs:
  GPT-4o-mini: $0.000031
  GPT-4o:      $0.000650
  ─────────────────
  Total:       $0.000681

Savings: -5% vs GPT-4o only (paid extra for GPT-4o-mini)
```

#### Scenario 3: Direct Routing
```
Query → GPT-4o directly (complex query)

Costs:
  GPT-4o-mini: $0.000000 (not called)
  GPT-4o:      $0.000650
  ─────────────────
  Total:       $0.000650

Savings: 0% (same as GPT-4o only)
```

### Expected Savings

Your savings depend on your query mix:

| Query Mix | Draft Acceptance Rate | Expected Savings |
|-----------|----------------------|------------------|
| 80% simple, 20% complex | 80% | 60-70% |
| 50% simple, 50% complex | 50% | 40-50% |
| 20% simple, 80% complex | 20% | 10-20% |

**Rule of thumb:** The more simple queries, the more you save!

---

## Configuration Options

### Model Configuration

```typescript
import { ModelConfig } from '@flowgate/core';

const modelConfig: ModelConfig = {
  name: 'gpt-4o-mini',               // Model name
  provider: 'openai',                // Provider (openai, anthropic, groq, ollama)
  cost: 0.000375,                    // Cost per 1K tokens (blended estimate)
  apiKey: process.env.OPENAI_API_KEY // Optional: override default API key
};
```

### Agent Configuration

```typescript
const agent = new CascadeAgent({
  models: [tier1, tier2],            // List of models (ordered by cost)
  verbose: true,                     // Enable logging
  enableCascade: true,               // Enable cascade system
});
```

### Quality Configuration

Quality validation is controlled via the `quality` option on the agent:

```typescript
import { CascadeAgent } from '@flowgate/core';

// Option 1: Use default (recommended for cascading)
const agent = new CascadeAgent({
  models: [...],
  // Default quality config automatically applied (0.7 threshold)
});

// Option 2: Customize quality settings
const agent = new CascadeAgent({
  models: [...],
  quality: {
    threshold: 0.7,                  // Confidence threshold (0.0-1.0)
    requireMinimumTokens: 10,        // Minimum response length
  },
});

// Option 3: Enable semantic validation with ML
const agent = new CascadeAgent({
  models: [...],
  quality: {
    threshold: 0.40,                 // Traditional confidence threshold
    requireMinimumTokens: 5,
    useSemanticValidation: true,     // Enable ML-based validation
    semanticThreshold: 0.5,          // 50% minimum similarity
  },
});
```

**Quality Threshold Trade-offs:**
- **Higher threshold (0.8+)** → Better quality, fewer drafts accepted, lower savings
- **Medium threshold (0.7)** → Balanced quality and savings (recommended)
- **Lower threshold (0.6-)** → More drafts accepted, higher savings, occasional quality issues

---

## Best Practices

### 1. Choose the Right Models

**Good Combinations:**
- GPT-4o-mini → GPT-4o (balanced, recommended)
- Claude Haiku → GPT-4o (cross-provider)
- Llama 3.1 8B (Groq) → GPT-4o (maximum savings)

**Avoid:**
- Similar-tier models (GPT-4o-mini → GPT-3.5 Turbo)
- Reverse ordering (GPT-4o → GPT-4o-mini)

### 2. Tune Quality Thresholds

Start with default (0.7) and adjust based on your needs:

```typescript
// Track acceptance rates
const results: boolean[] = [];
for (const query of yourQueries) {
  const result = await agent.run(query);
  results.push(result.draftAccepted || false);
}

const acceptanceRate = results.filter(Boolean).length / results.length;
console.log(`Draft acceptance rate: ${(acceptanceRate * 100).toFixed(1)}%`);
```

**If acceptance rate is:**
- < 30% → Lower threshold (0.6) or use better draft model
- 30-70% → Perfect! (balanced)
- > 70% → Can raise threshold (0.75) for better quality

### 3. Monitor Costs

```typescript
// Track costs over time
let totalCost = 0;
for (const query of yourQueries) {
  const result = await agent.run(query);
  totalCost += result.totalCost;
}

console.log(`Total cost: $${totalCost.toFixed(6)}`);
console.log(`Average per query: $${(totalCost / yourQueries.length).toFixed(6)}`);
```

### 4. Handle Failures Gracefully

```typescript
try {
  const result = await agent.run(query);
  console.log(result.content);
} catch (error) {
  console.error('Error:', error);
  // Fallback logic here
}
```

### 5. Use Appropriate Max Tokens

```typescript
// Short responses (save cost)
const result = await agent.run(query, { maxTokens: 50 });

// Medium responses (balanced)
const result = await agent.run(query, { maxTokens: 150 });

// Long responses (quality)
const result = await agent.run(query, { maxTokens: 500 });
```

---

## Troubleshooting

### Issue: All Queries Go to Expensive Model

**Symptoms:**
- Draft acceptance rate < 10%
- Costs almost same as GPT-4 only

**Solutions:**
1. Lower quality threshold:
   ```typescript
   const agent = new CascadeAgent({
     models: [...],
     quality: { threshold: 0.6 }
   });
   ```
2. Use better draft model: Try GPT-4o-mini (already recommended)
3. Check query complexity: Ensure you have simple queries in your mix

### Issue: Poor Quality Responses

**Symptoms:**
- Draft acceptance rate > 80%
- Responses are incorrect or low quality

**Solutions:**
1. Raise quality threshold:
   ```typescript
   const agent = new CascadeAgent({
     models: [...],
     quality: { threshold: 0.75 }
   });
   ```
2. Use better verifier model: Try GPT-4o instead of GPT-4
3. Enable verbose mode to see quality scores: `verbose: true`

### Issue: High Latency

**Symptoms:**
- Responses take too long
- Users complaining about wait times

**Solutions:**
1. Use faster models: Groq Llama for draft, GPT-4o-mini for verifier
2. Reduce max_tokens: `maxTokens: 100`
3. Skip cascade for time-critical queries

### Issue: Costs Higher Than Expected

**Symptoms:**
- Savings < 30%
- Many drafts rejected

**Possible Causes:**
1. Query mix too complex (mostly hard queries)
2. Quality threshold too high (rejecting good drafts)
3. Token estimates inaccurate

**Solutions:**
1. Analyze your query complexity distribution
2. Lower quality threshold slightly
3. Use cheaper draft model (Groq Llama, Ollama)

### Issue: TypeScript Type Errors

**Symptoms:**
- Compilation errors about missing types
- IDE not showing autocomplete

**Solutions:**
1. Ensure TypeScript version 4.5+:
   ```bash
   npm install -D typescript@latest
   ```
2. Check `tsconfig.json` includes:
   ```json
   {
     "compilerOptions": {
       "moduleResolution": "node16",
       "module": "ES2022"
     }
   }
   ```

---

## Next Steps

### 1. Run the Basic Example
```bash
cd packages/core/examples/nodejs
npx tsx basic-usage.ts
```

### 2. Customize for Your Use Case
- Modify models
- Adjust thresholds
- Add your queries

### 3. Read Advanced Guides
- [Multi-Provider Setup](./providers.md)
- [Custom Validation](./custom_validation.md)
- [Browser/Edge Deployment](./browser_cascading.md)

### 4. Explore More Examples
- **Tool Calling:** `tool-calling.ts`
- **Cost Tracking:** `cost-tracking.ts`
- **Multi-Provider:** `multi-provider.ts`
- **Reasoning Models:** `reasoning-models.ts`
- **Semantic Quality:** `semantic-quality.ts`
- **Production Patterns:** `production-patterns.ts`

### 5. Deploy to Production
- Set up monitoring
- Configure logging
- Implement fallbacks
- Track costs

### 6. Join the Community
- ⭐ Star the [GitHub repo](https://github.com/oTheShyo/flowgate)
- 💬 Join [Discussions](https://github.com/oTheShyo/flowgate/discussions)
- 🐛 Report issues
- 🤝 Contribute examples

---

## Quick Reference

### Common Commands

```bash
# Install
npm install @flowgate/core openai

# Run example
npx tsx my-cascade.ts

# Check types
npx tsc --noEmit

# Run with watch mode
npx tsx watch my-cascade.ts
```

### Code Snippets

**Basic Usage:**
```typescript
import { CascadeAgent } from '@flowgate/core';

const agent = new CascadeAgent({
  models: [
    { name: 'gpt-4o-mini', provider: 'openai', cost: 0.000375 },
    { name: 'gpt-4o', provider: 'openai', cost: 0.00625 },
  ],
});

const result = await agent.run('Your query here');
```

**Check Result:**
```typescript
console.log(`Response: ${result.content}`);
console.log(`Model: ${result.modelUsed}`);
console.log(`Cost: $${result.totalCost.toFixed(6)}`);
console.log(`Draft accepted: ${result.draftAccepted}`);
```

**Track Costs:**
```typescript
const total = results.reduce((sum, r) => sum + r.totalCost, 0);
console.log(`Total: $${total.toFixed(6)}`);
```

**With Tools:**
```typescript
const result = await agent.run(query, {
  tools: [
    {
      type: 'function',
      function: {
        name: 'get_weather',
        description: 'Get weather for a location',
        parameters: {
          type: 'object',
          properties: {
            location: { type: 'string' }
          }
        }
      }
    }
  ]
});
```

---

## TypeScript-Specific Features

### Full Type Safety

```typescript
import { CascadeAgent, ModelConfig, CascadeResult } from '@flowgate/core';

const models: ModelConfig[] = [
  { name: 'gpt-4o-mini', provider: 'openai', cost: 0.000375 },
  { name: 'gpt-4o', provider: 'openai', cost: 0.00625 },
];

const agent = new CascadeAgent({ models });
const result: CascadeResult = await agent.run('Hello');

// IDE autocomplete for all properties
result.content;
result.modelUsed;
result.totalCost;
result.draftAccepted;
result.cascaded;
```

### Async/Await

All operations are async - use `await` or `.then()`:

```typescript
// Using await
const result = await agent.run(query);

// Using .then()
agent.run(query).then(result => {
  console.log(result.content);
});
```

### Universal Runtime Support

Works in Node.js, browser, and edge runtimes:

```typescript
// Node.js
import { CascadeAgent } from '@flowgate/core';

// Browser/Edge
import { CascadeAgent } from '@flowgate/core';
// Same code works everywhere!
```

---

## Support

Need help?
- 💬 Ask in [Discussions](https://github.com/oTheShyo/flowgate/discussions)
- 🐛 Report a [bug](https://github.com/oTheShyo/flowgate/issues)
- 📧 Email [hello@flowgate.dev](mailto:hello@flowgate.dev)

---

**Happy Cascading! 🌊**
