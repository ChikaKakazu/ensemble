# Infrastructure Reference

## tmux Session/Window Naming

| Item | Name | Description |
|------|------|-------------|
| Session 1 | `ensemble-conductor` | Conductor + Dashboard |
| Session 2 | `ensemble-workers` | Dispatch + Workers |
| Window | `main` | Both sessions |

## Pane Layout

**Session 1: ensemble-conductor**
```
+------------------+------------------+
|   Conductor      |   dashboard      |
|   (claude/opus)  |   (less +F)      |
|   60%            |   40%            |
+------------------+------------------+
```

**Session 2: ensemble-workers**
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
tmux send-keys -t ensemble-conductor:main.0 'message' Enter
```
