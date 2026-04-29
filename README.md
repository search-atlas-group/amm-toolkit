# Agentic Marketing Mastermind

AI-powered digital marketing toolkit for [SearchAtlas](https://searchatlas.com) agencies. Run SEO, GBP, PPC, content, and LLM visibility workflows — all from your terminal with Claude Code.

## Setup (~5–10 minutes)

One command. It will ask you two questions — your workspace name and which IDE you use — then handle everything else automatically.

**macOS** — paste into Terminal:
```bash
/bin/bash -c "$(curl -fsSL https://forge.internal.searchatlas.com/search-atlas-group/agentic-marketing-mastermind/amm-toolkit/-/raw/main/Scripts/quickstart-mac.sh)"
```

**Windows** — paste into PowerShell (run as Administrator):
```powershell
irm https://forge.internal.searchatlas.com/search-atlas-group/agentic-marketing-mastermind/amm-toolkit/-/raw/main/Scripts/quickstart-windows.ps1 | iex
```

The setup will:
1. Create your agency workspace folder (you choose the name)
2. Ask which IDE you use — Cursor, Warp, VS Code, Windsurf, etc.
3. Install Git and Node.js if not already present
4. Install Claude Code via npm (`npm install -g @anthropic-ai/claude-code`)
5. Clone this toolkit into `~/YourWorkspace/AMM-SA/`
6. Connect the SearchAtlas MCP (OAuth — no API key needed)
7. Install all slash commands
8. Open your workspace in your chosen IDE

Your workspace will look like this:
```
~/YourWorkspace/
├── AMM-SA/       ← this toolkit (commands, workflows, docs)
└── clients/      ← one folder per client project
```

**First use:** Open your workspace in Claude Code (`claude` in terminal), then run `/my-account`. Claude will prompt you to authorize your SearchAtlas account — one-time OAuth flow.

## Commands

### Account & Clients
```
/my-account          # All businesses, projects, campaigns, GBP locations
/business-report     # Deep dive on a single business
/onboard-client      # Guided new client setup (brand vault pull or manual)
/sync-client         # Two-way sync: local brand-profile.md ↔ SA brand vault
```

### Execute Workflows
```
/run-seo             # SEO onboarding or monthly maintenance
/run-gbp             # Google Business Profile optimization
/run-ppc             # PPC campaign build and launch
/run-content         # Article generation from topical maps
/run-pr              # Press releases + cloud stacks + digital PR
/run-visibility      # LLM visibility and sentiment monitoring
```

### Share Results
```
/send-slack          # Post to Slack (supports multiple channels)
/send-discord        # Post to Discord via webhook
/send-email          # Send an email via Resend API
/send-circle         # Post to a Circle community space
```

### Security
```
/security-scan <url> # Scan any GitHub repo for threats before cloning or running it
```

## All Commands

| Command | Description |
|---------|-------------|
| `/my-account` | Show all businesses, projects, campaigns, and GBP locations |
| `/onboard-client` | Guided client onboarding — pull from brand vault or enter manually |
| `/sync-client` | Two-way sync between local brand-profile.md and SearchAtlas brand vault |
| `/business-report` | Deep dive report on a single business |
| `/run-seo` | SEO onboarding or monthly maintenance workflow |
| `/run-gbp` | Optimize a Google Business Profile |
| `/run-ppc` | Build and launch a PPC campaign |
| `/run-content` | Generate articles, topical maps, content briefs |
| `/run-pr` | Create and distribute press releases |
| `/run-visibility` | Run LLM visibility and sentiment analysis |
| `/send-slack` | Post to Slack (supports multiple channels) |
| `/send-discord` | Post to Discord via webhook |
| `/send-email` | Send an email via Resend API |
| `/send-circle` | Post to a Circle community space |
| `/security-scan` | Scan any GitHub repo for threats before cloning or running it |
| `/help` | List all available commands |

## Automate with Workflow Templates

Templates in `workflows/` define step-by-step tool chains for recurring tasks:

| Template | Use case |
|----------|----------|
| `seo-onboarding.yaml` | Full new client SEO setup |
| `monthly-seo.yaml` | Monthly maintenance: suggestions, schema, indexing |
| `gbp-optimization.yaml` | GBP cleanup: recommendations, categories, services |
| `gbp-monthly.yaml` | GBP maintenance: reviews, posts, automation |
| `ppc-launch.yaml` | PPC campaign: business, products, keywords, campaigns |
| `authority-building.yaml` | PR and link building: press, cloud stacks, outreach |
| `llm-visibility.yaml` | AI search: visibility, sentiment, SERP analysis |

## Security Scanner

Every installation includes a built-in repo security scanner. Before cloning any third-party tool or library, scan it first:

```
/security-scan https://github.com/owner/repo
```

Claude runs a 4-tier analysis — GitHub metadata, secrets detection, CVE checks, SAST rules, and an optional behavioral sandbox — and gives you a plain-English verdict before you touch any code.

**Three ways to scan:**

| Option | How | Best for |
|--------|-----|----------|
| Browser quick check | Paste URL into `tools/security/` UI | Fast first look, no setup |
| Full local scan | `python3 tools/security/server.py` then open the UI | Thorough pre-clone analysis |
| Claude Code | `/security-scan <url>` in Claude Code chat | Deep AI review with full report |

See [guides/security-scan-guide.md](guides/security-scan-guide.md) for full details.

## Prerequisites

- [Claude Code](https://claude.ai/code) installed
- A [SearchAtlas](https://searchatlas.com) account

## Manual MCP Setup

If you prefer to add the MCP server manually:

```bash
claude mcp add searchatlas --type http https://mcp.searchatlas.com/mcp
```

See [docs/MCP_SETUP.md](docs/MCP_SETUP.md) for full details and troubleshooting.

## Verify Setup

```bash
bash scripts/verify-setup.sh
```

## Documentation

- [MCP Setup Guide](docs/MCP_SETUP.md) — Connect to the SearchAtlas MCP
- [Tool Reference](docs/TOOL_REFERENCE.md) — Tool groups and operations
- [Golden Rules](docs/GOLDEN_RULES.md) — Best practices for reliable tool usage
- [Workflows Guide](docs/WORKFLOWS.md) — How workflow templates work
- [Intent Mapping](docs/INTENT_MAPPING.md) — Keyword-to-tool routing reference
- [Setup Guide (printable)](docs/Agentic-Marketing-Mastermind-Setup-Guide.html)

## Updating

```bash
git pull origin main
bash setup.sh
```

## License

MIT — see [LICENSE](LICENSE)
