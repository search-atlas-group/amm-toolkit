# /setup-integrations

Interactive wizard to connect your existing tools to Claude Code. Run this once and Claude will configure each integration automatically — you just answer questions and click through OAuth flows.

---

## Instructions for Claude

You are running an interactive integration setup wizard. Follow every step exactly. Do not skip steps. Do not summarize or compress the flow — go one integration at a time so the member isn't overwhelmed.

### Phase 1 — Discovery

Start by showing this menu and asking which tools they use:

---

**Which of these tools are you already using?** Reply with the numbers, names, or "all". You can also say "skip" to exit.

**CRM**
1. HubSpot — contacts, deals, pipeline

**Task Management**
2. ClickUp — tasks, lists, time tracking
3. Linear — issues, projects, cycles
4. Notion — docs, databases, knowledge base

**Communication**
5. Slack — messages, channels

**Email & Calendar**
6. Gmail — read/send email *(may need IT approval if on Google Workspace)*
7. Google Calendar — events, availability
   *(note: if you pick both Gmail and Calendar, it's one setup)*

**Development**
8. GitHub — repos, issues, PRs

---

Wait for their response. Confirm what you heard: *"Got it — setting up: [list]. Let's go one by one."*

If they mention a tool not on the list, acknowledge it and tell them: *"I don't have a setup recipe for [tool] yet — I'll skip it and we can add it manually after. Continuing with the rest."*

---

### Phase 2 — Setup (one at a time)

For each selected integration, follow the exact steps below. Complete one fully before moving to the next.

---

#### HubSpot

**What this connects:** Contacts, companies, deals, pipeline, tickets.

1. Tell the member: *"Setting up HubSpot. This uses the official HubSpot CLI — it takes about 2 minutes."*

2. Check if HubSpot CLI is installed:
   ```bash
   hs --version
   ```
   - If missing or below v8.2.0: run `npm install -g @hubspot/cli`
   - Wait for install to complete

3. Run the HubSpot MCP setup:
   ```bash
   hs mcp setup
   ```
   - When prompted to select a client, choose **Claude Code**
   - When asked about standalone mode, enter `y`

4. Verify: run `/mcp` in Claude Code and confirm **HubSpotDev** appears.

5. Tell the member: *"HubSpot connected ✅. You can now ask me things like 'show my open deals' or 'find contact [name]'."*

---

#### ClickUp

**What this connects:** Tasks, lists, spaces, folders, docs, time tracking (177 tools).

1. Tell the member: *"Setting up ClickUp. I'll need your API token — takes 1 minute."*

2. Ask: *"Go to ClickUp → Settings (bottom-left avatar) → Apps → Generate API Token. Paste it here when ready."*

3. Wait for the token. Store it in `.env`:
   ```bash
   echo "CLICKUP_API_TOKEN=<their_token>" >> .env
   chmod 600 .env
   ```

4. Add the MCP:
   ```bash
   claude mcp add clickup -e CLICKUP_API_TOKEN=<their_token> -- npx -y @chykalophia/clickup-mcp-server
   ```

5. Verify: ask Claude to "list my ClickUp spaces" — if it returns data, it's working.

6. Tell the member: *"ClickUp connected ✅. You can now ask me to create tasks, update status, query lists, and more."*

---

#### Linear

**What this connects:** Issues, projects, cycles, teams, roadmaps.

1. Tell the member: *"Setting up Linear. This uses OAuth — you'll just authorize in your browser."*

2. Add the MCP:
   ```bash
   claude mcp add linear --type http https://mcp.linear.app/sse
   ```

3. Tell the member: *"Done. Next time you ask me anything about Linear, it'll prompt you to authorize in the browser — just click Allow."*

4. Test now: ask Claude to "list my Linear teams" — it will trigger the OAuth prompt. Tell them to complete it.

5. Tell the member: *"Linear connected ✅. You can now ask me to show issues, create tasks, check cycle status, and more."*

---

#### Notion

**What this connects:** Pages, databases, workspace search.

1. Tell the member: *"Setting up Notion. I'll need an integration token — takes 2 minutes."*

2. Ask: *"Go to notion.so/my-integrations → click '+ New integration' → give it a name like 'Claude' → copy the Internal Integration Token. Then open any Notion page you want Claude to access → click ··· (top right) → Connections → add your integration. Paste the token here when ready."*

3. Wait for token. Store and add MCP:
   ```bash
   echo "NOTION_API_KEY=<their_token>" >> .env
   chmod 600 .env
   claude mcp add notion -e NOTION_API_KEY=<their_token> -- npx -y @modelcontextprotocol/server-notion
   ```

4. Verify: ask Claude to "search my Notion workspace for [anything]".

5. Tell the member: *"Notion connected ✅. Ask me to search, read, or update any page you've shared with the integration."*

---

#### Slack

**What this connects:** Channels, messages, search, posting.

1. Tell the member: *"Setting up Slack. You'll create a Slack app — takes about 3 minutes."*

2. Walk them through creating the bot:
   *"Go to api.slack.com/apps → Create New App → From scratch → name it 'Claude Assistant' → pick your workspace.*
   *Then: OAuth & Permissions → Bot Token Scopes → Add these scopes: `channels:read`, `channels:history`, `chat:write`, `search:read`.*
   *Then: Install to Workspace → Allow → copy the Bot User OAuth Token (starts with `xoxb-`)."*

3. Ask: *"Paste your Bot Token here."* Then ask: *"Now I need your Workspace ID. Open Slack in your browser — the URL shows /client/T0XXXXXXX. That T-code is it. Paste it here."*

4. Store and add MCP:
   ```bash
   echo "SLACK_BOT_TOKEN=<their_token>" >> .env
   echo "SLACK_TEAM_ID=<their_team_id>" >> .env
   chmod 600 .env
   claude mcp add slack \
     -e SLACK_BOT_TOKEN=<their_token> \
     -e SLACK_TEAM_ID=<their_team_id> \
     -- npx -y @modelcontextprotocol/server-slack
   ```

5. Verify: ask Claude to "list my Slack channels".

6. Tell the member: *"Slack connected ✅. You can now ask me to search messages, read threads, or post updates to channels."*

---

#### Gmail + Google Calendar

**What this connects:** Email threads, search, drafts (Gmail) + events and availability (Calendar).

> **Policy check first:** Before starting, ask — *"Is your Gmail a personal account (@gmail.com) or a company Google Workspace account?"*
> - **Personal Gmail:** Proceed normally.
> - **Google Workspace:** Warn them: *"Some Google Workspace orgs block external OAuth apps. If setup fails at the authorization step, your IT admin needs to allowlist the app — or you can use Outlook instead. Want to try anyway?"*
> - If they say no or mention it's definitely blocked: skip to the alternative below.

1. Tell the member: *"Setting up Gmail/Calendar. This requires a Google Cloud project — I'll walk you through each step. Takes about 5 minutes."*

2. Guide through Google Cloud setup:
   *"Go to console.cloud.google.com → Create a new project (name: 'Claude MCP') → APIs & Services → Enable APIs — search and enable: Gmail API, Google Calendar API → Credentials → Create OAuth 2.0 Client ID → Application type: Desktop app → Download the JSON → open it and find `client_id` and `client_secret`."*

3. Ask: *"Paste your client_id here."* Then: *"Paste your client_secret here."*

4. Get the refresh token:
   ```bash
   npx -y google-workspace-mcp-server auth
   ```
   *"This will open your browser — sign in with your Google account and click Allow. The terminal will print a refresh token — paste it here."*

5. Store all three and add MCP:
   ```bash
   echo "GOOGLE_CLIENT_ID=<client_id>" >> .env
   echo "GOOGLE_CLIENT_SECRET=<client_secret>" >> .env
   echo "GOOGLE_REFRESH_TOKEN=<refresh_token>" >> .env
   chmod 600 .env
   claude mcp add google-workspace \
     -e GOOGLE_CLIENT_ID=<client_id> \
     -e GOOGLE_CLIENT_SECRET=<client_secret> \
     -e GOOGLE_REFRESH_TOKEN=<refresh_token> \
     -- npx -y google-workspace-mcp-server
   ```

6. Verify Gmail: ask Claude to "search my Gmail for emails from this week".
   Verify Calendar: ask Claude to "what's on my calendar today?"

7. Tell the member: *"Gmail + Google Calendar connected ✅."*

**If Gmail is blocked by policy:** Tell the member — *"Since Gmail is blocked by your org's policy, here are your options: (1) Use Outlook — I can set that up instead if you have a Microsoft 365 account. (2) Forward important emails to a personal Gmail. (3) Copy-paste email content into our conversation when needed. Which works best?"*

---

#### GitHub

**What this connects:** Repos, issues, PRs, code search, file management.

1. Tell the member: *"Setting up GitHub. I'll need a Personal Access Token — takes 1 minute."*

2. Ask: *"Go to github.com → Settings (top-right avatar) → Developer settings → Personal access tokens → Tokens (classic) → Generate new token → set a name like 'Claude MCP' → select scopes: `repo`, `read:org` → Generate → copy the token. Paste it here."*

3. Store and add MCP:
   ```bash
   echo "GITHUB_PERSONAL_ACCESS_TOKEN=<their_token>" >> .env
   chmod 600 .env
   claude mcp add github \
     -e GITHUB_PERSONAL_ACCESS_TOKEN=<their_token> \
     -- npx -y @modelcontextprotocol/server-github
   ```

4. Verify: ask Claude to "list my GitHub repos".

5. Tell the member: *"GitHub connected ✅. You can now ask me to review PRs, create issues, search code, and more."*

---

### Phase 3 — Summary

After completing all selected integrations, show a summary:

```
✅ Setup complete! Here's what's connected:

[For each completed integration:]
  ✅  [Name] — [one-line description of what they can do]

[For each skipped/failed:]
  ⚠️  [Name] — [reason, what to do next]

To use your integrations, just ask naturally:
  "Show my open ClickUp tasks assigned to me"
  "Find emails from [client] this week"
  "What's on my calendar tomorrow?"
  "Create a GitHub issue for [description]"

To add more later, run /setup-integrations again.
To verify everything is working, run: bash scripts/verify-setup.sh
```

---

## Notes

- All API tokens are stored in `.env` (never committed — already in .gitignore)
- OAuth-based integrations (Linear) trigger auth on first use — no token to store
- If any step fails, tell the member exactly what went wrong and offer to retry or skip
- Never store tokens in anything other than `.env` or the MCP config env vars
