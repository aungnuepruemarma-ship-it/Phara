#!/bin/bash
# SessionStart hook — installs and wires up all MCP servers on every new session.
set -e
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG="$REPO/.claude/setup-mcp.log"

log() { echo "[$(date '+%H:%M:%S')] $*" | tee -a "$LOG"; }

log "=== MCP setup starting ==="
log "Repo: $REPO"

# 1. claude-flow
if ! command -v claude-flow &>/dev/null; then
  log "Installing claude-flow..."
  npm install -g claude-flow >> "$LOG" 2>&1
else
  log "claude-flow already installed: $(claude-flow --version 2>/dev/null)"
fi

# 2. Shodan MCP
if ! command -v mcp-shodan &>/dev/null; then
  log "Installing mcp-shodan..."
  npm install -g @burtthecoder/mcp-shodan >> "$LOG" 2>&1
else
  log "mcp-shodan already installed"
fi

# 3. Tor (for onion search)
if ! command -v tor &>/dev/null; then
  log "Installing Tor..."
  apt-get install -y tor >> "$LOG" 2>&1
fi

# 4. Python deps
log "Installing Python packages..."
pip install -q "mcp[cli]>=1.0.0" httpx pydantic fal-client requests[socks] PySocks >> "$LOG" 2>&1

# 5. Make wrappers executable
chmod +x "$REPO/mcp/claude-flow-start.sh"

# 6. Start Tor in background if not running
if ! pgrep -x tor &>/dev/null; then
  log "Starting Tor..."
  tor --RunAsDaemon 1 --Log "warn file /tmp/tor.log" >> "$LOG" 2>&1
  sleep 3
fi

# 7. Write ~/.claude/settings.json with all 5 MCP servers
mkdir -p ~/.claude
FAL_KEY="9fadd662-39fe-4a7c-a8b4-3dde85ee79dd:1cf87670cc81aa998ab0817f28ec4dcb"
SHODAN_API_KEY="${SHODAN_API_KEY:-}"

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
    },
    "shodan": {
      "command": "/opt/node22/bin/mcp-shodan",
      "env": {
        "SHODAN_API_KEY": "$SHODAN_API_KEY"
      }
    },
    "onion-search": {
      "command": "/usr/local/bin/python",
      "args": ["$REPO/mcp/onion-search/server.py"],
      "env": {
        "TOR_SOCKS_PORT": "9050"
      }
    }
  }
}
JSON

log "Written ~/.claude/settings.json (5 MCP servers)"
log "=== MCP setup complete ==="
