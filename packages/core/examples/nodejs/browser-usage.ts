/**
 * Browser Usage Example
 *
 * Demonstrates using flowgate in browser environments:
 * - Client-side integration
 * - Webpack/Vite bundling setup
 * - Environment variable handling
 * - CORS considerations
 * - Browser-specific patterns
 *
 * This is a Node.js example that shows the patterns - for actual browser usage,
 * bundle this with webpack/vite and load in HTML.
 *
 * Usage: npx tsx examples/nodejs/browser-usage.ts
 */

import { CascadeAgent } from '@flowgate/core';

/**
 * Browser-Compatible Configuration
 *
 * In a real browser app, you would:
 * 1. Bundle with Webpack/Vite
 * 2. Use environment variables via import.meta.env or process.env
 * 3. Handle API keys securely (never expose in client code!)
 */

console.log('\n╔═══════════════════════════════════════════════════════════════╗');
console.log('║         flowgate - Browser Integration Guide             ║');
console.log('╚═══════════════════════════════════════════════════════════════╝\n');

console.log('📦 Browser Integration Patterns\n');

// ============================================================================
// Pattern 1: Basic Browser Setup
// ============================================================================

console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
console.log('Pattern 1: Basic Browser Setup');
console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

console.log('1. Install flowgate:');
console.log('   npm install @flowgate/core\n');

console.log('2. Create your browser app:');
console.log(`
// src/app.ts
import { CascadeAgent } from '@flowgate/core';

// Initialize agent (API key from environment or backend)
const agent = new CascadeAgent({
  models: [
    {
      name: 'gpt-4o-mini',
      provider: 'openai',
      cost: 0.00015,
      apiKey: import.meta.env.VITE_OPENAI_API_KEY, // Vite
      // OR: process.env.REACT_APP_OPENAI_API_KEY  // Create React App
    },
    {
      name: 'gpt-4o',
      provider: 'openai',
      cost: 0.00625,
    },
  ],
});

// Use the agent
async function handleQuery(userInput: string) {
  const result = await agent.run(userInput);
  console.log(result.content);
}
`);

console.log('⚠️  Security Warning:');
console.log('   • Never expose API keys in client-side code');
console.log('   • Use backend proxy for production');
console.log('   • Environment variables can still be exposed\n');

// ============================================================================
// Pattern 2: Webpack Configuration
// ============================================================================

console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
console.log('Pattern 2: Webpack Configuration');
console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

console.log('webpack.config.js:');
console.log(`
const webpack = require('webpack');
const path = require('path');

module.exports = {
  entry: './src/index.ts',
  output: {
    path: path.resolve(__dirname, 'dist'),
    filename: 'bundle.js',
  },
  module: {
    rules: [
      {
        test: /\\.tsx?$/,
        use: 'ts-loader',
        exclude: /node_modules/,
      },
    ],
  },
  resolve: {
    extensions: ['.tsx', '.ts', '.js'],
    fallback: {
      // flowgate may need these polyfills
      "buffer": require.resolve("buffer/"),
      "stream": require.resolve("stream-browserify"),
      "util": require.resolve("util/"),
    },
  },
  plugins: [
    new webpack.ProvidePlugin({
      Buffer: ['buffer', 'Buffer'],
      process: 'process/browser',
    }),
    new webpack.DefinePlugin({
      'process.env.OPENAI_API_KEY': JSON.stringify(process.env.OPENAI_API_KEY),
    }),
  ],
};
`);

console.log('Install dependencies:');
console.log('   npm install --save-dev webpack ts-loader buffer stream-browserify util\n');

// ============================================================================
// Pattern 3: Vite Configuration
// ============================================================================

console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
console.log('Pattern 3: Vite Configuration (Recommended)');
console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

console.log('vite.config.ts:');
console.log(`
import { defineConfig } from 'vite';

export default defineConfig({
  build: {
    target: 'esnext',
  },
  define: {
    // Make env vars available
    'import.meta.env.VITE_OPENAI_API_KEY': JSON.stringify(
      process.env.VITE_OPENAI_API_KEY
    ),
  },
  optimizeDeps: {
    include: ['@flowgate/core'],
  },
});
`);

console.log('.env file:');
console.log(`
VITE_OPENAI_API_KEY=your_api_key_here
`);

console.log('Usage in app:');
console.log(`
import { CascadeAgent } from '@flowgate/core';

const agent = new CascadeAgent({
  models: [{
    name: 'gpt-4o-mini',
    provider: 'openai',
    cost: 0.00015,
    apiKey: import.meta.env.VITE_OPENAI_API_KEY,
  }],
});
`);

console.log('\n');

// ============================================================================
// Pattern 4: React Integration
// ============================================================================

console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
console.log('Pattern 4: React Integration');
console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

console.log('Custom Hook Pattern:');
console.log(`
// hooks/useFlowgate.ts
import { useState, useCallback } from 'react';
import { CascadeAgent } from '@flowgate/core';

// Initialize agent outside component (singleton)
const agent = new CascadeAgent({
  models: [
    { name: 'gpt-4o-mini', provider: 'openai', cost: 0.00015 },
    { name: 'gpt-4o', provider: 'openai', cost: 0.00625 },
  ],
});

export function useFlowgate() {
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<string>('');
  const [cost, setCost] = useState<number>(0);
  const [error, setError] = useState<string | null>(null);

  const query = useCallback(async (text: string) => {
    setLoading(true);
    setError(null);

    try {
      const result = await agent.run(text, { maxTokens: 200 });
      setResponse(result.content);
      setCost(result.totalCost);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, []);

  return { query, loading, response, cost, error };
}
`);

console.log('Component Usage:');
console.log(`
// components/ChatBox.tsx
import React, ` + `{ useState }` + ` from 'react';
import ` + `{ useFlowgate }` + ` from '../hooks/useFlowgate';

export function ChatBox() {
  const [input, setInput] = useState('');
  const ` + `{ query, loading, response, cost, error }` + ` = useFlowgate();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim()) {
      query(input);
    }
  };

  return (
    <div className="chat-box">
      <form onSubmit=` + `{handleSubmit}` + `>
        <input
          value=` + `{input}` + `
          onChange=` + `{(e) => setInput(e.target.value)}` + `
          placeholder="Ask anything..."
          disabled=` + `{loading}` + `
        />
        <button type="submit" disabled=` + `{loading}` + `>
          ` + `{loading ? 'Thinking...' : 'Send'}` + `
        </button>
      </form>

      ` + `{error && <div className="error">{error}</div>}` + `

      ` + `{response && (
        <div className="response">
          <p>{response}</p>
          <small>Cost: $` + `{cost.toFixed(6)}` + `</small>
        </div>
      )}` + `
    </div>
  );
}
`);

console.log('\n');

// ============================================================================
// Pattern 5: Vue Integration
// ============================================================================

console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
console.log('Pattern 5: Vue Integration');
console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

console.log('Composable Pattern:');
console.log(`
// composables/useFlowgate.ts
import { ref } from 'vue';
import { CascadeAgent } from '@flowgate/core';

const agent = new CascadeAgent({
  models: [
    { name: 'gpt-4o-mini', provider: 'openai', cost: 0.00015 },
  ],
});

export function useFlowgate() {
  const loading = ref(false);
  const response = ref('');
  const cost = ref(0);
  const error = ref<string | null>(null);

  const query = async (text: string) => {
    loading.value = true;
    error.value = null;

    try {
      const result = await agent.run(text);
      response.value = result.content;
      cost.value = result.totalCost;
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Unknown error';
    } finally {
      loading.value = false;
    }
  };

  return { query, loading, response, cost, error };
}
`);

console.log('Component Usage:');
console.log(`
<!-- ChatBox.vue -->
<template>
  <div class="chat-box">
    <form @submit.prevent="handleSubmit">
      <input
        v-model="input"
        placeholder="Ask anything..."
        :disabled="loading"
      />
      <button type="submit" :disabled="loading">
        ` + `{{ loading ? 'Thinking...' : 'Send' }}` + `
      </button>
    </form>

    <div v-if="error" class="error">` + `{{ error }}` + `</div>

    <div v-if="response" class="response">
      <p>` + `{{ response }}` + `</p>
      <small>Cost: $` + `{{ cost.toFixed(6) }}` + `</small>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useFlowgate } from '../composables/useFlowgate';

const input = ref('');
const ` + `{ query, loading, response, cost, error }` + ` = useFlowgate();

const handleSubmit = () => {
  if (input.value.trim()) {
    query(input.value);
    input.value = '';
  }
};
</script>
`);

console.log('\n');

// ============================================================================
// Pattern 6: Production Backend Proxy
// ============================================================================

console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
console.log('Pattern 6: Production Backend Proxy (Recommended)');
console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

console.log('⚠️  For production, use a backend proxy to protect API keys!\n');

console.log('Backend (Express):');
console.log(`
// server.ts
import express from 'express';
import { CascadeAgent } from '@flowgate/core';

const app = express();
app.use(express.json());

// Initialize agent on server (API key stays secure)
const agent = new CascadeAgent({
  models: [
    {
      name: 'gpt-4o-mini',
      provider: 'openai',
      cost: 0.00015,
      apiKey: process.env.OPENAI_API_KEY, // Secure server-side
    },
  ],
});

app.post('/api/query', async (req, res) => {
  try {
    const { query } = req.body;
    const result = await agent.run(query);
    res.json({
      content: result.content,
      cost: result.totalCost,
      model: result.modelUsed,
    });
  } catch (error) {
    res.status(500).json({ error: 'Query failed' });
  }
});

app.listen(3000);
`);

console.log('Frontend (Fetch API):');
console.log(`
// client.ts
async function queryFlowgate(text: string) {
  const response = await fetch('/api/query', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query: text }),
  });

  if (!response.ok) throw new Error('Query failed');

  const data = await response.json();
  return data;
}

// Usage
const result = await queryFlowgate('What is TypeScript?');
console.log(result.content);
`);

console.log('\n');

// ============================================================================
// Pattern 7: Streaming in Browser
// ============================================================================

console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
console.log('Pattern 7: Streaming in Browser');
console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

console.log('Client-side streaming works with async iterators:');
console.log(`
import { CascadeAgent, StreamEventType } from '@flowgate/core';

const agent = new CascadeAgent({
  models: [{ name: 'gpt-4o-mini', provider: 'openai', cost: 0.00015 }],
});

async function streamQuery(text: string, onChunk: (chunk: string) => void) {
  for await (const event of agent.stream(text)) {
    if (event.type === StreamEventType.CHUNK) {
      onChunk(event.content);
    }
  }
}

// React usage
function StreamingChat() {
  const [response, setResponse] = useState('');

  const handleQuery = async (text: string) => {
    setResponse('');
    await streamQuery(text, (chunk) => {
      setResponse(prev => prev + chunk);
    });
  };

  return <div>{response}</div>;
}
`);

console.log('\n');

// ============================================================================
// Summary
// ============================================================================

console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
console.log('📋 Browser Integration Summary');
console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

console.log('✅ Supported Bundlers:');
console.log('   • Webpack (with polyfills)');
console.log('   • Vite (recommended)');
console.log('   • Rollup');
console.log('   • esbuild');
console.log('');

console.log('✅ Supported Frameworks:');
console.log('   • React');
console.log('   • Vue');
console.log('   • Svelte');
console.log('   • Angular');
console.log('   • Vanilla JS/TS');
console.log('');

console.log('🔒 Security Best Practices:');
console.log('   1. Never expose API keys in client code');
console.log('   2. Use backend proxy for production');
console.log('   3. Implement rate limiting');
console.log('   4. Validate user input');
console.log('   5. Use environment variables properly');
console.log('');

console.log('⚡ Performance Tips:');
console.log('   • Initialize agent once (singleton pattern)');
console.log('   • Use streaming for better UX');
console.log('   • Implement loading states');
console.log('   • Cache responses when appropriate');
console.log('   • Monitor costs in production');
console.log('');

console.log('📚 Next Steps:');
console.log('   • See express-integration.ts for backend setup');
console.log('   • See streaming-text.ts for streaming patterns');
console.log('   • Check framework docs for specific integration');
console.log('');

console.log('✨ Done! You now know how to use flowgate in browsers.');
console.log('   This was a guide - adapt patterns to your stack.\n');
