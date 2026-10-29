/**
 * Basic LangChain Cascade Example
 *
 * Demonstrates how to wrap existing LangChain models with flowgate
 * for automatic cost optimization.
 *
 * Setup:
 *   export OPENAI_API_KEY="sk-..."
 *   pnpm install
 *   npx tsx examples/basic-usage.ts
 */

import { ChatOpenAI } from '@langchain/openai';
import { withCascade } from '../src/index.js';

async function main() {
  // Check API key
  if (!process.env.OPENAI_API_KEY) {
    console.log("❌ Set OPENAI_API_KEY first: export OPENAI_API_KEY='sk-...'");
    return;
  }

  console.log('🌊 LangChain + FlowGate Integration\n');

  // ========================================================================
  // STEP 1: Configure your existing LangChain models
  // ========================================================================
  // Nothing changes here - use your existing model configurations!

  const drafter = new ChatOpenAI({
    model: 'gpt-4o-mini',
    temperature: 0.7,
  });

  const verifier = new ChatOpenAI({
    model: 'gpt-4o',
    temperature: 0.7,
  });

  console.log('✓ Configured drafter: gpt-4o-mini ($0.15/1M tokens)');
  console.log('✓ Configured verifier: gpt-4o ($2.50/1M tokens)');
  console.log('✓ Cost difference: ~17x\n');

  // ========================================================================
  // STEP 2: Wrap with cascade (just 2 lines!)
  // ========================================================================

  const cascadeModel = withCascade({
    drafter,
    verifier,
    qualityThreshold: 0.7,
    // Use local pricing so costs/savings show up in `getLastCascadeResult()`.
    // If you prefer LangSmith to calculate costs server-side, omit this (costs will be $0 locally).
    costTrackingProvider: 'flowgate',
  });

  console.log('✓ Wrapped models with cascade logic\n');

  // ========================================================================
  // STEP 3: Use like any LangChain model
  // ========================================================================

  console.log('='.repeat(60));
  console.log('Example 1: Simple Question (may use drafter or verifier)\n');

  const result1 = await cascadeModel.invoke('What is 2+2?');
  console.log(`Answer: ${result1.content}\n`);

  // Get cascade statistics
  const stats1 = cascadeModel.getLastCascadeResult();
  if (stats1) {
    console.log('📊 Cascade Stats:');
    console.log(`   Model used: ${stats1.modelUsed}`);
    console.log(
      `   Drafter quality: ${typeof stats1.drafterQuality === 'number'
        ? `${(stats1.drafterQuality * 100).toFixed(0)}%`
        : 'n/a (direct-to-verifier)'}`
    );
    console.log(`   Accepted: ${stats1.accepted ? '✅' : '❌'}`);
    console.log(`   Drafter cost: $${stats1.drafterCost.toFixed(6)}`);
    console.log(`   Verifier cost: $${stats1.verifierCost.toFixed(6)}`);
    console.log(`   Total cost: $${stats1.totalCost.toFixed(6)}`);
    console.log(`   Savings: ${stats1.savingsPercentage.toFixed(1)}%`);
    console.log(`   Latency: ${stats1.latencyMs}ms`);
  }

  // ========================================================================
  // STEP 4: Complex question (may cascade)
  // ========================================================================

  console.log('\n' + '='.repeat(60));
  console.log('Example 2: Complex Question (may need verifier)\n');

  const result2 = await cascadeModel.invoke(
    'Explain the implications of quantum entanglement for computing.'
  );
  console.log(`Answer: ${result2.content.substring(0, 200)}...\n`);

  const stats2 = cascadeModel.getLastCascadeResult();
  if (stats2) {
    console.log('📊 Cascade Stats:');
    console.log(`   Model used: ${stats2.modelUsed}`);
    console.log(
      `   Drafter quality: ${typeof stats2.drafterQuality === 'number'
        ? `${(stats2.drafterQuality * 100).toFixed(0)}%`
        : 'n/a (direct-to-verifier)'}`
    );
    console.log(`   Accepted: ${stats2.accepted ? '✅' : '❌'}`);
    console.log(`   Total cost: $${stats2.totalCost.toFixed(6)}`);
    console.log(`   Savings: ${stats2.savingsPercentage.toFixed(1)}%`);
  }

  // ========================================================================
  // STEP 5: All LangChain features work!
  // ========================================================================

  console.log('\n' + '='.repeat(60));
  console.log('Example 3: Chainable methods work seamlessly\n');

  // bind() works
  const boundModel = cascadeModel.bind({ temperature: 0.1 });
  const result3 = await boundModel.invoke('What is TypeScript?');
  console.log(`✓ bind() works: ${result3.content.substring(0, 100)}...\n`);

  // ========================================================================
  // Summary
  // ========================================================================

  console.log('='.repeat(60));
  console.log('\n✅ Key Takeaways:');
  console.log('   • Zero code changes to your LangChain models');
  console.log('   • Potential cost savings when drafter is accepted');
  console.log('   • All LangChain features preserved');
  console.log('   • Quality-based cascading ensures no degradation');
  console.log('   • Full visibility into cascade decisions\n');
}

main().catch(console.error);
