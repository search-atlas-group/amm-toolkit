# Agent System Audit — Execution Playbook

You are the agent executing this. Your operator's agent system (orchestrator + PM/worker
fleet + memory) has degraded: bloated startup context, contradictory rules, dead
enforcement, unreliable memory retrieval. This document is the complete method, in
execution order. Follow the phases in sequence. Do not skip the read-only stage, do not
fix anything before the diagnosis is measured, and do not mark anything done until the
verification named in the changelog has run and its output was read.

Three standing rules for the whole run:

1. **Never fix a rule with another rule.** If a prose rule has been rewritten before and
   the problem persisted, the fix is mechanical (a hook, a test, a script) or deletion.
2. **Measure, then act.** Every finding carries a number from a command run this session.
   No opinions, no "probably".
3. **Read-only until Phase 4.** Diagnosis changes nothing.

## Phase 0 — Baseline (half a day)

Record these before touching anything, so the after-measurement means something:

| Metric | How to get it | Red flag |
|---|---|---|
| First-turn context tokens (median, p90) | Token-count your full startup load: rules, skill descriptions, tool names, memory index, hook output | Above ~50k, or growing week over week |
| Always-on rule prose size | Sum bytes of every file loaded every session | Above ~15KB |
| Visible skills / MCP tool names | Count what the harness actually exposes | Skills >150; any connector mounted twice |
| Agent dispatch payload | Size of everything one dispatch loads (definition + state file + fence) | Above ~100KB |
| Correction rate per user turn | Classify recent transcripts (Phase 3 method) | Above ~10% |
| Memory index freshness | Query the index; check the refresh job's last success | Any silent failure streak |

## Phase 1 — Parallel read-only audit (1 day)

Fan out parallel read-only auditors, one per layer. Each writes a report to a scratchpad
and changes nothing. Eleven lanes, each with its own hunting list:

| Auditor | Hunts for | Common errors to spot |
|---|---|---|
| **architecture** | What loads, runs, talks to what | Backups and stale copies still loaded (`.bak`, `-old`) ; duplicated subsystems |
| **context/startup** | Where first-turn tokens go | Connector mounted twice (doubles tool names); unauthenticated connector stubs still mounted; skill descriptions for skills never invoked; hooks emitting output every session for nothing |
| **rules** | The prose rule layer | Same rule living in 2+ layers, drifted apart; competing response formats; dead pointers to moved files; a rule that has been rewritten 3+ times while the problem got worse |
| **hooks** | Every hook registration | Wrong event name (output silently discarded, you pay the latency for nothing); malformed JSON the host drops; guards matching retired tool/server names so they never fire on the live path; substring matchers that block innocuous commands |
| **enforcement** | Every mechanism claimed to be mandatory | Prose "MUST" with no code behind it; a watchdog reporting green while jobs fail; launchd/scheduler jobs failing on permissions for weeks with nobody told |
| **fleet** | The worker agents | State files never rotated, so dispatch payload exceeds the read cap and the worker silently gets the oldest half; cron sweeps producing majority "no change" noise; duplicate agent definitions both alive |
| **memory** | The memo store | Bulk data (pickles, dumps, exports) living inside the memory tree; duplicate memos; memory split across 2+ stores that never see each other; the index loaded every session itself bloated past a few KB; per-project indexes auto-regenerated on a schedule to deliver almost nothing |
| **retrieval** | The search layer | See Phase 7 checklist |
| **sessions** | Transcript corpus | Which sessions run long and why; whether compaction is actually the cause (usually it is not) |
| **runtimes** | Every CLI profile in use | Parity drift: profiles pointing at different rules, models, or plugin sets |
| **connectors/MCP** | Every mounted integration | Stubs that never authenticated; the same server under two names |

Severity-rank every finding (SEV1 system-damaging / SEV2 costly / SEV3 cosmetic) with
the command that produced it.

## Phase 2 — Test the enforcement mechanisms (half a day)

The single highest-yield pass. List every mechanism anywhere that claims to be
mandatory: hooks, guards, linters, scheduled jobs, prose "MUST/required". For each one,
**attempt the thing it claims to prevent** and record whether it actually fired.

Expect to find 30–50% of them deliver nothing. Classify each failure: fixable in code
(now), fixable but blocked (queue for operator), or a prose claim that must be downgraded
to match reality. Never leave a "mandatory" label on something untested.

## Phase 3 — Classify your own transcripts (1 day)

Take the last ~60 days of sessions with human turns. Classify every user turn into this
taxonomy (it transfers; use it as-is):

- wrong-assumption · did-not-verify-before-claiming · misread-instruction ·
  scope-drift · format/length · tool-or-permission-friction · slow-or-long-loop ·
  context-loss-intra-session · asked-permission-unnecessarily · re-asked-known-info ·
  validation-opener

What this tells you, and what it almost always tells you:

- Most corrections are the agent producing the wrong *thing* (wrong assumption,
  claimed-done-without-checking), not format complaints. Format rules get rewritten
  hardest because they are the most visible, not the most costly.
- Compaction is usually a red herring. The dominant loss mode is intra-session: the
  agent forgets a constraint stated 40 turns earlier, rebuilds, the user re-states it.
  Count how many user turns were pure re-steering in your longest sessions.
- If a rule has been restated by the user multiple times, stop writing it down better:
  mechanize it or delete it.

## Phase 4 — Fix plan (operator decides scope)

One phase per layer, each with a changelog. Decision rules for every finding:

| Finding shape | Decision |
|---|---|
| Rule that fired 0 times, or that was rewritten repeatedly while friction rose | Delete it |
| Rule that matters but is prose-only | Convert to a hook, test, or script |
| Mechanism that half-works | Fix the mechanism, never patch around it with a new rule |
| Silent infrastructure failure | Fix the cause AND add loud failure: a status file and a notification after N consecutive failures |
| Unused skill/connector/stub | Remove from the load path; archive, do not delete, until the re-measure |
| Bulk data inside memory/config trees | Move to a gitignored local dir; audit git history for whether it ever leaked |

Fix order that works: safety items first (exposed credentials, data in pushed repos,
guards that never fire on the live send path), then context diet, then rule layer, then
retrieval, then fleet, then runtime parity.

## Phase 5 — Execute fixes with changelogs

Every phase produces a changelog: what changed, why, and the **verification command with
its actual output**. No changelog entry without a run verification. Where fixes are
mechanical, write tests; run the full suite after each phase.

## Phase 6 — Red-team your own claims (half a day)

Dispatch a separate adversarial agent (see routing below) with one instruction: for every
"done / verified / fixed" claim in the reports and changelogs, find the cheapest test
that would falsify it, and run it. Publish every finding with the command and output. It
will find false claims; that is the point. Re-run the full test suite after its fixes.

## Phase 7 — The search/memory layer

The memory store is useless if agents cannot query it, and the failure modes here are
almost always the same set. Build on a local index engine (we use `qmd`,
`npm install -g @tobilu/qmd`: BM25 + local vector search, offline, no API cost) and check
every one of these:

| Common error | How to spot it |
|---|---|
| Refresh job failing silently for weeks | Check the scheduler job's last-success timestamp, not its last-run; add a status file and a notification after 3 consecutive failures |
| Scheduler cannot reach the binary | Binary installed under a user Desktop/Documents path the scheduler has no permission to read (macOS TCC). Install off the restricted path |
| Vector search dead with no error | Native model binaries were never built: an npm postinstall was skipped. Reinstall allowing native scripts; no code change needed |
| Index stale | Run the update; compare file count before/after |
| Nothing tells agents to search | Write ONE skill file ("search the brain before concluding it is silent, and before re-asking the operator something the system may already know") and fan it to every runtime in use |
| Memory split across stores | Export the secondary store into the same index as a second collection, so one query covers both |
| Query phrasing failures | BM25 rewards 2–3 distinctive terms and is diluted by full sentences. Encode this in the skill |
| Mode misuse | Start with BM25 (~120ms); escalate to vector (~4s) only when BM25 is thin; avoid hybrid+rerank interactively (13s to timeout) |
| Graph-based retrieval | Evaluate before adopting: if its no-LLM output is clusters literally named "Community 0" and its useful mode needs a full LLM pass over every file, retire it. Keyword + vector covers the need |

The store itself needs the same diet as the index. Two more checks, both high-yield:

| Common error | How to spot it | The fix |
|---|---|---|
| The memory index loaded every session is itself a context cost | Measure its bytes; count entries that carry full descriptions where a name would do | Rebuild to a few dozen one-line pointers; when over budget drop descriptions, never the hooks that make entries findable |
| Auto-regenerated per-project indexes | Look for index files rebuilt on a timer (every few minutes) that each deliver one or two memos | Retire them; one global searchable index replaces the whole regeneration apparatus |
| Memo sprawl | Cluster near-identical memos by title; count memos never cited | One durable fact per memo; merge duplicates; archive stale ones with a status flag rather than deleting |

## Routing — which model does which pass

A gear is a job class, not a vendor. Cheap bulk goes to cheap lanes; judgment stays on
the strong models; and transcript classification deliberately runs on a **different
model family than the one being audited**, so the family under audit is not grading
itself. The spread we route through:

| Job | Gear | Model | Provider |
|---|---|---|---|
| Orchestrating the whole audit | Nodens (orchestrate) | Opus, medium | Anthropic |
| Synthesis passes (fuse many reports into one read) | Yog-Sothoth | Opus, high | Anthropic |
| Red-team re-audit (Phase 6) | Nyarlathotep | Opus, high | Anthropic |
| Fast recon across many files | Ithaqua | Sonnet, high | Anthropic |
| Standard build/implementation | Dagon | Sonnet, medium | Anthropic |
| Bulk mechanical grind | Shoggoth | Haiku, low | Anthropic |
| Transcript classification, bulk chunks | Mi-Go | GLM 5.x | z.ai |
| Transcript classification, small chunks | Nug | gpt-5.4-mini | OpenAI |
| Transcript classification, long-context chunks | Ubbo-Sathla | k3-256k | Moonshot |
| Independent second opinion / coding review | Atlach-Nacha / Eihort | kimi-for-coding / gpt-5.5 | Moonshot / OpenAI |

Dispatch these as parallel headless one-shots; it is safe to run several at once and it
is the reason a one-day phase takes one day.

## Phase 8 — Re-measure and close

Re-run every Phase 0 metric. The audit is closed when: each metric meets its target, the
full test suite passes, the red-team pass finds no SEV1, and every remaining prose
"mandatory" either has a working mechanism behind it or no longer says mandatory. Keep
the per-phase changelogs; they are the evidence trail and the template for the next audit.

## The short version, if context is tight

1. Measure the startup load and correction rate (Phase 0 table).
2. Fan out read-only auditors per layer with the common-error lists above.
3. Test every claimed enforcement mechanism by attempting what it forbids.
4. Classify transcripts on a different model family; taxonomy as given.
5. Fix in phases with changelogs: safety, context, rules, retrieval, fleet, runtimes.
6. Mechanize or delete repeated prose rules; never write a new one.
7. Make every silent failure loud.
8. Red-team every "done" claim; re-measure; close.
