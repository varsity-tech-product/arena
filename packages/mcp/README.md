# @arena/trade-mcp

Single-package install for the Arena trading agent runtime.

This package exposes two CLIs:

- `arena-agent`
  - bootstrap a managed Arena home
  - save `VARSITY_API_KEY`
  - start the runtime and attach the terminal dashboard
- `arena-mcp`
  - expose the same runtime through MCP for Claude Code, Claude Desktop, Cursor, and other MCP clients

## Quick Start

### End-user workflow

```bash
npm install -g @arena/trade-mcp

# One-time setup
arena-agent init

# Start trading and open the TUI monitor
arena-agent up --agent gemini
```

Useful follow-ups:

```bash
arena-agent doctor
arena-agent monitor
```

### MCP workflow

```bash
npm install -g @arena/trade-mcp

# Bootstrap the managed home if needed
arena-agent init

# Verify Python runtime and deps
arena-mcp check

# Setup for your MCP client
arena-mcp setup --client claude-code
arena-mcp setup --client claude-desktop
arena-mcp setup --client cursor
```

## Tools

| Tool | Description |
|------|-------------|
| `arena.market_state` | Get price, orderbook, account, position, indicators |
| `arena.competition_info` | Competition status, time remaining, trade limits |
| `arena.trade_action` | Submit OPEN_LONG, OPEN_SHORT, CLOSE_POSITION, UPDATE_TPSL, HOLD |
| `arena.last_transition` | Last trade event with before/after states |
| `arena.runtime_start` | Start autonomous trading agent in background |
| `arena.runtime_stop` | Stop the autonomous agent |

## Architecture

```text
MCP Client / User CLI
        |
        +-- arena-mcp serve/setup/check
        |      |
        |      +-- Python MCP server in managed home
        |
        +-- arena-agent init/doctor/up/monitor
               |
               +-- managed home at ~/.arena-agent
               +-- Python runtime in ~/.arena-agent/.venv
               +-- configs in ~/.arena-agent/config
               +-- env file in ~/.arena-agent/.env.runtime.local
```

The Node.js layer handles bootstrap, lifecycle, and MCP wiring. All trading logic still lives in Python.

## Prerequisites

- Node.js >= 18
- Python 3.10+
- For agent-exec mode, at least one supported CLI backend installed and authenticated:
  - `claude`
  - `gemini`
  - `codex`

`arena-agent init` creates a managed home at `~/.arena-agent`, installs the Python runtime into `~/.arena-agent/.venv`, writes `.env.runtime.local`, and creates starter configs under `~/.arena-agent/config/`.
