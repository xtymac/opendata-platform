#!/bin/bash

echo "=== Testing Playwright MCP Setup ==="
echo ""

echo "1. Checking Node.js and npx..."
node --version
npx --version
echo ""

echo "2. Testing Playwright MCP help..."
npx @playwright/mcp@latest --help | head -20
echo ""

echo "3. Starting Playwright MCP server (headless mode)..."
echo "   This will start the server in the background for testing"
echo ""

# Test if we can run it
timeout 5s npx @playwright/mcp@latest --browser chromium --headless &
PID=$!

sleep 3

if ps -p $PID > /dev/null; then
    echo "✓ Playwright MCP server started successfully (PID: $PID)"
    kill $PID 2>/dev/null
else
    echo "✗ Playwright MCP server failed to start"
fi

echo ""
echo "=== Configuration for Claude Desktop ==="
echo ""
cat ~/.config/claude/claude_desktop_config.json
echo ""

echo "=== To use with Claude Desktop ==="
echo "1. Copy the configuration from ~/.config/claude/claude_desktop_config.json"
echo "2. Add it to your Claude Desktop settings"
echo "3. Restart Claude Desktop"
echo ""

echo "=== To test the CKAN homepage with Playwright ==="
echo "You can use commands like:"
echo "  npx @playwright/mcp@latest --browser chromium"
echo ""
