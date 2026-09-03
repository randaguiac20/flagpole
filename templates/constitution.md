# <PROJECT> constitution

<!--
Principles, not commands. This is what a spec, a plan and a task list are checked *against* — so
every line must be something a reviewer can hold a diff up to and say yes or no.

The commands, the layout and the names live in CLAUDE.md. If a line here also appears there, one of
them is wrong, and they will drift.
-->

## Core principles

### I. <The spec is the source of truth>
<Behaviour comes from the specs. If the code needs to differ, the spec changes first. State what
counts as a feature and what counts as a chore, because chores do not get a spec.>

### II. <Simplicity and restraint>
<The fewest moving parts that satisfy the spec. What was deliberately not built is recorded, with
the signal that would change the decision.>

### III. <Test-first and deterministic> (NON-NEGOTIABLE)
<Every behaviour has a check that failed before the behaviour existed. Nothing depends on wall-clock
time, network availability or ordering. A check that has never failed has not been tested.>

### IV. <Security baseline>
<Least privilege by default. Where secrets may exist and where they may not. What must never appear
in a log or an artifact.>

### V. <Reproducibility>
<The same commit produces the same result. Every version pinned. Rebuildable from an empty
directory, by a documented sequence someone has actually run.>

## Technology and delivery constraints

<The choices that are settled, so no spec re-litigates them.>

## Development workflow

<Branching, commit format, what must pass before a merge, who is asked before anything reaches
outside the repository.>

## Governance

<How this file changes: amendment requires <what>, and every gate in the SDD loop checks against the
version in the tree.>

**Version**: 0.1.0 | **Ratified**: <DATE> | **Last amended**: <DATE>
