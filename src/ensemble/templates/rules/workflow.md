# Workflow Rules

## Atomic Operations
Multi-step workflows (commit/push, branch operations) must confirm each step
before proceeding. If a session may end unexpectedly, prioritize atomic operations.

### Recommended Flow
```
Make changes -> Run tests -> Confirm -> Commit -> Confirm -> Push -> Next task
```

## Debugging Protocol

When an error is shared, follow these steps BEFORE proposing a fix:

1. **Identify from stack trace**: Find exact file and line number
2. **Read the file**: Check error location and surrounding code
3. **Check dependencies**: Read imports, callers, related files
4. **Explain root cause**: Why this error occurred
5. **Propose fix**: Fix the root cause, not symptoms

## Compaction Recovery Protocol

After compaction, ALWAYS execute before resuming work:

1. Check your pane name: `tmux display-message -p '#W'`
2. Re-read your agent definition
3. Check current task in dashboard: `cat status/dashboard.md`
