#!/bin/bash
# Test TypeScript examples with proper workspace setup
#
# This script:
# 1. Ensures the package is built
# 2. Loads environment variables
# 3. Runs each TypeScript example
# 4. Reports results

set -e

echo "====================================="
echo "TypeScript Examples Testing"
echo "====================================="

# Navigate to examples directory
cd "$(dirname "$0")/../packages/core/examples" || exit 1

# Build parent package if needed
if [ ! -d "../dist" ]; then
    echo "📦 Building @flowgate/core..."
    cd ..
    pnpm build
    cd examples
fi

# Load environment variables
if [ -f "../../../.env" ]; then
    set -a
    source ../../../.env
    set +a
    echo "✅ Environment variables loaded"
else
    echo "⚠️  No .env file found"
fi

echo ""
echo "Running TypeScript examples..."
echo "-------------------------------------"

PASSED=0
FAILED=0

# Test Node.js examples
NODE_EXAMPLES=(
    "nodejs/basic-usage.ts"
    "nodejs/tool-calling.ts"
    "nodejs/multi-provider.ts"
    "nodejs/production-patterns.ts"
)

for example in "${NODE_EXAMPLES[@]}"; do
    echo ""
    echo "Testing: $example"

    if npx tsx "$example" > /dev/null 2>&1; then
        echo "✅ PASSED"
        ((PASSED++))
    else
        echo "❌ FAILED"
        # Show error
        npx tsx "$example" 2>&1 | tail -20
        ((FAILED++))
    fi
done

# Test streaming example
if [ -f "streaming.ts" ]; then
    echo ""
    echo "Testing: streaming.ts"

    if npx tsx streaming.ts > /dev/null 2>&1; then
        echo "✅ PASSED"
        ((PASSED++))
    else
        echo "❌ FAILED"
        npx tsx streaming.ts 2>&1 | tail -20
        ((FAILED++))
    fi
fi

# Validate browser example (compile only)
if [ -f "browser/vercel-edge/api/chat.ts" ]; then
    echo ""
    echo "Validating: browser/vercel-edge/api/chat.ts"

    # Just check if it compiles
    if npx tsc --noEmit browser/vercel-edge/api/chat.ts 2>/dev/null; then
        echo "✅ VALIDATED (compiles)"
        ((PASSED++))
    else
        echo "⚠️  VALIDATION WARNING"
        npx tsc --noEmit browser/vercel-edge/api/chat.ts 2>&1 | tail -10
        # Don't count as failure - browser examples need special env
    fi
fi

echo ""
echo "====================================="
echo "Summary:"
echo "  ✅ Passed: $PASSED"
echo "  ❌ Failed: $FAILED"
echo "====================================="

exit $FAILED
