# Communication Protocol

## Basic Principles
- Agent communication via file-based queue (queue/)
- File creation followed by send-keys notification (primary)
- Polling as fallback when notification fails
- Exclusive locking (flock + atomic write) for concurrent writes

## Timeout Settings
- Dispatch: 3 min wait, then poll queue/reports/ (30s interval)
- Conductor: Wait for completion notification, or 30 min timeout

## No Vague Language Rule

Reports must use specific numbers, names, and locations.

| Forbidden | Use Instead |
|-----------|------------|
| many | 3 occurrences |
| some | src/api/auth.py lines 45-52 |
| approximately | 87% |
| several | 4 items |
| a while | 30 seconds |

**Required in all reports:**
- **Who**: Worker-1, Conductor, etc.
- **How many**: Specific numbers
- **Where**: file_path:line_number
