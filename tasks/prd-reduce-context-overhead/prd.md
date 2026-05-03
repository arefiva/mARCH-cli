# PRD: Reduce Agent Context Overhead

## 1. Introduction/Overview

Agents working on this project experience memory spikes due to excessive context overhead. Analysis of session `b5565b05-5eb0-4905-a4dc-9a70352bd9cb` showed:

- **~14KB** of COPILOT.md workflow instructions injected as user message prefix
- **~38KB** system message
- **Non-standard fields** in `aes.json` (`securityWarnings`, `memoryConstraints`) adding ~2KB that may be injected into context

Combined, this leaves minimal room for actual work before hitting memory limits.

With `.copilot/instructions.md` now in place (providing meta-project guardrails), we can remove the redundant inline warnings from AES files and streamline the mARCH orchestrator's context injection.

## 2. Goals

- ✅ Remove non-standard fields from AES files (`securityWarnings`, `memoryConstraints`)
- ✅ Ensure AES files conform to the schema (only standard fields)
- ✅ Reduce initial context overhead by at least 50%
- ✅ Agents still receive necessary guardrails via `.copilot/instructions.md`

## 3. User Stories

### US-001: Clean Up AES Files

**Description:** As a developer using mARCH, I want AES files to contain only standard schema fields so that context isn't bloated with redundant metadata.

**Implementation Notes:**
- Remove `securityWarnings` array from `scripts/march/aes.json` (lines 6-11)
- Remove `memoryConstraints` object from `scripts/march/aes.json` (lines 12-31)
- Verify remaining structure matches AES schema (project, branchName, description, _source, userStories)
- Run AES validation: `python .github/skills/aes/validate_aes.py`
- Check that `scripts/ralph/aes.json` also has no non-standard fields

**Acceptance Criteria:**
- [ ] `scripts/march/aes.json` contains only schema-defined fields
- [ ] No `securityWarnings` field present in any AES file
- [ ] No `memoryConstraints` field present in any AES file
- [ ] AES validation passes: `python .github/skills/aes/validate_aes.py` exits 0
- [ ] `ruff check` passes with no errors
- [ ] `pytest` passes with no failures

### US-002: Document Context Reduction Strategy

**Description:** As a developer, I want clear documentation of how agents receive guardrails so that future contributors don't re-add inline warnings.

**Implementation Notes:**
- Update `scripts/march/DECISIONS.md` to document the context reduction strategy
- Add section explaining that `.copilot/instructions.md` replaces inline warnings
- Note that AES files should not contain custom fields beyond schema
- Reference the memory spike analysis from session investigation

**Acceptance Criteria:**
- [ ] `scripts/march/DECISIONS.md` has section on context reduction
- [ ] Section explains `.copilot/instructions.md` replaces inline warnings
- [ ] Section warns against adding custom fields to AES files
- [ ] Document references the root cause analysis (meta-project confusion)
- [ ] `ruff check` passes with no errors
- [ ] `pytest` passes with no failures

## 4. Non-Goals (Out of Scope)

- Modifying mARCH orchestrator code (external to this repo)
- Changing how Copilot CLI injects system prompts (external)
- Adding new AES schema fields

## 5. Technical Considerations

- The `securityWarnings` and `memoryConstraints` fields were well-intentioned but ineffective (agents ignored them anyway)
- `.copilot/instructions.md` is the standard location for agent guardrails
- Future AES files should not include custom fields

## 6. Open Questions

None — the approach is clear from the analysis.
