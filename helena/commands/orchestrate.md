---
description: Plan here, hand the coding to one cheaper worker at a time, tests before the diff
argument-hint: <task>
---

Task: $ARGUMENTS

You are the orchestrator for this task: you plan and judge, cheaper workers do the reading and the writing. Follow this
loop and nothing else.

1. **Small task: do it here.** If it takes about 5 tool calls or fewer, or one file you already know, skip the loop and
   say so in one line. A new worker costs more than the task.
2. **Plan, in at most 10 lines.** The steps in order, the files each one touches and the command that checks it. If you
   do not know where the code is, ask the `helena:scout` agent (Haiku, read-only) one question and plan from the paths
   it returns. Do not read files here just to find things. Write what you settled, why, and what you rejected under
   `## Decisions` in `HANDOFF.md` at the project root (create it if missing). Workers start cold; the rejected part is
   what stops the next one reopening it.
3. **One step, one `helena:builder`.** It runs on Sonnet and is the only one that writes. Give it the step, the files,
   what done means, the test command, and tell it to read `## Decisions` in `HANDOFF.md` first and not reopen what is
   there. Never two builders at once: they would edit the same tree.
4. **Judge the step from the diff.** The tests already ran before the builder could finish (Helena's done check). Read
   `git diff --stat`, then only the hunks you need. Do not re-read the files it touched.
5. **A step that failed gets one retry**, with a new builder told in one line what went wrong; add the failed approach to
   Decisions as rejected. If that fails too, do the step here. Never a third worker for the same step.
6. **End with** what was done per step, the test result and how many workers ran. `/helena:budget` shows what they cost.
