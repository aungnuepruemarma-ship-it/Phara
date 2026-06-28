#!/bin/bash
# SessionStart hook — installs and wires up all MCP servers on every new session.
# Runs automatically via .claude/settings.json SessionStart hook.

set -e
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG="$REPO/.claude/setup-mcp.log"

log() { echo "[$(date '+%H:%M:%S')] $*" | tee -a "$LOG"; }

log "=== MCP setup starting ==="
log "Repo: $REPO"

# 1. Install claude-flow globally (idempotent)
if ! command -v claude-flow &>/dev/null; then
  log "Installing claude-flow..."
  npm install -g claude-flow >> "$LOG" 2>&1
else
  log "claude-flow already installed: $(claude-flow --version 2>/dev/null)"
fi

# 2. Install Python deps for fal + higgsfield servers
log "Installing Python packages..."
pip install -q "mcp[cli]>=1.0.0" httpx pydantic fal-client >> "$LOG" 2>&1

# 3. Make wrapper executable
chmod +x "$REPO/mcp/claude-flow-start.sh"

# 4. Write ~/.claude/settings.json with all 3 MCP servers
mkdir -p ~/.claude
FAL_KEY="9fadd662-39fe-4a7c-a8b4-3dde85ee79dd:1cf87670cc81aa998ab0817f28ec4dcb"

cat > ~/.claude/settings.json <<JSON
{
  "mcpServers": {
    "higgsfield": {
      "command": "/usr/local/bin/python",
      "args": ["$REPO/mcp/higgsfield/server.py"],
      "env": {
        "HIGGSFIELD_API_KEY": ""
      }
    },
    "fal": {
      "command": "/usr/local/bin/python",
      "args": ["$REPO/mcp/fal/server.py"],
      "env": {
        "FAL_KEY": "$FAL_KEY"
      }
    },
    "claude-flow": {
      "command": "/bin/bash",
      "args": ["$REPO/mcp/claude-flow-start.sh"]
    }
  }
}
JSON

log "Written ~/.claude/settings.json"
log "=== MCP setup complete ==="
