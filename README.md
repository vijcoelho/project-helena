<p align="center">
  <img src="site/assets/img/helena.jpg" alt="Helena" width="280">
</p>

<h1 align="center">Helena</h1>

<p align="center">
  <b>A layer on top of Claude Code that starts blank and learns how you work.</b><br>
  Memory that writes itself, skills that load only when a request needs them,<br>
  hooks for what must always happen, and a benchmark that decides what stays.
</p>

<p align="center">
  <a href="LICENSE"><img alt="MIT license" src="https://img.shields.io/badge/license-MIT-black"></a>
  <img alt="Claude Code plugin" src="https://img.shields.io/badge/Claude%20Code-plugin-black">
  <img alt="version" src="https://img.shields.io/badge/version-0.7.0-black">
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
- [Your first day](#your-first-day)
- [Commands](#commands)
- [What she does on her own](#what-she-does-on-her-own)
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
| Day 1 | 0 memories. The hooks already protect you: API keys stay out of git, unreadable text goes back for a fix, where you stopped lives in `HANDOFF.md`. |
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

## Your first day

1. Open Claude Code in any project and work as usual.
2. Correct her when she gets something wrong ("no, we deploy with Docker", "never commit to main here").
   Every 6 prompts and when the session ends (4+ messages of yours), Haiku reads the new turns in the background and writes what is worth remembering.
   When a library skill was used and you corrected the result, the lesson is added under "## Learned" in that skill, so it gets better with use.
3. Say a git rule in chat ("don't commit videos in this repo") and she saves it to `<project>/.helena/git`. From then on
   the guard hook enforces it.
4. Before you stop, ask her to save where you stopped. `HANDOFF.md` is injected the next time you open that folder.
5. Run `/helena:status` the next day to see what she learned.

## Commands

| Command | What it does |
|---|---|
| `/helena:remember <fact>` | Teach her something right now (a rule, a preference, a project fact) |
| `/helena:forget <fact>` | Remove a memory that is wrong or outdated |
| `/helena:status` | What she has learned: memories, kits, library, skill candidates |
| `/helena:budget` | Where your tokens went this week (per day, per project, what filled the context) and what Helena costs |
| `/helena:skills` | The skills she created on her own from your repeated requests, and how often each was used |
| `/helena:undo <skill>` | Delete a skill she created (she will not create it again) |
| `/helena:undo <skill> learned` | Remove the last lesson she added to a skill |
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
python extras/measure_context.py            # how many tokens each enabled plugin adds to every message
```

## What she does on her own

- **Saves tokens.** Every message re-reads the whole context, so she keeps it small: a project brief from git at
  session start (no re-exploring the repo), the 2 memory notes that match the request delivered whole (no round trip to
  read them), lockfiles / build output / huge files / unbounded `git log` blocked before they flood the context, a
  warning by real context size (120k / 250k / 500k tokens) that asks for `HANDOFF.md` + `/clear`, and a hint when Opus
  gets a routine request or a broad search should go to a Haiku subagent.
- **Turns off plugins a project never uses.** After 3 sessions in a folder, plugins with no use there are switched off in
  that project's `.claude/settings.local.json` (plugins with hooks are never touched). Ask for something that needs one
  ("let's add a payment gateway" → Stripe) and she turns it back on; it loads when the session restarts.
- **Creates skills from your repetition.** Requests that repeat 20+ times, or 5+ times across 2+ sessions, go to Haiku,
  which writes a skill only if there is a real procedure in them. New skills live in the library (zero context until a
  request needs them), you are told at the next session start with the command to delete it, and a skill nobody uses for
  30 days is removed.
- **Keeps a hub note per project** in `<vault>/Projects/`: what it is like now, and a log of decisions and commits.

All background work runs in `helena/worker.py`, at most once every 20 hours, on Haiku, with its spending in
`~/.helena/ledger.jsonl` so `/helena:budget` can show what she costs next to what she saves.

## Token savings

Measured over 7 days and 3,030 messages: **243k tokens of context per message, only 39k of them fixed**. The rest is
history that grows with every message. So Helena cuts at both ends: skills stay in a library until a request needs them,
and sessions are kept short.

| | |
|---|---|
| **−11.9k** | fixed context tokens on every message, measured (39.7k → 27.8k), a 30% cut |
| **4+** | messages of yours per session before memory is distilled, on Haiku. Short sessions cost nothing |
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
| `~/.helena/kits.json` | your kits |
| `~/.helena/library/` | skills that cost zero context until a kit asks for them (`CATALOG.md` is the index) |
| `~/.helena/eval/tasks/` | your own benchmark tasks (they can depend on your memory and kits) |
| `~/.helena/ledger.jsonl` | what Helena's background work cost |
| `<project>/HANDOFF.md` | where you stopped; injected at session start in that folder |
| `<project>/.helena/git` | that project's git rules |

## How it is built

**Skills suggest, hooks enforce.** Whatever must always happen (no API keys in git, no commits to main, readable text)
is a hook and runs without asking. Skills are for knowledge: the recipe, the format, the path.

| Where | What |
|---|---|
| `helena/hooks/start.js` | SessionStart: git brief of the project, the folder's `HANDOFF.md`, the memory index, news (new skills), runs the worker if overdue |
| `helena/hooks/router.js` | UserPromptSubmit: matches the request against your kits and loads only those; injects matching memory notes; turns a git rule said in chat into `.helena/git`; re-enables a plugin a request needs; context warnings |
| `helena/hooks/guard.js` | PreToolUse: before `git commit`/`push`, denies API keys, `.env` files and anything that breaks `.helena/git` |
| `helena/hooks/trim.js` | PreToolUse: blocks lockfiles, build output, files over 100 KB and unbounded `git log` / recursive listings |
| `helena/hooks/check.js` | Stop: if the session touched front-end files, checks contrast on the `.html` and on live localhost URLs |
| `helena/hooks/end.js` → `helena/distill.py` | SessionEnd (and every 6 prompts, from router.js): Haiku reads the new turns in the background and writes memory, skill candidates and "## Learned" lessons |
| `helena/hooks/mod.mjs` | Claude Code mod: band above the prompt with context, % of the window, session cost and what `trim.js` blocked; spinner warning from 120k; `/painel` |
| `helena/worker.py` | background, once per 20h: plugin profiles, repeated requests → skills, Inbox candidates → skills, pruning |
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
```

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
- The guard hook blocks API keys and `.env` files before they reach git.

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
every 20 hours, both on Haiku. `/helena:budget` shows her spending next to what she saved.

**Do I need Obsidian?** No. The memory is a folder of Markdown notes. Obsidian is just a nice way to read and edit it.

**She learned something wrong.** `/helena:forget <fact>`, or delete the note in `<vault>/Memory/`.

**She created a skill I don't want.** `/helena:undo <skill>`. She will not create it again.

**Will an update wipe what she learned?** No. Nothing she learns lives inside the plugin folder.

## For teams

Free, Helena learns one person. In a team, the gain comes from everyone starting with the same rules, the same kits and
the same project memory, and from proving with numbers that it paid off. I set that up for companies:

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
