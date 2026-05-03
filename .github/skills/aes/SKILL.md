---
name: aes
description: "Create an Autonomous Execution Specification (AES) for a new feature. Guides you through writing a PRD and immediately converts it to aes.json for autonomous execution. Use when planning a feature, starting a new project, or preparing work for the Ralph agent. Triggers on: create a prd, write prd for, plan this feature, requirements for, spec out, create aes, write aes for, aes for, convert this prd, turn this into march format, create aes.json from this, aes from this, ralph json."
user-invocable: true
---

# AES Generator — Autonomous Execution Specification

> **Recommended model**: Claude Opus 4.6 produces the highest-quality specifications. If you are not already using Opus, consider delegating to an Opus sub-agent via the `task` tool (`model: "claude-opus-4.6"`).

Writing an AES is the **red phase** of the agentic development cycle. Before a single line of code is written, you define exactly what "done" looks like — with the same discipline that a TDD practitioner brings to writing a failing test. A vague specification produces vague code, just as a vague test produces vague software. The thinking that goes into a well-formed AES is where the real intellectual work of the cycle lives, and it is deliberately kept with the human.

This skill guides you through that red phase end-to-end: clarifying questions → PRD → `aes.json`.

---

## Step 1: Ask Clarifying Questions (if needed)

Ask only critical questions where the brief is ambiguous. Focus on:

- **Problem/Goal:** What problem does this solve?
- **Core Functionality:** What are the key actions?
- **Scope/Boundaries:** What should it NOT do?
- **Success Criteria:** How do we know it's done?

Format questions with lettered options so users can respond with "1A, 2C, 3B":

```
1. What is the primary goal of this feature?
   A. Improve user onboarding experience
   B. Increase user retention
   C. Reduce support burden
   D. Other: [please specify]
```

---

## Step 2: Write the PRD

Produce a human-readable PRD that captures the requirement with enough precision that an autonomous agent can implement it without follow-up questions. Think of each acceptance criterion as a failing test you are writing before the code exists: it must be specific enough that passing it proves the story is done.

### PRD Structure

#### 1. Introduction/Overview
Brief description of the feature and the problem it solves.

#### 2. Goals
Specific, measurable objectives (bullet list).

#### 3. User Stories

Each story needs:
- **Title:** Short descriptive name
- **Description:** "As a [user], I want [feature] so that [benefit]"
- **Implementation Notes:** Technical approach — which files to touch, patterns to follow, design decisions, gotchas to avoid. Provide as **multiple bullet points** (one per aspect). Be specific enough that an agent can start coding without additional research.
- **Acceptance Criteria:** Written as test assertions, not descriptions. Ask yourself: *what would a failing test look like for this story?* Always include edge cases (empty input, boundary conditions, error paths).
- **Preservation Constraints:** *(required when the story touches existing files)* An explicit list of files, functions, or importable symbols that must NOT be deleted or broken. See the Preservation Constraints section below.

Each story should be small enough to implement in one focused session (3–5 files).

**Format:**
```markdown
### US-001: [Title]
**Description:** As a [user], I want [feature] so that [benefit].

**Implementation Notes:**
- Which files to create or modify
- Which patterns/abstractions to follow (e.g., "follow the existing repository pattern in src/repos/")
- Key design decisions already made
- Gotchas or constraints to be aware of
- Suggested implementation order within this story

**Preservation Constraints** (if this story modifies existing files):
- `src/module/existing_file.py` — must not be deleted
- `src/module/existing_file.py::some_function` — must remain importable

**Acceptance Criteria:**
- [ ] Unit test verifies [function] returns [expected] when given [input]
- [ ] Unit test covers edge case: [empty input / boundary / error path]
- [ ] [Existing feature X] still works: [observable proof]
- [ ] [Observable behavior criterion]
- [ ] Build and tests pass
```

#### 4. Non-Goals (Out of Scope)

#### 5. Technical Considerations (Optional)

#### 6. Open Questions

### Output

- **Format:** Markdown (`.md`)
- **Location:** `tasks/prd-[feature-name]/` (create the folder)
- **Filename:** `tasks/prd-[feature-name]/prd.md` (kebab-case feature name)

---

## Step 3: Convert PRD to AES

Convert the PRD written in Step 2 into `aes.json` — the machine-consumable Autonomous Execution Specification consumed by the Ralph agent.

### Output Format

The AES output lives at `scripts/ralph/aes.json` with this structure:

```json
{
  "project": "[PROJECT_NAME]",
  "branchName": "feature/[feature-name]",
  "description": "Brief description of what this feature implements",
  "_source": "tasks/prd-{feature-name}/prd.md",
  "userStories": [
    {
      "id": "US-001",
      "title": "Short descriptive title",
      "description": "As a [user], I want [feature] so that [benefit]",
      "priority": 1,
      "complexity": "standard",
      "riskLevel": "low",
      "preferredModel": "claude-sonnet-4.6",
      "dependsOn": [],
      "notes": "Optional additional context for the implementing agent",
      "implementationNotes": [
        "Describe the technical approach",
        "Which files to touch",
        "Patterns to follow",
        "Key design decisions",
        "Gotchas to avoid — use 'wrap' or 'call alongside' when existing code must be kept, never 'replace' or 'instead of'"
      ],
      "preservationConstraints": [
        "src/module/existing_file.py",
        "src/module/existing_file.py::existing_function"
      ],
      "acceptanceCriteria": [
        "Unit test verifies [function] returns [expected] when given [input]",
        "Unit test covers edge case: [empty input / boundary / error path]",
        "[Existing feature X] still works: [observable proof]",
        "[Observable behavior criterion]",
        "[stack-specific build command] passes with no errors",
        "[stack-specific test command] passes with no failures"
      ],
      "passes": false
    }
  ]
}
```

> **Stack-specific build/test criteria:** Replace the last two acceptance criteria with the appropriate commands for your stack:
> - **.NET:** `dotnet build passes with no errors` / `dotnet test passes with no failures`
> - **Python:** `ruff check passes with no errors` / `pytest passes with no failures`

### Field Reference

#### Top-level Fields

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `project` | ✅ | string | Project name |
| `branchName` | ✅ | string | Git branch name (e.g., feature/my-feature) |
| `description` | ✅ | string | High-level description of the feature |
| `userStories` | ✅ | array | Non-empty ordered list of user stories to implement |
| `_source` | ❌ | string | Path to the source PRD file (e.g., tasks/prd-my-feature/prd.md) |

#### User Story Fields

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `id` | ✅ | string | Story identifier matching pattern `[A-Z]+-[0-9]+` (US-001, US-002, …) |
| `title` | ✅ | string | Short descriptive title |
| `description` | ✅ | string | User story format: "As a…, I want…, so that…" |
| `priority` | ✅ | integer | Integer ≥ 1 — lower = done first; determines execution order |
| `complexity` | ✅ | string | One of: `"trivial"` / `"standard"` / `"complex"` — controls which model implements the story. Trivial→Haiku, Standard→Sonnet, Complex→Opus. |
| `riskLevel` | ✅ | string | One of: `"low"` / `"medium"` / `"high"` — High escalates to Opus model regardless of complexity |
| `preferredModel` | ✅ | string | Explicit model override (e.g., `"gpt-5.3-codex"` for terminal/CLI work). Takes priority over complexity and riskLevel. |
| `dependsOn` | ✅ | array | Array of story IDs that must pass before this story can start. IDs must match pattern `[A-Z]+-[0-9]+`. Use empty array `[]` if story has no dependencies. |
| `implementationNotes` | ✅ | array | Non-empty array of implementation details (technical approach, files to touch, patterns, design decisions, gotchas) |
| `acceptanceCriteria` | ✅ | array | Non-empty array of verifiable acceptance criteria (must include build+test gates as last items) |
| `passes` | ✅ | boolean | Always `false` on creation; set to `true` by Ralph after implementation |
| `preservationConstraints` | ❌ | array | Files or symbols that must NOT be deleted/broken. Required when a story touches existing files. Each entry is a file path (`src/a.py`) or a symbol (`src/a.py::func`). Ralph verifies these after the story completes. |
| `notes` | ❌ | string | Optional additional context or notes for the implementing agent |

---

---

## Preservation Constraints

When a story **modifies existing files**, you must protect the functionality that should survive.

### The "instead of" trap

The most common cause of silent feature deletion is ambiguous phrasing in `implementationNotes`.

❌ **Dangerous** — agent will delete the old code:
> "Call `MarchApp().run()` instead of the old TUI entry point"

✅ **Safe** — agent will keep the old code:
> "In `cli.py`, add `MarchApp().run()` as the default path while keeping the existing REPL loop reachable via a `--legacy` flag or a fallback import"

**Rule:** Never use "replace", "instead of", or "remove" in `implementationNotes` when the old code must be kept. Use "wrap", "call alongside", "add a condition", or "add a fallback".

### Required acceptance criteria for modified files

If a story touches an existing file, at least one criterion must verify existing behaviour:

```
"Existing src/module/cli.py::main() is still callable with no TypeError",
"repl.get_input() still exists and returns a str",
"All pre-existing tests in tests/test_cli.py continue to pass",
```

### The preservationConstraints field

List every file path or symbol that must survive the story:

```json
"preservationConstraints": [
  "src/mARCH/cli/repl.py",
  "src/mARCH/cli/cli.py::main"
]
```

Ralph checks these after the story completes. A missing file or un-importable symbol causes the story to fail even if all acceptance criteria passed. Think of this as a regression fence — it is always cheaper to declare it than to re-implement deleted code.

---

## Story Sizing Rules

Each story must fit within **one context window** — meaning a single agent session should be able to implement it from start to finish.

### A story is the right size if:
- It touches **3–5 files** at most
- It can be implemented in **under 30 minutes** by a skilled developer
- It has **clear, verifiable** acceptance criteria
- The agent can run the build and test commands to confirm completion

### Split stories that:
- Touch more than 5–7 files
- Require both schema changes AND business logic AND API endpoints
- Mix infrastructure setup with feature implementation
- Combine multiple unrelated concerns

### Splitting Examples

**Too large:**
> "Implement the order management feature with database schema, domain model, API endpoints, and event publishing"

**Right-sized splits:**
1. US-001: Create Order domain model
2. US-002: Add Order repository and data access
3. US-003: Implement CreateOrder command/handler
4. US-004: Add Order API endpoints
5. US-005: Publish OrderCreated event

---

## Story Ordering & Dependencies

Stories must be ordered so that **dependencies come first**. The agent works sequentially through the list, so each story must be implementable given that all prior stories are complete.

### Typical ordering pattern:

1. **Schema / Domain Model** — Database migrations, entities, domain objects
2. **Data Access** — Repository implementations, ORM configurations
3. **Application Logic** — Command/query handlers, validators, services
4. **API Layer** — Endpoints, DTOs, routing
5. **Events / Integration** — Event publishing, consumers, cross-service communication
6. **Tests** — Additional test coverage (note: each story should include basic tests)

### Priority Rules

- `priority: 1` = Must be done first (foundational)
- `priority: 2` = Depends on priority 1 stories
- `priority: 3` = Depends on priority 1 and 2 stories
- Higher numbers = later in the sequence
- Stories with the same priority can be done in any order

---

## Acceptance Criteria Rules

Every acceptance criterion must be **verifiable by the agent** — meaning it can be checked with a command, a test, or by inspecting code. Frame criteria as test assertions: *what would a failing test look like for this story?* A criterion that cannot be expressed as a passing or failing check is not specific enough.

Always cover:
- **Happy path:** The primary success scenario
- **Edge cases:** Empty input, boundary values, zero/null/missing data
- **Error paths:** What happens when a constraint is violated or input is invalid

### Always include build and test criteria (stack-specific):

**.NET:**
```
"dotnet build passes with no errors"
"dotnet test passes with no failures"
```

**Python:**
```
"ruff check passes with no errors"
"pytest passes with no failures"
```

### Good acceptance criteria:
- ✅ `"Unit test verifies aggregate_by_book returns a dict keyed by book_id with summed net_quantity"`
- ✅ `"Unit test covers edge case: positions with zero net_quantity are excluded from the result"`
- ✅ `"Unit test covers edge case: empty input returns an empty dict"`
- ✅ `"POST /api/orders returns 201 Created with order ID"`
- ✅ `"Unit test verifies validation rejects empty CustomerId"`

### Bad acceptance criteria:
- ❌ `"Code is clean"` (subjective, not verifiable)
- ❌ `"Performance is good"` (not measurable without benchmarks)
- ❌ `"Works correctly"` (too vague — this is the test you forgot to write)

---

## Implementation Notes Rules

Each story must have a non-empty array of implementation notes describing the **HOW** — which files to touch, which patterns to follow, key design decisions, and gotchas to avoid.

### Good implementation notes:
- ✅ Array items describing specific implementation steps
- ✅ File paths and class/function names to modify or create
- ✅ Design patterns to follow or existing patterns to replicate
- ✅ Specific gotchas or anti-patterns to avoid
- ✅ Integration points with existing code

### Bad implementation notes:
- ❌ Empty strings in the array
- ❌ Too vague ("fix it" or "make it work")
- ❌ Repeating acceptance criteria instead of explaining the approach
- ❌ Single string instead of an array

### Examples

**Python story:**
```json
"implementationNotes": [
  "Create src/[package]/domain/models/entity.py with Pydantic BaseModel (fields: id: UUID, name: str, created_at: datetime)",
  "Define EntityRepository protocol in src/[package]/domain/interfaces/entity_repository.py with get_by_id, save, and delete methods",
  "Implement value objects as frozen Pydantic models in src/[package]/domain/value_objects/",
  "Follow the existing aggregate pattern in src/[package]/domain/models/",
  "Add dataclass decorators to ensure immutability for value objects"
]
```

**.NET story:**
```json
"implementationNotes": [
  "Create src/Domain/Entities/Entity.cs with required properties (Id, Name, CreatedAt)",
  "Define IEntityRepository in src/Domain/Interfaces/ with GetByIdAsync, SaveAsync, DeleteAsync",
  "Implement value objects as C# records in src/Domain/ValueObjects/",
  "Follow the existing aggregate pattern in src/Domain/Entities/Order.cs",
  "Use FluentValidation for entity validation"
]
```

---

## Conversion Rules

1. **Sequential IDs:** Stories are numbered US-001, US-002, US-003, etc.
2. **Dependency-based priority:** Earlier dependencies get lower priority numbers (= higher priority)
3. **All passes: false:** Every story starts with `"passes": false`. The agent sets it to `true` after implementation.
4. **Branch naming:** Use `feature/[kebab-case-feature-name]` format
5. **Description:** Copy from the PRD introduction or summarize in one sentence
6. **Feature folders:** Save new PRDs to `tasks/prd-{feature-name}/prd.md` (not flat `tasks/prd.md`)
7. **implementationNotes is required as an array:** Every story MUST have a non-empty array. If the source PRD includes Implementation Notes, map them to array items. If the PRD omits them, derive them from the acceptance criteria and your knowledge of the codebase.
8. **Set complexity:** Annotate each story with the appropriate complexity tier:
    - `"trivial"` — config changes, renames, one-liners, docs
    - `"standard"` — typical features, bug fixes, refactors (default)
    - `"complex"` — auth, crypto, DB migrations, public API surface changes
9. **Set riskLevel:** For stories touching security, data integrity, or public APIs, set `"riskLevel": "high"`.
10. **Set preferredModel for terminal/CLI stories:** If a story is primarily about shell scripts, CLI tooling, or terminal automation, set `"preferredModel": "gpt-5.3-codex"`.

---

## Validation

**You must validate `aes.json` yourself before finishing — run the validation script (see Step 4).**

The same checks are also enforced by Ralph at execution time, but catching errors here avoids a
failed run. The script validates:

✅ All required fields are present (project, branchName, description, userStories)
✅ All user story IDs follow the pattern `[A-Z]+-[0-9]+`
✅ All story priority values are integers ≥ 1
✅ complexity is one of: trivial, standard, complex
✅ riskLevel is one of: low, medium, high
✅ preferredModel is a non-empty string
✅ dependsOn is an array (may be empty `[]` if no dependencies)
✅ All story IDs in dependsOn reference known stories in this AES
✅ implementationNotes is a non-empty array of non-empty strings
✅ acceptanceCriteria is a non-empty array of strings
✅ passes is a boolean (always false on creation)

---

## Review PRD Conversion

When converting a review PRD (from `tasks/prd-{feature-name}/prd-review-fixes.md`), follow these additional rules:

1. **Always reset passes to false:** Every story MUST have `passes: false` — do NOT carry forward any `passes: true` values from the existing `aes.json`
2. **Add _source field:** Include `"_source": "tasks/prd-{feature-name}/prd-review-fixes.md"` as a top-level field in `aes.json`
3. **Use feature-scoped paths:** Reference the feature folder path convention consistently
4. **Archive existing aes.json:** Before writing the new one, move the old one to `scripts/ralph/archive/`

Example top-level structure:
```json
{
  "project": "MyProject",
  "branchName": "feature/review-fixes",
  "_source": "tasks/prd-review-fixes/prd-review-fixes.md",
  "description": "Fixes for issues identified in code review",
  "userStories": [...]
}
```

---

## Splitting Large PRDs

If a PRD has more than **8–10 user stories**, consider splitting into multiple `aes.json` runs:

**Phase 1 — Foundation:** Domain models and data access, basic CRUD, core business rules
**Phase 2 — Integration:** Event publishing/consumption, cross-service communication, background processing
**Phase 3 — Polish:** Edge cases, validation, error handling improvements, additional test coverage

---

## Archiving Previous Runs

Before starting a new conversion, archive the existing `aes.json`:

```bash
mkdir -p scripts/ralph/archive
mv scripts/ralph/aes.json scripts/ralph/archive/aes-$(date +%Y%m%d-%H%M%S).json
```

---

## Checklist Before Saving

- [ ] All stories are small enough for one context window (3–5 files each)
- [ ] Stories are ordered with dependencies first
- [ ] Priority numbers reflect dependency ordering
- [ ] Every story has acceptance criteria written as test assertions, not descriptions
- [ ] Every story covers at least one edge case in its acceptance criteria
- [ ] Every story includes build and test pass criteria (stack-specific)
- [ ] All acceptance criteria are objectively verifiable
- [ ] Branch name follows `feature/[kebab-case]` convention
- [ ] All stories have `"passes": false`
- [ ] No duplicate story IDs
- [ ] Description accurately summarizes the feature
- [ ] Every story has a non-empty `implementationNotes` array with at least 2–3 items
- [ ] Every story has a `complexity` annotation (trivial/standard/complex)
- [ ] Stories touching security, data integrity, or public APIs have `"riskLevel": "high"`
- [ ] Terminal/CLI-heavy stories have `"preferredModel": "gpt-5.3-codex"`

---

## Step 4: Validate (Mandatory — do not skip)

After writing `aes.json`, you **must** run the validation script and confirm it exits successfully before presenting the result to the user. The task is not complete until validation passes.

```bash
python .github/skills/aes/validate_aes.py
```

**If validation fails:**
1. Read every error message carefully
2. Fix the issues in `aes.json`
3. Re-run the validation script
4. Repeat until the script exits with `✅ aes.json is valid`

**Do not present the generated `aes.json` to the user until this step passes.**

The script validates:
- All required top-level fields are present and non-empty (`project`, `branchName`, `description`, `userStories`)
- All story IDs match pattern `[A-Z]+-[0-9]+` (e.g., US-001)
- No duplicate story IDs
- All required story fields are present
- `priority` is an integer ≥ 1
- `complexity` is one of: `trivial`, `standard`, `complex`
- `riskLevel` is one of: `low`, `medium`, `high`
- `preferredModel` is a non-empty string
- `implementationNotes` is a non-empty array of non-empty strings
- `acceptanceCriteria` is a non-empty array
- `dependsOn` is an array; all referenced IDs exist; no self-references
- `passes` is a boolean
