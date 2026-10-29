# Cost Tracking Integration

@flowgate/langchain offers **two flexible cost tracking options** to fit your workflow:

## 📊 Cost Tracking Providers

### 1. **LangSmith** (Default)

Use LangSmith's server-side cost calculation - the native LangChain ecosystem choice.

```typescript
import { ChatOpenAI } from '@langchain/openai';
import { withCascade } from '@flowgate/langchain';

const cascade = withCascade({
  drafter: new ChatOpenAI({ modelName: 'gpt-5-nano' }),
  verifier: new ChatOpenAI({ modelName: 'gpt-5' }),
  // LangSmith is the default provider
  costTrackingProvider: 'langsmith', // Can omit this line
});
```

**✅ Benefits:**
- ✓ Automatic, always up-to-date pricing
- ✓ No pricing table maintenance needed
- ✓ Multi-modal cost tracking (text, images, caching, reasoning tokens)
- ✓ Integrated with LangSmith UI for visualization
- ✓ Native LangChain ecosystem integration

**❌ Requirements:**
- Requires `LANGSMITH_API_KEY` environment variable
- Requires network connectivity (costs calculated server-side)

**📈 Viewing Costs:**

Costs are visible in your [LangSmith Dashboard](https://smith.langchain.com). Token counts are automatically sent to LangSmith for server-side cost calculation.

```typescript
const result = await cascade.invoke("Your query");
const stats = cascade.getLastCascadeResult();

console.log('Model Used:', stats.modelUsed);       // drafter or verifier
console.log('Quality:', stats.drafterQuality);     // 0-1 score
console.log('Latency:', stats.latencyMs);          // milliseconds

// ⚠️ Costs are $0 locally (calculated by LangSmith)
console.log('Local Cost:', stats.totalCost);       // 0 (see LangSmith UI)
```

---

### 2. **FlowGate** (Local Calculation)

Use FlowGate's built-in pricing table for offline, dependency-free cost tracking.

```typescript
const cascade = withCascade({
  drafter: new ChatOpenAI({ modelName: 'gpt-5-nano' }),
  verifier: new ChatOpenAI({ modelName: 'gpt-5' }),
  costTrackingProvider: 'flowgate', // Use local pricing
});
```

**✅ Benefits:**
- ✓ No external dependencies
- ✓ Works offline
- ✓ Immediate local cost feedback
- ✓ No LangSmith account required
- ✓ Privacy-friendly (no data sent externally)

**❌ Limitations:**
- Pricing table may lag behind provider updates
- Limited to text tokens (no multi-modal support yet)
- Requires manual updates for new models

**📈 Viewing Costs:**

Costs are calculated immediately and returned in the stats object:

```typescript
const result = await cascade.invoke("Your query");
const stats = cascade.getLastCascadeResult();

console.log('Drafter Cost:', stats.drafterCost);      // $0.000123
console.log('Verifier Cost:', stats.verifierCost);    // $0 (if not used)
console.log('Total Cost:', stats.totalCost);          // $0.000123
console.log('Savings:', stats.savingsPercentage);     // 66.7%
```

---

## 🎯 When to Use Each

### Use **LangSmith** (default) when:

- ✅ You already use LangSmith for observability
- ✅ You want the most accurate, up-to-date pricing
- ✅ You need multi-modal cost tracking
- ✅ You want cost visualization in LangSmith UI
- ✅ You're deploying to production with LangChain ecosystem

### Use **FlowGate** when:

- ✅ You don't want external dependencies
- ✅ You need offline support
- ✅ You want immediate local cost feedback
- ✅ You're prototyping and don't have LangSmith yet
- ✅ You prefer privacy-focused, local-only tracking

---

## ⚙️ Configuration

```typescript
interface CascadeConfig {
  drafter: BaseChatModel;
  verifier: BaseChatModel;
  qualityThreshold?: number;               // 0-1, default: 0.7
  enableCostTracking?: boolean;            // default: true
  costTrackingProvider?: 'langsmith' | 'flowgate';  // default: 'langsmith'
}
```

### Disabling Cost Tracking

```typescript
const cascade = withCascade({
  drafter,
  verifier,
  enableCostTracking: false, // Disable all cost tracking
});
```

---

## 🔄 Switching Providers

You can easily switch between providers:

```typescript
// Development: Use FlowGate for quick local feedback
const devCascade = withCascade({
  drafter,
  verifier,
  costTrackingProvider: 'flowgate',
});

// Production: Use LangSmith for comprehensive observability
const prodCascade = withCascade({
  drafter,
  verifier,
  costTrackingProvider: 'langsmith',
});
```

---

## 📦 Supported Models (FlowGate Provider)

When using `costTrackingProvider: 'flowgate'`, the following models have built-in pricing:

### OpenAI
- `gpt-5`, `gpt-5-mini`, `gpt-5-nano`, `gpt-5.1`
- `gpt-4o`, `gpt-4o-mini`, `gpt-4-turbo`
- `gpt-3.5-turbo`

### Anthropic
- `claude-opus-4-6`, `claude-sonnet-4-6`, `claude-haiku-4-5-20251001`
- `claude-3-5-sonnet-20241022`, `claude-3-5-haiku-20241022`
- `claude-3-opus-20240229`, `claude-3-sonnet-20240229`, `claude-haiku-4-5-20251001`
- `claude-sonnet-4`, `claude-haiku-4.5`

### Google
- `gemini-2.5-flash`, `gemini-2.5-pro`
- `gemini-1.5-pro`, `gemini-1.5-flash`

### Others
- Groq models
- Together AI models

**Missing a model?** It will default to $0 cost. [Open an issue](https://github.com/oTheShyo/flowgate/issues) to request additions.

---

## 🌐 Environment Variables

### For LangSmith Provider

```bash
# Required for LangSmith cost tracking
LANGSMITH_API_KEY=lsv2_pt_...
LANGSMITH_PROJECT=your-project-name
LANGSMITH_TRACING=true  # Optional, enables full tracing
```

### For FlowGate Provider

No environment variables required! Works completely offline.

---

## 💡 Best Practices

1. **Development**: Use `flowgate` provider for fast iteration without LangSmith dependency
2. **Production**: Use `langsmith` provider for comprehensive cost tracking and observability
3. **Hybrid**: Use `flowgate` locally, `langsmith` in CI/production
4. **Privacy**: Use `flowgate` if you can't send data to external services

---

## 📊 Example: Full Comparison

See [`examples/cost-tracking-providers.ts`](../examples/cost-tracking-providers.ts) for a complete side-by-side demonstration of both providers.

```bash
npx tsx examples/cost-tracking-providers.ts
```

---

## 🔗 Related Documentation

- [LangSmith Documentation](https://docs.smith.langchain.com/)
- [FlowGate Pricing Table](../src/models.ts)
- [Main README](../README.md)
