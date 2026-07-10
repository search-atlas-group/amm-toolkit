# MCP Setup Guide

How to connect the SearchAtlas MCP server to Claude Code.

## What is MCP?

[Model Context Protocol (MCP)](https://modelcontextprotocol.io/) lets Claude Code call external tools directly. The SearchAtlas MCP server gives you access to the full SearchAtlas AI Agent platform — SEO, GBP, PPC, content, authority building, LLM visibility, and more.

## Setup (2 steps)

### Step 1: Add the MCP server

Run this once in your terminal:

```bash
claude mcp add searchatlas --transport http https://mcp.searchatlas.com/mcp
```

That's it. No API key, no JSON editing.

### Step 2: Authorize

The first time you use a SearchAtlas tool in Claude Code, it will prompt you to authorize via OAuth. You'll be redirected to your SearchAtlas account to approve access — same login you use on the platform.

After approving, you're connected for the session. Claude Code manages token refresh automatically.

### Verify

Open Claude Code in this directory and run:

```
/my-account
```

You should see your SearchAtlas account overview.

---

## Protocol Details

| Setting | Value |
|---------|-------|
| Protocol | JSON-RPC 2.0 |
| Transport | Streamable HTTP |
| Auth | OAuth 2.1 (handled by Claude Code) |
| Endpoint | `https://mcp.searchatlas.com/mcp` |
| Scopes | `mcp:tools:read`, `mcp:tools:execute`, `mcp:resources:read` |

---

## Troubleshooting

### OAuth prompt not appearing

Restart Claude Code after running `claude mcp add`. The MCP list updates on restart.

### "Unauthorized" errors mid-session

Your OAuth token expired. Run any SearchAtlas tool and re-authorize when prompted, or restart Claude Code.

### Connection timeout

- Verify you can reach `https://mcp.searchatlas.com` from your network
- Check if a firewall or VPN is blocking the connection
- Try restarting Claude Code

### Tool not found / unexpected behavior

The MCP exposes a large set of tools. Use schema discovery — ask Claude to list available SearchAtlas tools or describe what you want to accomplish and let it route to the right tool.

### Re-add or update the MCP

```bash
claude mcp remove searchatlas
claude mcp add searchatlas --transport http https://mcp.searchatlas.com/mcp
```
