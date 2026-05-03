# Feature Context — copilot-cli-python

> Fix 5 issues from code review: shell injection, zombie processes, deadlock, ambiguous edits, temp file leak

> **Auto-generated sections below — custom sections are preserved.**
> Add custom notes in the 'Custom Context' section at the bottom.

## Story Groups

### All Stories
- **US-001**: Mitigate shell injection in bash executor (priority 1)
- **US-002**: Kill subprocess on timeout and clean up temp files (priority 2)
- **US-003**: Read stdout and stderr concurrently to prevent deadlock (priority 3)
- **US-004**: Reject ambiguous multi-match file edits (priority 1)

## Schema Extensions

_No schema field references detected in acceptance criteria._

## Cross-Module Touch Points

_No cross-module touch points detected._

## Known Constraints

_No constraints defined in aes.json. Add a `constraints` list if needed._
