# SearchAtlas Toolkit — Marketplace Submission Guide

> Two paths to discoverability for `searchatlas`. Path 1 (community) is concrete and can ship in days. Path 2 (official) is relationship-driven and runs in parallel.

---

## Pre-Submission Checklist (both paths)

Both marketplace paths require the plugin to already exist as a working public repo. Confirm these are true before submitting anywhere:

- [ ] `feature/plugin-conversion` merged into `main`
- [ ] `v1.0.0` tagged and pushed to GitHub
- [ ] `github.com/search-atlas-group/amm-toolkit` is public
- [ ] README's quickstart commands work end-to-end:
  ```
  /plugin marketplace add search-atlas-group/amm-toolkit
  /plugin install searchatlas
  ```
- [ ] At least one `sa-*` command runs successfully against the real MCP after OAuth
- [ ] `CHANGELOG.md` v1.0.0 entry matches what shipped
- [ ] `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` validate against `tests/plugin-manifest.test.sh`

---

## Path 1: Community Marketplace (Immediate)

### How it works

- **Submission portal:** [clau.de/plugin-directory-submission](https://clau.de/plugin-directory-submission)
- **Not a GitHub PR.** PRs against `anthropics/claude-plugins-community` are auto-closed. All changes flow through Anthropic's internal pipeline.
- After submission:
  1. Automated security + schema scanning
  2. Manual approval at Anthropic's discretion
  3. Nightly sync to the community marketplace
- Approved plugins appear when users add the community marketplace and browse the `/plugin → Discover` tab.

### Form field values (copy-paste ready)

| Field | Value |
|---|---|
| **Plugin name** | `searchatlas` |
| **Repository URL** | `https://github.com/search-atlas-group/amm-toolkit` |
| **Short description** | Official SearchAtlas toolkit — SEO, GBP, PPC, content, and AI visibility workflows. |
| **Long description** | Official SearchAtlas command-line toolkit. 21 slash commands covering the full SearchAtlas surface: SEO audits, Google Business Profile optimization, Google Ads campaign management, content generation via Content Genius, press release distribution, AI visibility tracking across ChatGPT/Claude/Gemini/Perplexity, and more. For anyone using SearchAtlas to manage SEO and digital marketing — solo operators, in-house teams, and agencies alike. Powered by the SearchAtlas MCP, which is auto-registered when the plugin installs (no separate setup). |
| **Category** | Integrations (best fit if a single category is required; ask Anthropic about a Marketing/SEO category if asked) |
| **Author** | SearchAtlas |
| **Author URL** | `https://searchatlas.com` |
| **License** | MIT |
| **MCP endpoint** | `https://mcp.searchatlas.com/mcp` |
| **MCP auth model** | OAuth 2.1 (SearchAtlas account) |
| **Contact email** | _(the SearchAtlas team member who owns plugin support)_ |
| **Tags / keywords** | seo, gbp, ppc, content, ai-visibility, llm-visibility, marketing, searchatlas, mcp |

### After you submit

- Anthropic runs automated validation on the manifest and MCP endpoint
- If something fails validation, expect an email with specifics — fix in the repo, resubmit
- Typical approval time is **not published** but community signal suggests 1–2 weeks
- Once approved, you'll be visible to anyone who has added the `claude-plugins-community` marketplace

### Common rejection reasons (preempt)

- MCP endpoint unreachable from Anthropic's validators → confirm `mcp.searchatlas.com` is publicly reachable, returns valid JSON-RPC 2.0 responses
- Plugin manifest missing required fields → our `tests/plugin-manifest.test.sh` catches this; run it before submitting
- Name collision → unlikely (`searchatlas` is specific), but verify by browsing the existing community marketplace before submitting
- Security concerns about the MCP (e.g., asks for excessive scopes) → SearchAtlas's OAuth scope should be documented at submission time

---

## Path 2: Official Marketplace (Partnership Track)

### How it works

- **No public submission process.** Inclusion is at Anthropic's discretion.
- Existing official-marketplace partners: Vercel, Figma, GitHub, Linear, Stripe, Firebase, Supabase, Atlassian, Asana, Notion, Slack, Sentry.
- These are all **relationship-based**, not application-driven.
- Inclusion means every fresh Claude Code user sees SearchAtlas Toolkit in their Discover tab by default — significantly larger distribution than the community path.

### What you're pitching

A category Anthropic's official marketplace doesn't have a partner for yet: **integrated marketing / SEO / AI visibility platform.**

Use this comparable analysis to anchor the conversation:

| Existing partner | Category | What they bring |
|---|---|---|
| Vercel | Infrastructure | Deployment, edge, AI gateway |
| Stripe | Payments | Billing/payments API |
| Figma | Design | Design-to-code, component sync |
| Linear | Project mgmt | Task orchestration |
| GitHub | Source control | Code, PRs, issues |
| Sentry | Observability | Error tracking |

**SearchAtlas slots into:** marketing infrastructure / SEO / AI visibility — adjacent to Vercel but for the marketing layer, comparable depth and audience overlap with developer-adjacent product/marketing teams using Claude Code.

### Outreach package

#### Contact paths (in order of preference)

1. **Any direct Anthropic contact you have** — the partnership pipeline is relationship-driven; a warm intro beats cold outreach by orders of magnitude
2. **[Anthropic partner portal](https://partnerportal.anthropic.com/s/partner-registration)** — primary public path, though it's framed for broader commercial partnerships
3. **Cold outreach via LinkedIn** to Anthropic Claude Code product or partnerships team
4. **partners@anthropic.com** as a last resort (not officially documented but a reasonable best-effort address)

#### Email template (drop-in)

> Subject: SearchAtlas Toolkit — Claude Code plugin partnership inquiry
>
> Hi [name],
>
> SearchAtlas published `searchatlas` to the Claude Code plugin marketplace [date]. We've seen [X installs / Y MCP calls / Z active users] in [period], and the response from agencies and in-house SEO teams using Claude Code has been strong.
>
> We'd love to discuss inclusion in `claude-plugins-official` as a verified partner alongside Vercel, Figma, Stripe, and others. A few reasons we'd fit:
>
> 1. **Category gap.** Your official marketplace has infra (Vercel), payments (Stripe), design (Figma), source (GitHub), but no SEO/marketing/AI-visibility partner. SearchAtlas is the established player here, and AI-assisted marketing workflows are growing fastest among Claude Code's product-builder audience.
>
> 2. **MCP depth.** Our MCP exposes 200+ tools across SEO audits, Google Business Profile, Google Ads, content generation (Content Genius), press distribution, AI visibility tracking (mentions across ChatGPT/Claude/Gemini/Perplexity), local SEO heatmaps, and more. Not a thin API wrapper — it's the actual SearchAtlas platform driven through MCP.
>
> 3. **Audience overlap.** Solo operators, in-house teams, and agencies all use Claude Code today. SearchAtlas serves all three.
>
> 4. **Active maintenance.** v1.0.0 shipped [date]; we have a dedicated team for plugin support and ongoing development.
>
> Happy to share usage data, walk through the integration, and discuss what verified partner status would require from us. [Your availability].
>
> [signature]

#### Adoption metrics to prepare

Anthropic will likely ask for these; have them ready before the first conversation:

- [ ] **Install count** since launch (from community marketplace stats, GitHub stars, or your own telemetry if added)
- [ ] **Active user count** (unique MCP-authenticated users in the last 30 days)
- [ ] **MCP call volume** (calls/month — proves real usage, not just installs)
- [ ] **Customer testimonials** — short quotes from agency or in-house SEO users who use SearchAtlas via Claude Code
- [ ] **Retention proxy** — what % of installers are still using the plugin 30 days later, if you can measure it
- [ ] **Geographic spread** (where are users? signals platform legitimacy)
- [ ] **Maintenance cadence** — release frequency, response time on issues

#### Technical brief to attach

A short technical doc for Anthropic to evaluate:

- MCP endpoint architecture (production stability, uptime SLA if any)
- Auth model (OAuth 2.1 — what scopes are requested, how revocation works)
- Rate limits (per-user, per-org)
- Tool catalog summary (what 200+ tools roughly cover)
- Security posture (how SearchAtlas handles user data, where it's stored, compliance status)
- Plugin update cadence and how the plugin handles MCP-side breaking changes

A 2-page PDF or a single web page is enough. Don't over-engineer it.

### Realistic timing

- **Cold path** (no warm intro): 4-8 weeks from first email to a yes/no, often longer
- **Warm path** (intro through existing Anthropic relationships): 2-4 weeks
- Anthropic publishes no SLA; pace depends on their partnership pipeline at the time

If no response within 2 weeks, follow up via a different contact rather than re-mailing the same address.

---

## What to do first (recommended sequence)

1. **Now (after Phase 10 user-gate completes):**
   - Push `feature/plugin-conversion` → merge to main → tag v1.0.0
   - Submit to community marketplace via the portal

2. **In parallel:**
   - Start collecting adoption metrics
   - Identify the warmest Anthropic contact you have
   - Draft the partnership pitch email (use the template above)

3. **Once community listing is live (2-4 weeks):**
   - Use real adoption numbers to fill in the partnership pitch
   - Reach out to Anthropic with the email + technical brief attached

4. **Optional intermediate step:**
   - Announce community-marketplace availability publicly (SearchAtlas blog, X, LinkedIn, customer email)
   - The public momentum strengthens the official-marketplace pitch

---

## Sources

- Community marketplace submission: [clau.de/plugin-directory-submission](https://clau.de/plugin-directory-submission)
- Community marketplace mirror: [github.com/anthropics/claude-plugins-community](https://github.com/anthropics/claude-plugins-community)
- Official marketplace mirror: [github.com/anthropics/claude-plugins-official](https://github.com/anthropics/claude-plugins-official)
- Claude Code plugin docs: [code.claude.com/docs/en/discover-plugins](https://code.claude.com/docs/en/discover-plugins)
- Anthropic partner portal: [partnerportal.anthropic.com](https://partnerportal.anthropic.com)
