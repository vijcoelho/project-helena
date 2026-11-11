// PreCompact: what this prints becomes instructions for the summary that replaces the conversation. A summary keeps what
// to build and drops how to work, then spends its room on file contents that could be read again. This says what to keep
// and what to drop. start.js still brings the user's rules back word for word after it (source: compact): this is the
// first net, that one the second. No LLM, no state.
if (process.env.HELENA_DISTILLING) process.exit(0);
console.log(`Keep in the summary, in the user's own words where it is a rule:
- every rule the user gave on how to work: what not to touch, what to ask before doing, language, commit and branch rules
- decisions made and approaches rejected, each with its reason, so nobody reopens them
- files changed, as path:line, and what is still half done in each
- the command that checks the work and its last result (the failing test's name and message, if it failed)
- the next step, in one line
Leave out: file contents and command output (both can be read again), search results, and anything tried and undone.`);
