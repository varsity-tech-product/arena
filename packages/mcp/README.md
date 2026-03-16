# @arena/trade-mcp

MCP server for the Arena trading agent runtime. Connect Claude Code, Claude Desktop, Cursor, or any MCP client to trade on Varsity Arena.

## Quick Start

```bash
# From the arena project root
cd packages/mcp
npm install
npm run build

# Check Python environment
node dist/cli.js check

# Setup for your MCP client
node dist/cli.js setup --client claude-code
node dist/cli.js setup --client claude-desktop
node dist/cli.js setup --client cursor
```

Or install globally:

```bash
npm install -g .
arena-mcp check
arena-mcp setup --client claude-code
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

```
MCP Client (Claude)  <--stdio-->  arena-mcp (Node.js)  <--stdio-->  Python MCP server
                                      │
                                      ├── arena.market_state      → Python bridge
                                      ├── arena.competition_info  → Python bridge
                                      ├── arena.trade_action      → Python bridge
                                      ├── arena.last_transition   → Python bridge
                                      ├── arena.runtime_start     → spawns Python runtime
                                      └── arena.runtime_stop      → kills runtime process
```

The Node.js layer is a thin wrapper. All trading logic stays in Python.

## Prerequisites

- Node.js >= 18
- Python 3.12+ with venv at `<arena_root>/.venv`
- `pip install -e <arena_root> mcp` in the venv
- `.env.runtime.local` with `VARSITY_API_KEY`
