<p align="center">
  <img src="site/assets/img/helena.jpg" alt="Helena" width="280">
</p>

<h1 align="center">Helena</h1>

<p align="center">
  <b>The layer that checks, on top of Claude Code, Codex and any AI. It starts blank and learns how you work.</b><br>
  Memory that checks itself against the code, a switch to another AI that loses nothing,<br>
  hooks that stop "done" with failing tests, and a benchmark that proves what stays.
</p>

<p align="center">
  <a href="LICENSE"><img alt="MIT license" src="https://img.shields.io/badge/license-MIT-black"></a>
  <img alt="Claude Code plugin" src="https://img.shields.io/badge/Claude%20Code-plugin-black">
  <img alt="version" src="https://img.shields.io/badge/version-1.2.1-black">
</p>

---

## Why

I read every Claude Code session I had: 465 sessions across 15 projects. The pattern never changed. I corrected the AI,
it got it right, and the next session it forgot. I had about 60 skills installed and almost none were called at the right
time (63 skill calls against 6,310 Bash calls).

Having a skill is not enough. It has to show up when the request needs it, and stay out when it does not, because every
token in the context is re-read on every message. Helena is the fix:

```
Observe   mine.py              what you repeat and what you correct (reads ~/.claude/projects, masks secrets)
Remember  Obsidian vault       one note per fact; loaded when a session starts, written by itself when it ends
Load      kits + library       skills stay out of context until a request needs them
Prove     eval/run.py          every task runs with and without Helena; a skill only stays if it wins
```

## Contents

- [She arrives empty](#she-arrives-empty)
- [Requirements](#requirements)
- [Install](#install)
- [Other AIs](#other-ais)
- [Your first day](#your-first-day)
- [Commands](#commands)
- [What she does on her own](#what-she-does-on-her-own)
- [She checks the work](#she-checks-the-work)
- [Token savings](#token-savings)
- [Configuration](#configuration)
- [Where your Helena lives](#where-your-helena-lives)
- [How it is built](#how-it-is-built)
- [Benchmark](#benchmark)
- [Privacy](#privacy)
- [Update and uninstall](#update-and-uninstall)
- [FAQ](#faq)
- [For teams](#for-teams)
- [License](#license)

## She arrives empty

A fresh install knows nothing about you: no memories, no kits, an empty library. What ships is the machinery:

- **Hooks that always run**: handoff on session start, secret and git guard before every commit and push, context
  trimming, readability check on front-end work, memory distillation every 6 prompts and when a session ends.
- **Three skills that are just knowledge**: `handoff`, `readability`, `library`.
- **Commands** to teach her by hand and to watch what she does.

Everything she learns lives in **your** folders, never inside the plugin, so updates never wipe it. The more you use her,
the better she gets: corrections become memory notes, repeated procedures become skill candidates, and candidates only
become skills after they beat the baseline.

| When | What you get |
|---|---|
| Day 1 | 0 memories, or a head start from your past sessions with `/helena:setup`. The hooks already protect you: API keys stay out of git, unreadable text goes back for a fix, where you stopped lives in `HANDOFF.md`. |
| Week 1 | Your corrections become notes in your vault. The next session starts already knowing. |
| Month 1 | Kits shaped like your work: the right skill comes in when a request needs it and stays out when it does not. |
| Always | A skill candidate only gets in if it wins the benchmark. Ties go out, because context costs. |

## Requirements

- [Claude Code](https://claude.com/claude-code), logged in (Helena's background work uses your own `claude` CLI on Haiku,
  no API key needed). The in-terminal band and `/painel` need Claude Code 2.1.287 or newer; older versions fall back to
  the status line.
- Node.js 18+ (hooks)
- Python 3.10+ (distillation, worker, library, benchmark)
- Edge or Chrome installed (the contrast checker drives it through `playwright-core`; no browser download)
- [Obsidian](https://obsidian.md) is optional. The memory is plain Markdown in a folder; Obsidian just makes it nice to browse.

Works on Windows, macOS and Linux.

## Install

```bash
git clone https://github.com/vijcoelho/project-helena.git
cd project-helena/helena/tools && npm install && cd ../../..   # contrast checker
claude plugin marketplace add ./project-helena
claude plugin install helena@helena
```

Optional, but recommended:

```bash
# where your memory lives (default: ~/Helena). Point it at your Obsidian vault to browse it there.
mkdir -p ~/.helena && echo "/path/to/your/obsidian/vault" > ~/.helena/vault

# your kits: start from the example and shape it to your work
cp project-helena/helena/kits.example.json ~/.helena/kits.json
```

Status line (the context size, always visible). Helena copies the script to `~/.helena/statusline.js` on the first
session; then add this to `~/.claude/settings.json`:

```json
"statusLine": { "type": "command", "command": "node ~/.helena/statusline.js" }
```

Restart Claude Code. On the next session start you will see Helena's brief at the top.

## Other AIs

One memory, every model. Helena is not tied to Claude: the same vault and library work in Codex, Antigravity (Gemini),
Qwen Code, Kimi, Grok CLI and opencode (which runs any provider: Llama, DeepSeek, Grok, Kimi, Qwen...).

```bash
python project-helena/helena/connect.py            # connects every CLI it finds
python project-helena/helena/connect.py --remove   # undoes it
```

- **Codex** reads Claude Code plugins, so it gets the whole plugin (brief, kits, memory notes, guard) plus the MCP server.
  Its sessions are distilled into the same vault.
- **The others** get `helena/mcp.js`, a dependency-free MCP server with six tools: `helena_start` (session brief),
  `helena_context` (notes and kits for a request), `helena_skill` (a library skill), `helena_remember` (save a fact),
  `helena_limits` (every plan's usage and weekly pace) and `helena_rewind` (undo the last request).
  The "how to use Helena" block goes into their global instruction file (`GEMINI.md`, `QWEN.md`, opencode `AGENTS.md`).
- **Any other MCP client** (Cursor, Claude Desktop, Windsurf, LM Studio): paste the JSON `connect.py` prints.

Something you teach her in Codex shows up in Claude the next session, and the other way around.

**Out of limit? Keep going in another AI, without losing the thread.** Helena reads each plan's usage from disk (Claude
from the status line, Codex from its sessions; ChatGPT shares Codex's limit). At 80% she asks for `HANDOFF.md` and
`/clear`; at 95% she saves `HANDOFF.md` and hands you the command for the AI with room, ready to paste:
`codex "Read HANDOFF.md and continue from Next"`. The next AI does not just read the handoff, Helena **checks it against
the repo** first (files changed after it was written, commits since, files it names that are gone) and asks the AI to
restate the next step in one line, so you see it picked up the right thing. She also watches the **weekly pace**: when the
week is going faster than it resets, she says when it runs out and how much a day lasts. `/helena:limits` shows every AI.

**One instruction file.** Codex reads `AGENTS.md`, Claude reads `CLAUDE.md`. Keep one: Helena hands it to the AI that does
not read it.

## Your first day

1. Run `/helena:setup` once. She asks where your Obsidian vault is and reads your last 10 project sessions (a few cents on
   Haiku), so she starts already knowing your corrections and preferences instead of empty.
2. Work as usual in any project.
3. Correct her when she gets something wrong ("no, we deploy with Docker", "never commit to main here").
   Every 6 prompts and when the session ends (4+ messages of yours), Haiku reads the new turns in the background and writes what is worth remembering.
   When a library skill was used and you corrected the result, the lesson is added under "## Learned" in that skill, so it gets better with use.
4. Say a git rule in chat ("don't commit videos in this repo") and she saves it to `<project>/.helena/git`. From then on
   the guard hook enforces it.
5. Before you stop, ask her to save where you stopped. `HANDOFF.md` is injected the next time you open that folder.
6. Run `/helena:status` the next day to see what she learned, or open `<vault>/Weekly/` for the week.

## Commands

| Command | What it does |
|---|---|
| `/helena:setup` | First day: point her at your vault and let her learn from your past sessions |
| `/helena:remember <fact>` | Teach her something right now (a rule, a preference, a project fact) |
| `/helena:forget <fact>` | Remove a memory that is wrong or outdated |
| `/helena:status` | What she has learned: memories, kits, library, skill candidates |
| `/helena:budget` | Where your tokens went this week (per day, per project, what filled the context), what each subagent cost by model and effort, and what Helena costs |
| `/helena:skills` | The skills she created on her own from your repeated requests, and how often each was used |
| `/helena:undo <skill>` | Delete a skill she created (she will not create it again) |
| `/helena:undo <skill> learned` | Remove the last lesson she added to a skill |
| `/helena:undo <skill> fold` | Restore a skill from before she folded its lessons into the recipe |
| `/helena:routines [what, how often]` | List routines, or add one in plain words ("every Monday check this project's dependencies"); `remove <name>`, `run <name>` |
| `/helena:rewind [n]` | Undo: the folder as it was before the last request (or n back). Run it again to undo the rewind |
| `/helena:limits` | Every AI plan's usage (5 hours and week) and whether the week lasts at this pace |
| `/helena:audit [days]` | What the hooks blocked or asked about; `--json` for a team's own log tools |
| `/helena:share <note>` | Copy one of your memory notes into the repo's `.helena/memory/`, reviewed like code |
| `/painel` | A pane with context by category and Helena's own spending (Claude Code 2.1.287+) |

Scripts you run from the repo:

```bash
python mine.py                              # what you repeat and what you correct, from your history
python library.py install <repo-or-folder>  # add third-party skills to the library (zero context until needed)
python library.py move <skill>              # take a skill out of ~/.claude/skills (always loaded) into the library
python library.py restore <skill>           # the opposite
python library.py catalog                   # rebuild ~/.helena/library/CATALOG.md
python helena/worker.py --now               # run the background work now
python helena/budget.py 7                   # token report for the last 7 days
python helena/scan.py <skill-folder>        # security scan of a skill (library.py install runs it; --trust to override)
python extras/measure_context.py            # how many tokens each enabled plugin adds to every message
```

## What she does on her own

- **Saves tokens.** Every message re-reads the whole context, so she keeps it small: a project brief from git at
  session start (no re-exploring the repo), the 2 memory notes that match the request delivered whole (no round trip to
  read them), lockfiles / build output / huge files / unbounded `git log` blocked before they flood the context, a
  warning by real context size (120k / 250k / 500k tokens) that asks for `HANDOFF.md` + `/clear`, and a hint when a broad
  search or a long-output command on Opus should go to a Haiku subagent (never `/model` mid-session: the switch re-reads
  the whole history uncached).
- **Turns off plugins a project never uses.** After 3 sessions in a folder, plugins with no use there are switched off in
  that project's `.claude/settings.local.json` (plugins with hooks are never touched). Ask for something that needs one
  ("let's add a payment gateway" → Stripe) and she turns it back on; it loads when the session restarts.
- **Creates skills from your repetition.** Requests that repeat 20+ times, or 5+ times across 2+ sessions, go to Haiku,
  which writes a skill only if there is a real procedure in them. New skills live in the library (zero context until a
  request needs them), you are told at the next session start with the command to delete it, and a skill nobody uses for
  30 days is removed.
- **Runs your routines.** A routine is a prompt with a schedule (`12h`, `1d`, `7d`) and a spending cap (default $0.10
  per run). Due ones run on Haiku when a session ends (no scheduler, nothing always on). They can only read files and
  the web; anything that needs a decision becomes a "needs you" line in `<vault>/Inbox/needs-you.md` and in the next
  session's brief, never acted on. Each run is logged in `<vault>/Routines/<name>.md`; a routine with a goal logs its
  progress in the project's hub note.
- **Keeps a hub note per project** in `<vault>/Projects/`: what it is like now, and a log of decisions and commits.
- **Tidies her memory.** When notes changed, Haiku looks for duplicates and contradictions and merges them into one note
  (the newer fact wins). The old versions go to `<vault>/Archive/`; notes that look outdated are only flagged to you.
- **Skills that tidy themselves.** When a skill collects 5 lessons under "## Learned", Haiku folds them into the recipe
  so the skill stays short. The previous version stays as `SKILL.md.bak` (`/helena:undo <skill> fold`).
- **Writes a weekly review** in `<vault>/Weekly/<year>-W<week>.md`, no LLM: notes new or changed, skills created,
  lessons learned, open "needs you" items, and what she cost.

All background work runs in `helena/worker.py`, at most once every 20 hours (routines: whenever they are due), on Haiku, with its spending in
`~/.helena/ledger.jsonl` so `/helena:budget` can show what she costs next to what she saves.

## She checks the work

The top complaint about AI code is "almost right, but not quite" (66% of developers, Stack Overflow 2025). PR review bots
see it after it lands; these hooks stop it inside the agent's own loop, with no LLM and in any CLI that runs plugin hooks.

- **Memory that checks itself.** A note can name the code it depends on (`checks: src/db.js#connectPostgres`) or a date
  it stops holding (`until: 2026-12-31`). When the file or the name is gone, the note still shows up, marked
  **STALE** with the reason, so the AI checks the code before trusting it. A fact that replaces another
  (`supersedes:`, "we moved from Redis to Postgres") archives the old note instead of keeping both. Distillation fills
  these fields by itself.
- **No "done" with failing tests.** When a turn edited code, the Stop hook runs the project's tests (`npm test`, pytest,
  `cargo test`, `go test`, or the command in `.helena/test`) and sends the failure back once. The agent is told to fix the
  code, not the test, or to say plainly the failure was already there.
- **Tests are not weakened.** An edit that removes assertions from a test file or adds a skip asks you first.
- **Made-up packages are stopped.** `npm i` / `pip install` of a name that does not exist on the registry is denied (AIs
  invent package names; attackers register them). A package published days ago or barely downloaded asks first.
- **Secrets stay out of the context, not only out of git.** Reading a `.env` (Read, Grep, `cat`) is denied and the AI
  gets the key names, never the values.
- **Destructive commands ask first**, even when permissions would let them run: `DROP TABLE`, `DELETE` without `WHERE`,
  `rm -rf /`, `git push --force`, `git reset --hard`, `terraform destroy`, a production database URL.
- **Undo in any CLI.** Before each request she snapshots the folder (git, without touching your index or branch);
  `/helena:rewind` puts it back.
- **Outside text is data, not a request.** A fetched page, a search result or an MCP tool result that carries a line
  written for an AI ("ignore previous instructions", "do not tell the user", in English or Portuguese) is flagged right
  next to the result, and the attempt is logged. It flags and never blocks; fixed phrases only, so a reworded attack
  passes.
- **A redo is called out.** "Try again" / "that's not what I asked" leaves the failed attempt in context, re-read on
  every message. Before spending another one the AI says in one line what went wrong and what changes, and asks when
  the request still reads two ways.
- **A heavy instruction file has a price.** `CLAUDE.md` / `AGENTS.md` is re-read on every message; past ~3k tokens she
  says what it costs (once a week) and offers to move the sometimes-only rules to memory notes.

Every decision lands in `~/.helena/audit.jsonl` (`/helena:audit`).

## Token savings

Measured over 7 days and 3,030 messages: **243k tokens of context per message, only 39k of them fixed**. The rest is
history that grows with every message. So Helena cuts at both ends: skills stay in a library until a request needs them,
and sessions are kept short.

| | |
|---|---|
| **−11.9k** | fixed context tokens on every message, measured (39.7k → 27.8k), a 30% cut |
| **4+** | messages of yours per session before memory is distilled, on Haiku. Short sessions cost nothing |
| **4x** | cheaper background calls: Helena's own Haiku runs load no plugins, skills or MCP (~48k → ~12k tokens per distillation) |
| **0** | LLM calls in the secret and git hooks: regex and git, in milliseconds |
| **100 KB** | the cap: lockfiles, build output, huge files and unbounded `git log` are blocked before they reach the context |

The math that matters: every message re-reads the whole context, so ~15k fewer fixed tokens × 40 messages is ~600k
tokens no longer re-read in one session.

## Configuration

### Kits (`~/.helena/kits.json`)

A kit is a trigger regex and the skills it brings in. Nothing loads unless the request matches.

```json
{
  "web": {
    "trigger": "\\b(site|website|landing ?page|frontend|layout)\\b",
    "always": [],
    "skills": ["readability"],
    "on_demand": ["web-design-guidelines"]
  }
}
```

- `skills`: plugin skills to use when the kit matches.
- `always`: library skills whose `SKILL.md` she reads before coding.
- `on_demand`: library skills she may read if the request needs them (paths in `CATALOG.md`).

Names in `always` / `on_demand` must exist in `~/.helena/library/CATALOG.md`. Install them with `library.py install`.

### Git rules per project (`<project>/.helena/git`)

```
main: no
never: *.mp4 renders/ .env.production
```

`main: no` denies direct commits on `main`/`master` (merges and pushes stay free). `never:` takes globs like
`.gitignore`. The guard hook also denies API keys and `.env` files in anything about to be committed or pushed.

### Team policy (`<repo>/.helena/policy`) and tests (`<repo>/.helena/test`)

Versioned with the code, so a change to the rules goes through review like any other.

```
deny: terraform apply      # regex per line: AIs may not run it here
ask: kubectl               # AIs must get an OK first
mcp: github, helena        # the only MCP servers AIs may use in this repo
```

`.helena/test` holds the test command the done check runs (or `off`). Without it, Helena uses what the project has.
These are guardrails for the AI, not a sandbox: whoever owns the machine can turn hooks off.

### Environment variables

| Variable | Effect |
|---|---|
| `HELENA_VAULT` | Overrides the vault path from `~/.helena/vault` |
| `HELENA_EVAL` | Set by the benchmark: the session never distills into your vault |

## Where your Helena lives

| Path | What |
|---|---|
| `<vault>/Memory/` | one note per fact (`type`, `description` frontmatter). The index is injected at every session start |
| `<vault>/Inbox/` | skill candidates found by distillation, waiting for a benchmark |
| `<vault>/Projects/` | one hub note per project |
| `<vault>/Weekly/` | the weekly review |
| `<vault>/Archive/` | memory notes merged away by the tidy step (move one back to undo) |
| `<vault>/Routines/` | one log per routine; decisions they left you go to `Inbox/needs-you.md` |
| `~/.helena/routines.json` | your routines |
| `~/.helena/kits.json` | your kits |
| `~/.helena/library/` | skills that cost zero context until a kit asks for them (`CATALOG.md` is the index) |
| `~/.helena/eval/tasks/` | your own benchmark tasks (they can depend on your memory and kits) |
| `~/.helena/ledger.jsonl` | what Helena's background work cost |
| `<project>/HANDOFF.md` | where you stopped; injected at session start in that folder, checked against the repo |
| `<project>/.helena/git` | that project's git rules |
| `<project>/.helena/memory/` | the team's memory notes, committed with the code |
| `<project>/.helena/policy` · `.helena/test` | the team's rules for AIs · the done check's test command |
| `~/.helena/audit.jsonl` | every hook decision (`/helena:audit`) |
| `refs/helena/turns` | the undo snapshots, in each repo's reflog (never pushed) |

## How it is built

**Skills suggest, hooks enforce.** Whatever must always happen (no API keys in git, no commits to main, readable text)
is a hook and runs without asking. Skills are for knowledge: the recipe, the format, the path.

| Where | What |
|---|---|
| `helena/hooks/start.js` | SessionStart: git brief of the project, the folder's `HANDOFF.md` checked against the repo, the instruction file the AI does not read (and the cost of a heavy one), the memory index (yours + the team's, STALE marks), news, runs the worker if overdue |
| `helena/hooks/router.js` | UserPromptSubmit: matches the request against your kits and loads only those; injects matching memory notes; turns a git rule said in chat into `.helena/git`; re-enables a plugin a request needs; context, limit and weekly pace warnings; the redo note; the undo snapshot. Subagent reports and notifications are not treated as requests |
| `helena/hooks/memory.js` | memory notes from the vault and `.helena/memory/`, and their `checks:` / `until:` |
| `helena/hooks/guard.js` | PreToolUse: before `git commit`/`push`, denies API keys, `.env` files and anything that breaks `.helena/git` |
| `helena/hooks/gate.js` | PreToolUse: `.env` reads, made-up or brand-new packages, destructive commands, weakened tests, `.helena/policy` |
| `helena/hooks/outside.js` | PostToolUse (WebFetch, WebSearch, MCP): flags a line written for an AI in text that came from outside |
| `helena/hooks/trim.js` | PreToolUse: blocks lockfiles, build output, files over 100 KB and unbounded `git log` / recursive listings |
| `helena/hooks/check.js` | Stop: if the session touched front-end files, checks contrast on the `.html` and on live localhost URLs |
| `helena/hooks/done.js` | Stop: if this turn edited code, runs the tests and sends a failure back |
| `helena/hooks/limits.js` · `rewind.js` | plan usage and weekly pace (`/helena:limits`) · undo snapshots (`/helena:rewind`) |
| `helena/scan.py` · `helena/audit.py` | skill security scan · hook decision report |
| `helena/hooks/end.js` → `helena/distill.py` | SessionEnd (and every 6 prompts, from router.js): Haiku reads the new turns in the background and writes memory, skill candidates and "## Learned" lessons |
| `helena/hooks/mod.mjs` | Claude Code mod: band above the prompt with context, % of the window, session cost and what `trim.js` blocked; spinner warning from 120k; `/painel` |
| `helena/routines.py` | routines: runs the due ones read-only on Haiku with `--max-budget-usd`; log, "needs you", goal progress |
| `helena/worker.py` | background, once per 20h: plugin profiles, repeated requests → skills, Inbox candidates → skills, pruning, then `tidy.py` |
| `helena/tidy.py` | memory merge, folding lessons into skills, weekly review |
| `helena/budget.py` · `helena/skills.py` · `helena/history.py` | reports behind `/helena:budget`, `/helena:skills`, `/helena:undo`; transcript reader (no LLM) |
| `helena/statusline.js` | `helena · ctx 85k · Opus` |
| `helena/tools/contrast.mjs` | WCAG AA for every visible text, desktop and phone |
| `helena/skills/` | `handoff`, `readability`, `library` |
| `helena/commands/` | the `/helena:*` commands |
| `library.py` · `mine.py` | library manager · history miner |
| `eval/` | the benchmark and the hook tests |

## Benchmark

Every task runs as a full Claude Code session, once without Helena and once with her. A skill that does not win goes
back to the library.

```bash
python eval/run.py -n 1                  # everything (eval/tasks + ~/.helena/eval/tasks)
python eval/run.py git-rule -n 3         # one task, 3 rounds
python eval/promote.py                   # list skill candidates from the Inbox; pass a name to turn one into a task
python eval/test_guard.py                # guard hook, no Claude calls
python eval/test_trim.py                 # trim hook, no Claude calls
python eval/test_distill.py              # distillation remembers corrections, skips trivia, never stores secrets
python eval/test_learn.py                # checkpoint offsets and "## Learned" lines (no LLM)
python eval/test_routines.py             # routines: schedule, log, "needs you", goal progress (no LLM)
python eval/test_tidy.py                 # memory merge, folding lessons, weekly review (no LLM)
python eval/test_verify.py               # STALE notes, supersedes, handoff check, instruction file, redo (no LLM)
python eval/test_outside.py              # lines aimed at an AI in fetched pages and tool results (no LLM)
python eval/test_gate.py                 # .env, packages, destructive commands, tests, team policy, audit (no LLM)
python eval/test_rewind.py               # undo snapshots and the done check (no LLM)
python eval/test_limits.py               # limit warning, ready command, weekly pace (no LLM)
python eval/test_scan.py                 # skill security scan on install, registry (no LLM)
python eval/registry.py                  # site/registry.json: every piece, its context cost, scan and measured lift
```

Each run records its tokens and cost too; `eval/results.json` keeps the last result per task (pass rate per column,
tokens per run), and a task's `uses` file names the hook or skill it measures. `eval/registry.py` joins that with each
piece's context cost and security scan: a piece with no benchmark says so instead of claiming a win.

A task folder has `prompt.md`, `fixture/`, `check.py` (exit 0 = pass), and optionally `setup.py` (prepares the folder),
`prepare.py` (runs alongside the session) and `ab.json` (what differs between columns). Benchmark sessions never distill
into your vault and never go to history. Each round costs a real session, so start with `-n 1` and only add rounds when
the result is close.

The creator's scoreboard (Sonnet, without → with Helena):

| Task | Without | With | What stayed |
|---|---|---|---|
| per-project git rule | 1/5 | 5/5 | hook blocks commits to main and videos |
| save where I stopped | 0/2 | 2/2 | `handoff` skill |
| resume where I stopped | 1/2 | 2/2 | hook injects `HANDOFF.md` |
| hard-to-read text | 0/2 | 2/2 | contrast hook at the end |
| run locally | 2/2 | 2/2 | tie: skill removed |

Tests get it wrong too: every failure is inspected before it becomes a conclusion.

## Privacy

- Everything stays on your machine: your vault, `~/.helena`, your project folders. Nothing is sent anywhere except the
  Claude Code sessions you already run (and the Haiku calls Helena makes through your own `claude` CLI).
- Secrets are masked before anything is written to memory, and the distillation test checks that keys never reach it.
- The guard hook blocks API keys and `.env` files before they reach git, and the gate hook keeps `.env` values out of the
  AI's context in the first place.
- The only network call a hook makes is the package registry check (`registry.npmjs.org` downloads count, `pypi.org`),
  with the package name only, when the AI installs a package.

## Update and uninstall

```bash
cd project-helena && git pull
claude plugin marketplace update helena
claude plugin update helena@helena
```

```bash
claude plugin uninstall helena@helena
claude plugin marketplace remove helena
```

Your memory, kits and library stay in your folders; delete `~/.helena` and the vault folders yourself if you want them gone.

## FAQ

**Does she need an API key?** No. Background work runs through your logged-in `claude` CLI on Haiku.

**How much does she cost?** Distillation only runs on sessions with 4+ of your messages, and the worker at most once
every 20 hours, both on Haiku with nothing extra loaded (a few cents a call). Routines stop at their own cap. `/helena:budget` shows her spending next to what she saved.

**Do I need Obsidian?** No. The memory is a folder of Markdown notes. Obsidian is just a nice way to read and edit it.

**She learned something wrong.** `/helena:forget <fact>`, or delete the note in `<vault>/Memory/`.

**She created a skill I don't want.** `/helena:undo <skill>`. She will not create it again.

**Will an update wipe what she learned?** No. Nothing she learns lives inside the plugin folder.

## For teams

Free, Helena learns one person. In a team, the gain comes from everyone starting with the same rules, the same kits and
the same project memory, and from proving with numbers that it paid off. I set that up for companies:

What ships for teams, free:

- **Shared memory, reviewed like code.** Notes in `<repo>/.helena/memory/` load for everyone who opens the repo, in any
  AI. `/helena:share <note>` turns one of yours into a file for a pull request.
- **Policy as code.** `.helena/policy` says what AIs may run, what needs an OK and which MCP servers are allowed.
- **Audit log.** `~/.helena/audit.jsonl`, one line per decision; `/helena:audit --json` feeds your own log tools.

What I set up for companies:

- **Team rollout**: every machine configured, shared project memory in a team vault, status line and panel on.
- **Company rules as hooks**: protected branches, commit conventions, files that never go up, your stack's secrets.
- **Custom kits**: skills for your stack, security reviewed, loaded only when a request needs them.
- **Benchmark on your tasks**: your team's real work run with and without Helena, with the scoreboard.
- **Token report**: where the team spends context and what that is worth at the end of the month.
- **Training**: one session for the team on Claude Code with Helena.

Get in touch through [my GitHub profile](https://github.com/vijcoelho).

## Contributing

Issues and pull requests are welcome. Before a PR, run the tests that need no Claude calls:

```bash
python eval/test_guard.py && python eval/test_trim.py
```

A new behavior that must always happen should be a hook with a test. A new skill should come with a benchmark task that
shows it wins.

## License

[MIT](LICENSE) © Vitor Coelho
