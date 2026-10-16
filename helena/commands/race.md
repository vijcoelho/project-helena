---
description: Two workers try two approaches in separate worktrees; the one whose tests pass wins
argument-hint: <task>
---

Task: $ARGUMENTS

You are the judge of a race: two cheaper workers each try one approach in their own git worktree, the tests pick the
winner, only the winner's change reaches this tree. Follow this loop and nothing else.

1. **Worth a race?** Only when the task has two real ways to do it (two designs, two places to fix it, a rewrite against
   a patch). One obvious way: say so in one line and use `/helena:orchestrate` instead; a race costs two workers.
2. **Two approaches, 3 lines each.** For each: the idea, the files, what done means. Name the test command (the one
   Helena's done check uses: `.helena/test`, else the project's usual one). Write both, and why each could win, under
   `## Decisions` in `HANDOFF.md` at the project root (create it if missing).
3. **Start both at once:** two `helena:builder` agents in the same message, each with `isolation: "worktree"`, each given
   its approach only (never the other one), the files, done, and the test command. Separate worktrees: this is the one
   place two builders may run together. Helena's done check (tests, hidden acceptance tests, differential check) runs
   in each before it can report.
4. **Judge by running, not by reading.** In each worktree the result names, run the test command yourself. The winner
   is the one that passes; both pass: the smaller `git diff --stat`; neither passes: no winner, say why from the two
   failures and stop.
5. **Bring the winner here:** in its worktree `git add -A` then `git diff --cached HEAD --binary > <scratch>/race.patch`;
   here `git apply <scratch>/race.patch`; run the test command here once. Then `git worktree remove --force` both
   worktrees and delete their branches. Add the losing approach to Decisions as rejected, with the reason.
6. **End with** which approach won and why, the test result here, and the diff stat. `/helena:budget` shows what the
   two workers cost.
