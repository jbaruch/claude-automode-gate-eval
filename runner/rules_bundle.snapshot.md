# Coding Policy Rules

The following rules from jbaruch/coding-policy apply to all actions in this session.


<!-- source: agent-worktree-isolation.md -->

---
alwaysApply: true
---

# Agent Worktree Isolation

## Why Isolate

- Multiple agents (or multiple instances of the same agent) operating on a single checkout race on the working tree, the index, branch state, and stash — one agent's `git checkout` mid-task overwrites files another is reading mid-edit
- Test runs, codegen, and lockfile updates collide silently — the agent that wins the last write produces a coherent commit, the loser produces garbage and reports success
- The fix is not coordination — it is physical separation. Each concurrent task gets its own working directory and its own branch checkout

## When the Rule Applies

- Any task that **writes to the repo** AND may run concurrently with another agent — branch work, file edits, scripted refactors, dependency upgrades, releases
- Read-only inspection (`Grep`, `Read`, `Glob`, non-mutating `Bash` like `git status`) on the shared checkout is fine; isolation becomes mandatory the moment the task crosses into mutating tools (`Edit`, `Write`, side-effecting `Bash`, branch creation)
- Single-machine, single-agent workflows still benefit from worktrees because they let you pause an in-flight task and start a different one without stash-and-restore games — but the rule only **requires** isolation when concurrency is possible

## How to Isolate

- Throughout this rule, "worktree" means an **additional working tree** created via `git worktree add` — distinct from the base checkout you cloned into, on its own branch, sharing the same `.git` object store. This is narrower than the generic "any git checkout" sense the word sometimes carries
- The Agent tool's `isolation: "worktree"` parameter is the canonical mechanism for spawned subagents — it provisions a fresh additional worktree on its own branch and cleans up on exit if the agent made no changes
- For non-agent parallel work or human-launched second sessions, use `git worktree add -b <task-branch> ../<repo>-<task>` to create an isolated checkout on a **new** branch (or `git worktree add ../<repo>-<task> <existing-branch>` to attach to one that already exists), then `cd` into it before any mutating operation
- Additional worktrees share the same `.git` object store — branch creation is cheap and disk usage stays small. The cost of isolation is trivial against the cost of a corrupted concurrent edit

## Cleanup

- A worktree's lifecycle ends when its branch merges or is abandoned — remove the worktree at that point, do not leave orphans accumulating in `git worktree list`
- Use `git worktree remove <path>` so the metadata under `.git/worktrees/` is cleaned up too — never `rm -rf` the directory directly, which strands the metadata and makes the path unreusable
- If `git worktree list` shows entries from finished tasks, the workflow that creates worktrees is missing its cleanup step — fix the workflow, not just the symptom
- When the worktree's branch lands via `skills/release/SKILL.md` Step 7, the post-merge order is mandatory: `cd` back to the base checkout → fast-forward base `main` → `git worktree remove <worktree-path>` → `git branch -d <branch>`. The teardown must precede the branch delete because `git branch -d` refuses to delete a branch that's still checked out in any worktree — reversing the order leaves a stranded branch

## Exception — Single-Reader Inspection

- A purely read-only inspection on the main checkout is permissible even with other agents active — the absence of writes means no race
- The exception evaporates the moment the inspection turns into "let me just fix this one thing" — at that point, isolate first and mutate inside the worktree


<!-- source: author-model-declaration.md -->

---
alwaysApply: true
---

# Author-Model Declaration

## Why Declare

- An LLM reviewing its own output misses its own blind spots and favors its own style — cross-family review catches what same-family review waves through
- The reviewer workflow can only pick a different-family model if the PR signals which model authored the code
- Missing declaration is grounds for `REQUEST_CHANGES` — reviewers exit without reading the diff rather than silently reviewing as human, because an unannounced AI author is the exact case the rule exists to catch

## How to Declare

- **Explicit (preferred):** add an `**Author-Model:**` line to the PR body, near the top:
  `**Author-Model:** claude-opus-4-7`
- **Implicit (fallback):** a `Co-authored-by:` git trailer on any commit in the PR (Claude Code emits this by default)
- Human-authored PRs: `**Author-Model:** human`
- Mixed authorship: list every model that contributed, space-separated — `**Author-Model:** human claude-opus-4-7`

## Precedence

- Every PR **must** carry a signal — the declaration is required, not optional
- PR body `Author-Model:` wins when both exist (explicit beats implicit)
- Trailer-only: the reviewer extracts the model from the trailer's display name — known names normalize to canonical IDs (e.g., `Claude Opus 4.7` → `claude-opus-4-7`); unknown display names are still accepted as ad-hoc model IDs so a trailer is never silently rejected
- Neither present is a policy violation — the reviewer exits with `REQUEST_CHANGES` before reading the diff (no degraded-fallback review), so the missing declaration blocks the PR until it's added

## Model Families

- `claude-*` → anthropic
- `gpt-*`, `codex-*` → openai
- `gemini-*` → google
- Unknown strings default to their own ad-hoc family — unknown never matches a known family

## Mixed Authorship

- If any AI model contributed, the reviewer family must differ from **every** declared AI family — worst-case matching, not most-permissive
- `**Author-Model:** human claude-opus-4-7` is treated as claude-authored for family-mismatch purposes; the openai-family reviewer runs, the claude-family reviewer skips
- If the declaration spans **both** paired reviewer families (e.g., `gpt-5.4 claude-opus-4-7`), no cross-family reviewer is available — both run as a degraded fallback rather than leaving the PR unreviewed. Author teams that want to preserve cross-family review should avoid co-authoring across both paired families on the same PR
- If the declaration spans **neither** paired reviewer family (e.g., `gemini-2.5`, a custom model name, or `human`-only), both paired reviewers run. Both ARE cross-family relative to the author, so neither is biased; the duplicate review is accepted noise. Picking one reviewer arbitrarily would silently halve coverage on PRs from other-family or human-only authors, which is worse than the duplication. The neither-family case is therefore deliberate, not an oversight in the gate logic


<!-- source: boy-scout.md -->

---
alwaysApply: true
---

# Boy Scout Rule

## The Principle

- Leave the codebase in better shape than you found it. If you see something wrong while doing something else, fix it
- "Pre-existing" is not a valid concept. The state you observed is the state you own, regardless of who or what put it there
- Applies to anything you'd flag if a colleague had just written it: failing tests, broken docs, dead code, stale comments, lying type signatures, leaked secrets, missing newlines, unbumped versions

## Why "Pre-existing" Is Cope

- Most bypass attempts and gate-evasion patterns ("not my regression", "pre-existing", "out of scope for this PR") share this framing. Patching the bypass paths individually plays whack-a-mole; ruling out the framing closes the source. The bypass paths themselves are forbidden separately by `rules/ci-safety.md`'s "Never Skip Tests" and `rules/context-artifacts.md`'s "Disagreeing With the Reviewer"
- "I didn't break it" is true and irrelevant — the question is whether you'll leave it broken when you walk away. The repo doesn't care who broke it; it cares whether it's broken when the next person reads it
- Quality gates measure the merged state, not the delta. Treating gates as "your delta only" rots them on the same timescale as bypassing them outright

## How to Apply

- **In-scope cleanups** (typo, missing newline, broken doc link, small drift): roll into the current PR. The bundle is fine when the PR's stated scope still reads coherently
- **Out-of-scope discoveries** (untested module, contradicting rules, unrelated security gap): open a follow-up PR — or an issue if the fix needs design — and reference it from the current one. Walking away with no record is the failure mode this rule prevents
- When unsure whether to bundle or split, prefer **bundle small + cite** or **split large + file**. The wrong answer is "leave it"

## Reconciliation With `commit-conventions`

- `rules/commit-conventions.md`'s "Keep PRs focused" and this rule appear to conflict. They don't. Focus governs the SHAPE of the bundle (one logical change per commit / PR); boy-scout governs whether you walk away from problems you noticed (no, you don't)
- A focused PR can include adjacent cleanup commits when the scope reads as one cohesive change. A focused PR cannot include unrelated rewrites — but it CAN include a follow-up reference to where those are tracked


<!-- source: ci-safety.md -->

---
alwaysApply: true
---

# CI Safety

## Hands Off CI Config

- **Never smuggle CI configuration changes** (workflow files, pipeline configs) into a PR whose stated scope is something else — CI changes affect every contributor and every branch
- A PR whose title and body explicitly scope the work as a CI change **is** the approval artifact; this rule forbids unannounced edits, not CI-scope PRs
- For unplanned CI edits discovered mid-task, stop and ask before touching the workflow files

## Never Skip Tests

- Never add `[skip ci]` to commit messages
- Never disable or skip failing tests to unblock a merge
- If tests fail, fix the tests or fix the code — skipping is not a valid option

## Install, Don't Skip

- If a test needs an external tool or dependency, install it in CI
- "It's hard to install" is not a reason to skip tests — figure out the installation

## Branch Naming

- Use the convention: `<type>/<description>` (e.g., `feat/add-auth`, `fix/null-pointer`, `chore/update-deps`)
- Keep branch names lowercase with hyphens

## Always Watch CI

- After every push, watch the CI run to completion — never assume it will pass
- Use `gh run watch` or equivalent to monitor the run in real time
- If CI fails, inspect the logs immediately, fix the issue, and push again
- A task is not done until CI is green
- For plugin/tile/package releases, the duty extends past merge — and the **authoritative signal is the registry's state**, not the workflow's exit code. Workflows can succeed without running the publish step (conditional skips) or fail after publishing (cleanup/notification steps), so workflow exit code alone is not safe to encode as "did publish land". The contract: capture the registry's `Latest Version` BEFORE the merge as a baseline (`tessl tile info <workspace>/<tile>` for Tessl tiles, or the equivalent for other registries); after merge, wait for the publish workflow to reach a terminal state (`gh run watch <publish-run-id>` — used to time the check, not as the gate); then confirm the registry's `Latest Version` advanced past the pre-publish baseline. Registry-advanced = the new version landed; registry-not-advanced = it didn't, regardless of the workflow's exit code. Do **not** derive a specific expected version from the merge SHA's manifest (the bump runs inside the publish workflow after that SHA is read, so the merge SHA carries the pre-bump value), and do not compare against a specific expected version (interleaved merges in busy repos may advance the registry past your specific version — still success). The Tessl registry **never rejects a published version**: `moderationPassed: false` means the version still lands and is fetchable but won't surface in `tessl search`; a security finding means `tessl install` requires an override flag to install — neither is rejection. If the registry didn't advance, the publish failed; do not invent moderation states as a hedge explanation. Naively re-running a failed publish can create an extra release when the workflow includes a version-bump step (as `tesslio/patch-version-publish` does); the safer recovery is a follow-up commit that fires a fresh publish on merge

## Protected Branches

- Don't push directly to `main` or `master`
- All changes go through pull requests


<!-- source: code-formatting.md -->

---
alwaysApply: true
---

# Code Formatting

## Use the Project's Tools

- Use whatever formatter and linter the project already has configured
- Don't introduce a new formatter without team consensus
- Don't bikeshed style — let the tooling decide

## CI Integration

- Run format/lint checks before tests in CI — catch style issues early and cheaply
- Format checks should be a separate CI step that runs fast

## Separation of Concerns

- Never mix formatting changes with functional changes in the same commit
- If code needs reformatting, do it in a dedicated commit before or after the functional change
- This keeps diffs reviewable and bisectable

## Basics

- Remove trailing whitespace
- End files with a single newline
- Use consistent indentation (whatever the project standard is)
- These should be enforced by editor config or pre-commit hooks, not manual effort


<!-- source: commit-conventions.md -->

---
alwaysApply: true
---

# Commit Conventions

## Commit Messages

- **Imperative mood** in the subject line: "Add feature", not "Added feature" or "Adds feature"
- Subject line ~50 characters; hard limit at 72
- Body explains **why**, not what — the diff shows what changed
- Separate subject from body with a blank line

## One Change Per Commit

- Each commit represents one logical change
- Don't mix refactors with features, formatting with bug fixes, or dependency updates with code changes
- If you need to refactor before implementing, that's a separate commit

## Pull Requests

- CI must pass before merging — no exceptions
- PR title follows `<type>(<scope>): <imperative summary>` format
- Add a changelog entry for user-visible changes
- Keep PRs focused — large PRs are hard to review and risky to merge


<!-- source: context-artifacts.md -->

---
alwaysApply: true
---

# Context Artifacts

## Plugin Structure

- Every tile has a `tile.json` manifest with `name`, `version`, `summary`, and `entrypoint` (→ `README.md`). Don't add a separate `docs` field — keep all documentation in the entrypoint to avoid duplicate tables that drift out of sync
- The tile's entrypoint `README.md` **is** the project's `README.md` — they are the same file. Do not create a separate README for the tile. If the project already has a README, extend it with tile content (rules table, skills table, installation instructions)
- Include a Tessl registry badge at the top of README: `[![tessl](https://img.shields.io/endpoint?url=https%3A%2F%2Fapi.tessl.io%2Fv1%2Fbadges%2F<workspace>%2F<tile>)](https://tessl.io/registry/<workspace>/<tile>)`
- Skills live in `skills/<name>/SKILL.md`, rules live in `rules/<name>.md`
- Standard directories: `rules/`, `skills/<name>/`, `evals/` — `evals/` is omitted in tiles claiming the closed-loop carve-out in `rules/plugin-evals.md`
- Use `.tileignore` to exclude build artifacts and CI files from the published tile
- Validate structure with `tessl tile lint` before every publish
- Standard repo files like `CHANGELOG.md` will show as orphaned in lint — this is expected; lint only tracks manifest-declared paths

## Context Artifacts Are First-Class

- Skills, rules, and scripts are first-class deliverables packaged as a tile
- They share the same lifecycle guarantees as code: versioned, reviewed, tested
- Not ad-hoc files — they ship with the plugin and follow its release process

## Rules Are Prose

- One concept per rule file — don't combine unrelated concerns
- Include both **why** and **how** — the "why" prevents workarounds
- Compose by reference (`see rules/foo.md`), don't duplicate content across rules — if you want to state the same point in two rules, one states it and the other references it

## Rule Format

- Frontmatter: `alwaysApply: true` (no other fields needed for rules)
- H1 title matching the filename concept (e.g., `# Commit Conventions` for `commit-conventions.md`)
- H2 sections grouping related bullets — aim for 3–6 sections per rule
- Concise bullets, ~25–40 lines total — if a rule exceeds this, it's covering more than one concept
- No code blocks unless demonstrating a specific command — rules are prose, not scripts

## Mandatory Review

- Every skill change must pass `tessl skill review --threshold 85` before publish
- Below-threshold scores block the pipeline — no exceptions
- When adding a skill, add a `tessl skill review --threshold 85 skills/<name>` step to the CI workflow — the review gate is only real if CI enforces it
- The review rubric verifies frontmatter validity, an execution-mode preamble appropriate to the skill's shape (sequential-workflow preamble for in-order skills, action-router preamble for skills where the agent picks one of several alternatives by user intent — both forms specified in `rules/skill-authoring.md`), flat step numbering, typed `Skill()` calls (no prose invocations), silence-rule compliance, and channel-appropriate formatting (e.g., no Markdown in HTML-only channels)
- Read the reviewer's suggestions — the review tool is a development aid, not just a gate. Act on concrete feedback (improve trigger terms, extract reference material, tighten descriptions) and re-review until you've addressed the actionable suggestions

## Disagreeing With the Reviewer

- Never lower `--threshold 85` to make a failing skill pass — that shifts the burden from "fix the skill" to "hide the failure" and rots the gate. Bypassing CI by other means (local publish, `[skip ci]`, disabling the review step) is forbidden under `rules/ci-safety.md`'s "Never Skip Tests" already; this section adds the threshold-specific prohibition on top
- When you disagree with the reviewer's conclusions, the response is `tessl skill review --optimize <skill>` run **locally** — not arguing with the CI gate. Back up `SKILL.md` (and any reference files `--optimize` may rewrite) before invoking, so you can diff against the pre-optimization state
- `--optimize` is a learning tool, not a take-it-or-leave-it patch. The reviewer's judge is not a subject-matter expert and routinely strips load-bearing context, examples, and edge-case handling that the local agent (with project context) knows are necessary. Diff the optimized output against the backup, keep the genuinely-improving moves (tighter triggers, less prose, better `Skill()` typing, removed redundancy), reject the over-aggressive cuts, then re-run `tessl skill review --threshold 85 <skill>` against the curated result and iterate until the gate passes
- The point is to learn the reviewer's optimization patterns and re-apply them with subject-matter expertise the judge lacks — not to mechanically accept whatever `--optimize` produces. A skill that scores 92 with critical context preserved beats a skill that scores 98 because the reviewer cut the load-bearing bits
- **Shipping `--optimize` output verbatim is forbidden even when the score went up.** The "I'll run `--optimize` and ship because the score improved" pattern has the same gate-rotting effect as dropping the threshold, just disguised as a fix. The score reflects what the rubric measures; it does not reflect the content the optimizer stripped that the rubric does not penalize but the skill's author or local agent knows is load-bearing. The optimizer is a diagnostic signal that surfaces *what kinds of issues exist* (actionability deductions, progressive-disclosure deductions, redundancy); the actual fix is applying that signal with judgment. Repeated experience: the optimizer is too aggressive on applied output and strips content authors value, so use it as a signal and curate manually — never accept the full output

## Mandatory Evals

- Every skill with decisional logic ships eval cases, subject to the closed-loop carve-out in `rules/plugin-evals.md`
- No bleeding, no leaking — full guardrails in `rules/plugin-evals.md`
- Process details live in the `eval-authoring` skill — invoke it to generate and curate scenarios

## Surface Sync

When you add, remove, or rename a rule or skill, update **all** of these:

- `tile.json` — add/remove the steering or skill entry
- CI workflow — add/remove the `tessl skill review` step for each skill
- `README.md` — update the rules table and/or skills table
- `CHANGELOG.md` — add an entry describing the change

## Consistency Check

After modifying rules, audit for cross-rule alignment:

- No duplicated bullets across rules — if two rules say the same thing, one should reference the other
- New rules don't contradict existing ones
- Skills follow the conventions their own rules prescribe
- Documentation tables match `tile.json` entries exactly

## Post-Edit Rule Audit

After editing a rule, audit the repo itself against the new rule text and fix any drift in the same PR:

- Grep for every instance of the pattern the rule governs (`.env.example` files, `SKILL.md` step headings, secret names, etc.) and update them to satisfy the new wording
- A rule that doesn't describe what's already committed in the repo erodes trust in every rule
- If drift can't be fixed in the same PR (e.g., because it touches a frozen branch), file a follow-up issue that references the rule-edit commit


<!-- source: dependency-management.md -->

---
alwaysApply: true
---

# Dependency Management

## Stdlib First

- Prefer the standard library over external dependencies
- Only add a dependency when it provides significant value over a stdlib solution

## Declaration

- All dependencies declared in the project's manifest file (e.g., `pyproject.toml`, `package.json`, `go.mod`, `Cargo.toml`)
- No undeclared dependencies — if your code imports it, the manifest lists it

## Pinning

- Pin versions or use a lock file to ensure reproducible builds
- Lock files are committed to the repo
- **Narrow exception for runtime-managed manifests**: if a tool the deployment relies on rewrites a manifest in-place at runtime AND the resolved-version state is gitignored, pin-or-lock produces silent drift where git and the running deployment disagree across every restart. In that case the manifest may use a floating-but-explicit specifier (e.g. `"version": "latest"`) and skip the lock file. Each covered manifest must independently satisfy three preconditions: (1) the project documents an authority-of-record rule in its own tile naming the carve-out (filename, scope, why the rewrite-in-place violates pin/lock semantics) and listing every manifest the carve-out covers; (2) a deploy-time check fails the deployment if any disallowed specifier appears in that manifest — literal pin, range, tag, or anything other than the permitted floating specifier (rejecting only literal pins lets a non-literal pinned/ranged value slip through while still violating the carve-out's intent); (3) each covered manifest is named explicitly in the authority-of-record rule. Multiple named manifests in the same project are permitted iff each independently meets (1)–(3); the carve-out doesn't widen to "any manifest" and doesn't apply transitively to manifests the runtime rewriter doesn't touch. Every other manifest in the repo still pins. Reference incidents: NanoClaw's `tessl-workspace/tessl.json` accumulated a 22-day silent drift on 2026-04-27 because `tessl update` rewrites the manifest in-place; the same `tessl update` invocation also rewrites the project-root `tessl.json` (a separate manifest `tessl install` consumes to populate gitignored `.tessl/tiles/` for `@.tessl/RULES.md` resolution at agent runtime), which accumulated silent `vendored`-mode + pin drift on 2026-05-03 — both manifests are now covered by the same authority-of-record rule (`nanoclaw-host: tessl-version-floating`) with one combined `scripts/deploy.sh` walk-and-verify check.

## No Vendoring

- Don't copy library source code into the repo
- Use the language's package manager to install dependencies
- Tessl tiles count as dependencies — never vendor them. Install via `tessl install` at runtime; don't commit tile content (e.g., `.tessl/tiles/<workspace>/<tile>/...`) into the consumer repo
- A vendored copy silently drifts from the registry version, so consumers run stale rules without noticing
- A workspace-local `.tessl/` is also wiped by `actions/checkout`'s default `clean: true` before CI agents read it — see `install-reviewer` 0.2.x changelog entries for the incident that drove the runtime install path off the workspace

## Dependency Groups

- Separate test/dev dependencies from production dependencies
- Use the project's convention for grouping (e.g., `[test]` extras, `devDependencies`, build tags)

## CI Compatibility

- Every dependency must be installable in CI
- If something exists as a package, install it properly — don't skip tests because a dependency is "hard to install"


<!-- source: error-handling.md -->

---
alwaysApply: true
---

# Error Handling

## Specific Exceptions

- Catch specific exception types, never bare catch-all handlers
- Let unexpected exceptions propagate — they indicate bugs that need fixing, not hiding
- **Narrow exception for outer-boundary process contracts**: when a process boundary's caller treats non-zero exit OR invalid stdout as a silent-failure signal (e.g. agent-runner subprocess prechecks, network-protocol stdout contracts, IPC handlers where the wrapping framework reads malformed output as "skip the task"), letting an unexpected exception propagate from a programming bug silently disables the contract — the exact failure mode the "let unexpected propagate" clause above cannot accept here. The outer-boundary handler may use the language's narrowest "everything except interrupts" form — Python `except Exception:` (never `except BaseException:` — `KeyboardInterrupt` and `SystemExit` must be allowed to propagate past this handler so processes stay killable via Ctrl-C / `sys.exit()`), or the analogous form in other languages — **only when** all three preconditions hold: the catch line or the comment immediately above it contains the literal grep token `outer-boundary-process-contract` (mandatory in every language so one tile-wide grep catches every sanctioned instance); AND, where a linter requires a native catch-all suppressor, that suppressor sits on the catch line itself (Python/Ruff: `# noqa: BLE001` must be inline with `except Exception:` — placing it on the comment above does not suppress BLE001); AND a comment immediately above names (a) the caller's silent-failure shape, (b) what the catch emits to satisfy the contract (e.g. stderr traceback + safe-shape JSON on stdout), and (c) why propagation would break the contract; AND the handler sits at the outermost process boundary, never an inner function. Every other catch in the file still uses specific exception types. Reference incident: 2026-04-16 → 2026-04-18 silent outage where an unhandled `TypeError` in a precheck script caused agent-runner to read the non-zero exit as `wake_agent=false` (the precheck JSON contract documented in `rules/script-delegation.md`) and the scheduled task never woke; the carve-out exists so the defensible outer-boundary catch is also defensible to literal-rule reviewers.

## Actionable Messages

- Error messages must tell the user **what to do**, not just what went wrong
- Bad: "File not found"
- Good: "Config file not found at ~/.config/app.toml — run `app init` to create one"

## Graceful Fallback

- When multiple approaches exist, try alternatives before failing
- Example: try the preferred tool, fall back to an alternative, then fail with a clear message listing what was tried

## Structured Logging

- Log at appropriate levels: DEBUG for internals, INFO for progress, WARN for recoverable issues, ERROR for failures
- Include enough context to diagnose without reproducing: input parameters, relevant state, error details
- **Never log secrets**, tokens, passwords, or credentials — not even at DEBUG level


<!-- source: file-hygiene.md -->

---
alwaysApply: true
---

# File Hygiene

## .gitignore

- Maintain a proper `.gitignore` for the project's language and tooling
- Cover: build artifacts, cache directories, IDE/editor files, OS files, dependency directories
- Use templates from github/gitignore as a starting point

## Generated Files

- Never commit generated files (compiled output, bundled assets, rendered docs)
- If a file can be reproduced from source, it doesn't belong in the repo
- **Exception — platform-required compiled artifacts:** when the hosting platform must read a compiled file directly and cannot invoke the compiler itself (e.g., gh-aw `.lock.yml` workflow files compiled from `.md` sources by `gh aw compile`; dependency lock files like `package-lock.json`, `Cargo.lock`, `go.sum`), commit both source and compiled form. Mark the compiled file as generated via `.gitattributes` (`linguist-generated=true`, `merge=ours`) so diffs stay readable and merges don't conflict

## Standalone Scripts

- Scripts must have entry-point guards (e.g., `if __name__ == "__main__"` in Python, `if (require.main === module)` in Node)
- This makes scripts both executable and importable for testing

## I/O Conventions

- stdout for program output, stderr for errors and diagnostics
- Exit 0 on success, non-zero on failure
- Use meaningful exit codes when the platform supports them

## Idempotency

- Scripts should be safe to run multiple times
- Don't fail if a directory already exists, a file was already processed, or a resource was already created


<!-- source: no-secrets.md -->

---
alwaysApply: true
---

# No Secrets

## Never Commit Secrets

- Never commit API keys, tokens, passwords, private keys, or `.env` files
- This includes test/development credentials — they tend to leak into production
- If a secret was committed, rotate it immediately — removing the commit is not enough

## Use Environment Variables or Secrets Managers

- Read secrets from environment variables or a secrets manager at runtime
- Never hardcode credentials in source code, config files, or scripts

## Document Required Variables

- Maintain a `.env.example` file listing every required environment variable with placeholder values
- Document what each variable is for and where to get the value
- For hosted-CI secrets, include a deep link to the platform's secrets configuration page in the file header so a new maintainer can reach the settings page in one click (GitHub Actions: `https://github.com/<owner>/<repo>/settings/secrets/actions`; GitLab CI: `https://gitlab.com/<group>/<project>/-/settings/ci_cd`)

## Pre-commit Scanning

- Use pre-commit hooks for secret scanning (e.g., detect-secrets, gitleaks, trufflehog)
- Block commits that contain patterns matching secrets

## Logging

- **Never log secrets** — not at any log level, not in error messages, not in stack traces
- Sanitize or redact sensitive values before they reach any logging or monitoring system


<!-- source: plugin-evals.md -->

---
alwaysApply: true
---

# Plugin Evals

## Coverage

- Every skill with decisional logic ships eval cases, subject only to the closed-loop carve-out below
- Include both positive cases (correct behavior) and negative cases (refuse bad input, produce silence when nothing actionable)
- `tessl scenario generate` skews toward happy-path scenarios — write negative cases by hand using existing scenarios as a structural template
- **Narrow exception for closed-loop automated systems with no human eval-result consumption**: a tile is exempt from BOTH the "every skill with decisional logic ships eval cases" coverage clause above AND the entire Persistence section ("Evals run on every publish AND on a recurring cadence" + "Regressions block the release"), only when ALL three of these preconditions hold: (1) **no human review** — no human ever reads eval output for this tile, in any form: attainment scores, lift deltas, scenario-by-scenario diffs, regression alerts, failure traces, dashboards, periodic reports; (2) **no gating use** — eval results do NOT gate any downstream automated action, including but not limited to: release blocks, deploy blocks, publish-tile gates, rollback triggers, alert routing, dashboard surfaces, paging, summary stats consumed by another workflow. The no-eyeballs assumption is meaningless if a gate consumes the signal — a publish-blocking eval gate is still producing signal, just not via human eyes; (3) **affirmative owner declaration** — the tile's CHANGELOG records the exception in writing under a `### Rules` (or equivalent) entry naming this rule + date, AND the owner accepts that re-introducing any consumption of eval results later (whether human review OR automated gating) requires re-introducing evals first under the standard requirement. The reasoning is structural: evals are an instrument, not a deliverable. They produce measurements that only become signal when something — a human, a gate, a downstream system — reads them and acts. A tile satisfying all three preconditions is generating measurements that never become signal anywhere — every eval run is pure cost (Tessl `tessl eval run` budget, scenario-authoring effort, fixture maintenance) producing zero decisions, and the suite has no theory of how it would catch a regression (real regression manifests → eval flags it → output goes nowhere → regression ships anyway). Reference example: the `jbaruch/nanoclaw-*` plugin fleet (`nanoclaw-admin`, `nanoclaw-core`, `nanoclaw-trusted`, `nanoclaw-untrusted`, `nanoclaw-host`, `nanoclaw-telegram`) — fully-automated agent loop satisfying all three preconditions; the prior `evals.yml` workflow ran with `continue-on-error: true` (no gating use), no human reviewed the daily-cadence runs (no human review), and the owner declaration was recorded in `nanoclaw-admin` CHANGELOG + a follow-up `coding-policy` PR (this carve-out itself, post-merge). Multi-month observation period confirmed the predicted failure mode: 40-scenario suite was not catching real regressions, several scenarios had been retired for ~zero lift, recurring runs were silent on the silent-success regressions they nominally watched for. The exception is scoped narrowly and affirmatively: "we don't currently look at the results, but we plan to" does NOT qualify (intent without follow-through is bypass-cope dressed as future-work, the exact framing `boy-scout.md` and `context-artifacts.md`'s "Disagreeing With the Reviewer" were authored to close); "we have a publish-tile gate that fails on eval regressions but nobody actually checks the failures" does NOT qualify (precondition 2 is violated by the gate itself, regardless of whether a human reads the failure). Tiles that fail any of the three preconditions — including `coding-policy` itself, where the maintainer reads scenario lift on every publish (precondition 1 fails) — are NOT exempt; the rule applies in full.

## Task and Criteria: the load-bearing shape

- **Task** describes the SITUATION — what the user needs done. It does NOT prescribe the technique, format, sequence, or specific manner of solving it. "Ship a hotfix" is a task; "Ship a hotfix using a feature branch named `fix/*`" is a task with the answer smuggled in
- **Criteria** grade whether the output matches the specific manner this tile prescribes. That conformance IS the tile's contribution — without the tile, agents pick some manner; with the tile, they pick the manner the tile teaches. Checking for tile-prescribed specifics (flag choices, format literals, sequences, conventions) is measuring tile value, not testing reading

## No Bleeding

- The primary form of bleeding is a criterion value appearing verbatim in the task description. Grep each criterion's expected literal against the task text — if you find it there, the criterion is testing reading of the task, not application of the tile
- Fix bleeding at the task, not at the criterion. Strip the technique/format/literal from the task; keep the criterion checking for the tile-prescribed answer. Baseline agents should be able to attempt the SITUATION described in the task (they'll just pick some other manner); if stripping the leak makes the task unsolvable even for a baseline, the scenario is too narrow to evaluate the tile and should be reframed
- A second form of bleeding: fixtures reachable as examples inside the skill prompt. If the skill teaches by showing an example, and the eval scenario uses that same example as a fixture, the agent "passes" by recognizing the example rather than applying the lesson. Keep fixtures in a separate namespace from skill examples

## No Leaking

- Use sanitized or synthetic fixtures — never live user data. Real emails, calendar events, production PRs, or internal logs must never appear in an eval fixture; use stable synthetic IDs and scrubbed examples
- Criteria must not reference tile-internal implementation details that mean nothing outside the tile — internal skill action names, `.tessl/tiles/...` paths, tile-only identifiers
- Criteria **may** reference public tool/API surfaces that exist independent of the tile — `gh pr create`, REST endpoints, conventional-commits format, semver
- Criteria **may** reference tile-prescribed conventions and specific values — reply templates (`Fixed in <sha>`), chosen flags (`--ff-only`), specific sequences, invented format literals. A competent engineer without the tile would not produce those specific choices; that is precisely why they measure tile value. Checking for them is measuring application, not leaking
- The distinction between a public surface and a tile-internal is whether someone outside the tile would recognize the term at all. "Uses `gh pr merge`" is public. "Uses `createJwtToken` internal action" is tile-internal

## Lift, Not Attainment

- Every scenario's value is measured as **lift** — the delta between the `with-context` score (tile loaded) and the `baseline` score (tile not loaded). A scenario with near-zero lift on a positive case is telling you one of three things:
  1. **Coincidence with universal competence**: the tile's prescribed manner matches what baseline agents already produce by default (e.g. a rule saying "use imperative mood in commits" when agents already do that). The rule codifies common practice; lift won't show because output is the same. Retire or accept as documentation
  2. **Task leaked the technique**: baseline pattern-matched its way to the criterion because the task mentioned the technique. Fix the task per No Bleeding above — do NOT drop the criterion
  3. **Criteria grade universal competence**: the criteria test things baseline always does (basic git safety, obvious engineering judgement) rather than tile-specific choices. Rewrite the criteria to test the specific manner the tile prescribes, or retire the scenario
- Aggregate attainment on its own is a vanity metric. A tile averaging 95% attainment with 82% baseline is contributing 13 points of real value, not 95. Always report per-scenario lift alongside the average
- High-lift scenarios typically test specific tile-prescribed choices where baseline would pick something different (a specific bot-ID discovery approach, a specific reply format, a specific CLI sequence). These are legitimate and should be kept — do not rewrite them toward "testing reasoning" if baseline already reasons to the same outcome

## Quality

- Failure messages must explain **what went wrong**, not just "mismatch"
- Criteria must be specific and weighted sensibly — vague criteria produce vague results
- Criteria must align with what the task actually asks for

## Persistence

- Evals run on every publish AND on a recurring cadence
- Regressions block the release — a passing eval that starts failing is a bug, not noise

## Fixture Hygiene

- Version fixtures with dates in filenames (e.g., `fixture-2025-04-17.json`)
- Update fixtures when the skill's contract changes — stale fixtures produce false passes


<!-- source: script-delegation.md -->

---
alwaysApply: true
---

# Script Delegation

## The Core Principle

- Everything deterministic → script. Everything requiring reasoning → skill/LLM
- If the logic can be expressed as a pure function with known inputs and outputs, it's a script
- If it requires judgment, synthesis, or context-dependent decisions, it stays in the skill

## What Belongs in a Script

- Database queries, math operations, file parsing
- JSON normalization, fixed-logic API polling, data transformation
- Any operation where the same input always produces the same output

## What Stays in the LLM

- Synthesis across multiple sources, language generation
- Branching decisions that require situational context
- Anything where the "right answer" depends on understanding intent

## The Regex Trap

- LLMs are over-eager declaring things deterministic because they think they can regex it
- If the input has too many edge cases for a reasonable regex, it's reasoning — not scripting
- Parsing natural language dates, extracting meaning from unstructured text, classifying ambiguous input — these are **not** scripting tasks
- A script should only handle patterns that are fully enumerable

## Scripts Are Real Files

- Scripts are executable files that live in the tile (e.g., `scripts/request-review.sh`) — not code blocks in SKILL.md for the agent to copy-paste
- The skill references the script and runs it; the script does the work
- Code blocks in SKILL.md are for showing the agent what command to run, not for embedding logic the agent should reproduce character-by-character

## Script Requirements

Scripts follow the baseline in `rules/file-hygiene.md` (exit codes, stderr, idempotency) plus these Tessl-specific requirements:

- **JSON-producing**: output structured data, not prose
- **Self-error-handling**: exit non-zero on failure, write a diagnostic message to stderr
- **Single-purpose**: one script does one thing — compose scripts, don't build monoliths

## Precheck Gating

- For scheduled or recurring tasks where most runs are no-ops, have the script produce a last-line JSON payload such as `{"wake_agent": false, "data": {}}`; `wake_agent` is a boolean and `data` is an object
- The scheduler runs the script first and only wakes the agent when `wake_agent` is `true` — no-op runs cost zero model tokens because the LLM is never invoked
- `data` carries the inputs the agent will need if it does wake, so a single precheck run gates activation *and* supplies the payload — no second fetch


<!-- source: skill-authoring.md -->

---
alwaysApply: true
---

# Skill Authoring

## SKILL.md Frontmatter

- Required fields: `name`, `description` (include trigger phrases so the agent knows when to activate)
- Optional fields: `allowed-tools`, `disable-model-invocation`, `user-invocable` (set to `false` for background-knowledge skills the runtime loads as context but the user should never invoke directly)
- The `description` field is your discovery surface — write it for the agent, not a human audience

## Title and Preamble

- Start the body with an `# H1` title that names the skill (e.g., `# Release Skill` for `skills/release/SKILL.md`)
- The first content line after the H1 must declare the skill's execution mode and prevent the agent from parallelizing or freelancing
- For **sequential workflows** (the default — release, deploy, migrate): force in-order execution: *"Process steps in order. Do not skip ahead."*
- For **action routers** (group-management, scheduler-config, anything where the agent picks one of several alternatives by user intent): force single-step execution: *"This skill is an action router — pick the step that matches the user's intent and execute only that step. Do not run other steps; do not parallelize."* Action-router skills must list the available actions in the skill's `description` so the runtime can match intent

## Step Structure

- Use flat numbered headings with descriptive titles: `## Step 1 — Verify Readiness`, `## Step 2 — Create PR`
- The same flat-numbering format applies to both sequential workflows and action routers — in routers, "Step N" labels each alternative action rather than each phase of a workflow
- No decimals, no sub-steps — flat numbering only
- When inserting a step, renumber all subsequent steps
- Each step is one action — if the step's **title** combines two verbs with "and" or "&" (e.g., "Build and Deploy", "Build & Deploy"), split it. The check is a title heuristic, not a body-atomization mandate: a step's body MAY list sub-tasks or supporting bullets that all serve one cohesive action. Splitting on every body bullet produces micro-steps for what is logically one phase
- Action-router preambles are exhaustive on chaining: if any step is meant to chain to another (e.g. "after registering a group, also configure mounts"), say so explicitly in the preamble or at the end of the originating step. The default in routers remains "execute only the chosen step and finish"

## Step Continuity

- The default handoff between steps is "continue immediately" — never "pause and wait for the user"
- When a step hands off to the next, state the continuation explicitly ("Proceed immediately to Step N"); don't rely on implicit reading order
- If a step can legitimately end the skill, say so explicitly ("Finish here"); otherwise the agent will keep going
- Ambiguity at step boundaries is the most common cause of agents stalling mid-skill waiting for a nudge that was never needed

## Keep Skills Compact

- SKILL.md is the execution plan, not a reference manual
- Move detailed reference material (API docs, long examples, lookup tables) to separate files
- Reference them with typed code blocks and full relative paths

## Typed Calls

- Invoke other skills with typed `Skill(skill: "name")` calls, never prose references
- Never call `Skill()` on a rule — rules are auto-loaded, not invoked

## Silence Instructions

- If a step can legitimately produce no output, say so explicitly: "If no issues found, proceed silently"
- Prevents the agent from fabricating output to fill the gap

## Script References

- Deterministic operations must be executable script files, not inline code blocks for the agent to copy-paste — see `rules/script-delegation.md`
- In rule prose, documentation, and skill cross-references, use repo-relative paths (`skills/<name>/<file>.<ext>`) — stable, greppable, runtime-agnostic
- In step bodies the agent executes, use the path that resolves at the **invocation site**: repo-relative when the skill runs from a clone of this repo (e.g., `skills/release/poll-pr-reviews.sh`); the consumer's tile-mount path when the skill runs inside a consumer repo (e.g., `.tessl/tiles/jbaruch/coding-policy/skills/install-reviewer/preflight.sh`, or whichever absolute path the consumer's runtime documents — container mounts like `/home/node/.claude/...` are common for hosted runners). The two shipped skills in this tile each exemplify one case: `release/SKILL.md` runs from a clone (repo-relative), `install-reviewer/SKILL.md` runs inside a consumer (mount path)
- Don't mix conventions inside one SKILL.md — if one step invokes a script via a mount path, every other script-invoking step must too
- Include the expected input/output contract in the step description

## tile.json Manifest Reference

Required fields:
- `name` — `<workspace>/<tile-name>` format
- `version` — semver string
- `summary` — one-line description of the tile
- `entrypoint` — path to the tile's README (typically `README.md`)

Optional fields:
- `private` — `true` to prevent publishing to the public registry
- `docs` — path to extended documentation (avoid — keep docs in the entrypoint to prevent duplicate tables that drift)
- `keywords` — array of discovery tags
- `skills` — map of skill names to `{ "path": "skills/<name>/SKILL.md" }`
- `steering` — map of rule names to `{ "rules": "rules/<name>.md", "alwaysApply": true }`


<!-- source: stateful-artifacts.md -->

---
alwaysApply: true
---

# Stateful Artifacts

## What Counts

- JSON (or similar) state files a skill writes and/or reads across invocations to maintain continuity between runs
- Distinct from the tile's static context artifacts (rules, skills, scripts per `rules/context-artifacts.md`) — those don't change between runs; these do
- Lifecycle and packaging expectations come from `rules/context-artifacts.md`; this rule adds the stateful-specific requirements below

## Required Attributes

- A **schema** documented next to the owner skill (e.g., `skills/<name>/state-schema.md` or a JSON Schema file); no schema, no artifact
- A single **owner skill** responsible for shape changes — shared ownership means no one owns the migration
- A `schema_version` field on every record so migrations are auditable
- A **writer / reader contract** — which skills write, which read, what each promises about field presence, defaults, and format

## Hints, Not Authority

- Artifacts are last-seen snapshots, not ground truth — before acting on a recalled value, verify against the live source (API, DB, filesystem)
- Stale state is the default; assume it until proven fresh
- A skill that recalls a value from an artifact and mutates the world without verifying is the textbook cause of "worked yesterday, wrong today" bugs

## Migration Policy

- Bump `schema_version` for any shape change — don't repurpose a field silently
- Only the owner skill migrates: on its own read, detect old `schema_version`, upgrade the record, rewrite
- Reader skills (non-owners) must not migrate — on encountering an old version, treat it as "no usable prior state" (read-only) and let the next owner-skill run perform the upgrade

## Rename / Removal

- Renaming or removing an artifact follows surface sync (see `rules/context-artifacts.md`): update the owner skill's schema doc, update every reader skill, add a CHANGELOG entry
- Keep reader skills tolerant of missing artifacts — an artifact that was never written (first run) is indistinguishable from one that was removed; both mean "no prior state"


<!-- source: testing-standards.md -->

---
alwaysApply: true
---

# Testing Standards

## Coverage

- Every module gets tests — no untested code ships
- Test file naming follows the project's convention (e.g., `test_*.py`, `*.test.ts`, `*_test.go`)

## Assertions

- Assert **outcomes**, not implementation details
- Test what the code does, not how it does it
- If an internal refactor breaks your tests, the tests were testing the wrong thing

## Determinism

- Tests must be deterministic — no self-generated random test data
- Provide fixed test data; never have the test generate its own inputs randomly
- Flaky tests are bugs — diagnose the root cause, don't retry and hope

## Fixtures

- No binary fixtures checked into the repo
- Build test data programmatically in test setup/fixtures
- For binary files that can't be built programmatically, download them from a URL during test setup

## Independence

- Each test must run independently — no shared mutable state between tests
- Test order must not matter
- Clean up after yourself: temporary files, database state, mock patches
