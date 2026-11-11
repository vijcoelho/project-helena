---
description: Plan here, cheaper workers write (independent steps side by side in worktrees), tests before the diff
argument-hint: <task>
allowed-tools: Bash(node:*)
---

Task: $ARGUMENTS

You are the orchestrator for this task: you plan and judge, cheaper workers do the reading and the writing. Every token
you read or write here is paid again on each later message, at this session's price; a worker's is paid once, at its own.
Follow this loop and nothing else.

1. **Small task: do it here.** About 5 tool calls or fewer, or one file you already know: skip the loop and say so in one
   line. A new worker starts at ~34k tokens of its own; below that the task is cheaper here.
2. **Plan, in at most 12 lines.** Each step: what changes, the files it touches, what done means. If you do not know
   where the code is, ask the `helena:scout` agent (Haiku, read-only) one question and plan from the paths it returns;
   do not read files here just to find things. Write what you settled, why, and what you rejected under `## Decisions`
   in `HANDOFF.md` at the project root (create it if missing). A decision that changes mid-run keeps its line, marked
   `superseded by: <the new one>`; never delete it.
3. **Sort the steps into waves.** Two steps go in the same wave only when they share no file, neither needs the other's
   result, and none of their files has uncommitted changes (`git status --short -- <files>` prints nothing): a worktree
   starts from the last commit, so it does not see uncommitted work. Everything else runs one step at a time in this tree.
   One step, or any doubt: one at a time.
4. **Brief each `helena:builder` in under 10 lines:** the step, its files, what done means. Nothing else: Helena hands
   every worker the project's check command, `## Decisions` and the report format when it starts, so do not repeat them.
   - One at a time: one builder, in this tree, and wait for it.
   - A wave: its builders in ONE message (3 at most), each with `isolation: "worktree"` and only its own step.
5. **Land a wave with one command**, then check once here:
   !`node "${CLAUDE_PLUGIN_ROOT}/wave.js" --where`
   A `NOT LANDED` line means that builder's patch collided with this tree: its worktree is kept; redo that step here,
   one at a time, and remove the worktree after. Then run the project's check command in this tree once: a worktree
   without its dependencies installed cannot have run it.
6. **Judge from the diff, not from the files.** Helena's done check already ran the tests before a builder in this tree
   could finish. Read `git diff --stat`, then only the hunks you doubt. Do not re-read what a builder touched.
7. **A failed step climbs one rung at a time:** a new builder told in one line what went wrong, with `model: "opus"`
   when this session runs on a model above Opus (a cold Opus worker still costs less than this context), else the
   same builder again; add the failed approach to Decisions as rejected. If that fails too, do the step here. Never a
   third worker for the same step.
8. **Review a large change once, after the last wave has landed and the tests pass.** Large means more than 3 files or
   more than 150 changed lines (`git diff --stat` against the commit you started from). Smaller: skip it and say so in
   one line. Otherwise:
   - One fresh `general-purpose` worker (Helena pins it to a cheaper model), given only the task text and the diff,
     nothing from this conversation. It returns at most 5 findings, each as `path:line`, what breaks, how to reproduce
     it. No style remarks.
   - If there are findings, a second fresh worker gets the findings and the diff. Its only job is to prove each one
     wrong, by reading the code or running something, and to return `stands` or `refuted` with the evidence.
   - Fix only the findings that stand (a builder, same rules as the waves) or show them to the user. One round, no loop.
9. **End with** what was done per step, the check's result here and how many workers ran. `/helena:budget` shows what
   they cost.
