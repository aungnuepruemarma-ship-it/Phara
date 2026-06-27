# Higgsfield AI MCP Server

MCP server that exposes [Higgsfield AI](https://higgsfield.ai) video-generation capabilities as tools for any MCP-compatible client (Claude Desktop, Cursor, Windsurf, etc.).

## Tools

| Tool | Description |
|------|-------------|
| `generate_video` | Generate a video from a text prompt or an image URL |
| `get_video_status` | Poll a generation job and retrieve the download URL when ready |
| `list_videos` | List past generations for your account (paginated) |
| `delete_video` | Permanently delete a generation and its video file |
| `get_account_info` | View account details and usage quotas |
| `list_camera_motions` | List all available camera movement presets |
| `list_models` | List available generation models with descriptions |

## Setup

### 1. Get your API key

Sign up at [higgsfield.ai](https://higgsfield.ai) and copy your API key from the dashboard.

### 2. Install

```bash
cd mcp
pip install -e .
```

Or run directly without installing:

```bash
cd mcp
pip install -r higgsfield/requirements.txt
python -m higgsfield.server
```

### 3. Configure Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "higgsfield": {
      "command": "python",
      "args": ["-m", "higgsfield.server"],
      "cwd": "/path/to/Phara/mcp",
      "env": {
        "HIGGSFIELD_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

Or if installed via pip:

```json
{
  "mcpServers": {
    "higgsfield": {
      "command": "higgsfield-mcp",
      "env": {
        "HIGGSFIELD_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `HIGGSFIELD_API_KEY` | Yes | Your Higgsfield AI API key |

## Example Usage

Once connected, ask Claude:

> "Generate a 6-second cinematic video of a mountain sunrise with a slow zoom-in camera movement."

> "Check the status of generation abc123."

> "List my last 5 video generations."

## Camera Motions

`static` · `pan_left` · `pan_right` · `tilt_up` · `tilt_down` · `zoom_in` · `zoom_out` · `orbit_left` · `orbit_right` · `crane_up` · `crane_down` · `dolly_in` · `dolly_out`

## Models

| Model | Description |
|-------|-------------|
| `higgsfield-1` | Flagship cinematic model — best quality (recommended) |
| `diffusion-1` | Fast diffusion model — lower latency |

## Aspect Ratios

| Value | Use case |
|-------|----------|
| `16:9` | Landscape / YouTube / cinema (default) |
| `9:16` | Portrait / TikTok / Reels |
| `1:1` | Square / Instagram |
