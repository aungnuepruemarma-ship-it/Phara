#!/bin/bash
# Auto-reads Claude Code session token and starts claude-flow MCP server
TOKEN_FILE="/home/claude/.claude/remote/.session_ingress_token"
[ -f "$TOKEN_FILE" ] && export ANTHROPIC_API_KEY=$(cat "$TOKEN_FILE")
export ANTHROPIC_BASE_URL="${ANTHROPIC_BASE_URL:-https://api.anthropic.com}"
exec /opt/node22/bin/claude-flow mcp start "$@"
