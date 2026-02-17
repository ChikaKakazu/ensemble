# Infrastructure Reference

## tmux Session/Window Naming

| Item | Name | Description |
|------|------|-------------|
| Session 1 | `{project-name}-conductor` | Conductor + Dashboard |
| Session 2 | `{project-name}-workers` | Dispatch + Workers |
| Window | `main` | Both sessions |

Note: Project name is derived from the current directory name (dots and colons replaced with hyphens).
Example: directory `my.project` → sessions `my-project-conductor` / `my-project-workers`
You can also specify explicitly with `ensemble launch --session NAME`.

## Pane Layout

**Session 1: {project-name}-conductor**
```
+------------------+------------------+
|   Conductor      |   dashboard      |
|   (claude/opus)  |   (less +F)      |
|   60%            |   40%            |
+------------------+------------------+
```

**Session 2: {project-name}-workers**
```
+------------------+------------------+
|   dispatch       |   worker-1       |
|   (claude/sonnet)|   (claude/sonnet)|
|                  +------------------+
|                  |   worker-2       |
|   60%            |   40%            |
+------------------+------------------+
```

## Pane ID Usage

```bash
# Correct: Use pane IDs from panes.env
source .ensemble/panes.env
tmux send-keys -t "$CONDUCTOR_PANE" 'message'
tmux send-keys -t "$CONDUCTOR_PANE" Enter

# Wrong: Do NOT use pane numbers directly
tmux send-keys -t {project-name}-conductor:main.0 'message' Enter
```
