#!/bin/bash

# MessageList Component Verification Script
# Checks for common issues and validates the implementation

echo "==================================="
echo "MessageList Component Verification"
echo "==================================="
echo ""

# Check if files exist
echo "1. Checking file existence..."
FILES=(
  "MessageList.tsx"
  "MessageList.module.css"
  "MessageItem.tsx"
  "MessageItem.module.css"
  "index.ts"
  "README.md"
)

for file in "${FILES[@]}"; do
  if [ -f "$file" ]; then
    echo "  ✓ $file exists"
  else
    echo "  ✗ $file missing"
  fi
done

echo ""

# Count lines
echo "2. Checking line counts..."
echo "  MessageList.tsx: $(wc -l < MessageList.tsx) lines"
echo "  MessageItem.tsx: $(wc -l < MessageItem.tsx) lines"
echo "  MessageList.module.css: $(wc -l < MessageList.module.css) lines"
echo "  MessageItem.module.css: $(wc -l < MessageItem.module.css) lines"

echo ""

# Check for common issues
echo "3. Checking for common issues..."

# Check for console.log (should be removed in production)
if grep -q "console.log" MessageList.tsx MessageItem.tsx 2>/dev/null; then
  echo "  ⚠ Warning: console.log found (consider removing for production)"
else
  echo "  ✓ No console.log statements"
fi

# Check for any type
if grep -q ": any" MessageList.tsx MessageItem.tsx 2>/dev/null; then
  echo "  ⚠ Warning: 'any' type found (consider using specific types)"
else
  echo "  ✓ No 'any' types used"
fi

# Check for TODO comments
if grep -q "TODO\|FIXME" MessageList.tsx MessageItem.tsx 2>/dev/null; then
  echo "  ⚠ Warning: TODO/FIXME comments found"
else
  echo "  ✓ No TODO/FIXME comments"
fi

echo ""

# Check imports
echo "4. Checking imports..."
if grep -q "react-window" MessageList.tsx; then
  echo "  ✓ react-window imported"
else
  echo "  ✗ react-window not imported"
fi

if grep -q "from 'antd'" MessageList.tsx MessageItem.tsx; then
  echo "  ✓ Ant Design components imported"
else
  echo "  ✗ Ant Design not imported"
fi

echo ""

# Check exports
echo "5. Checking exports..."
if grep -q "export default MessageList" MessageList.tsx; then
  echo "  ✓ MessageList exported"
else
  echo "  ✗ MessageList not exported"
fi

if grep -q "export default MessageItem" MessageItem.tsx; then
  echo "  ✓ MessageItem exported"
else
  echo "  ✗ MessageItem not exported"
fi

if grep -q "export type { Message }" index.ts; then
  echo "  ✓ Message type exported"
else
  echo "  ✗ Message type not exported"
fi

echo ""

# Summary
echo "==================================="
echo "Verification Complete!"
echo "==================================="
echo ""
echo "Next steps:"
echo "1. Install react-window: npm install react-window @types/react-window"
echo "2. Run TypeScript compiler: npx tsc --noEmit"
echo "3. Test the component with sample data"
echo ""
