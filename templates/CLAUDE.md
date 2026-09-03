# <PROJECT NAME>

<One sentence: what this is, and what the reader is meant to learn or do.>

@docs/architecture.md

## Where things are

| Path | What |
|---|---|
| `<src>/` | <the codebases, one row each> |
| `<specs>/` | <if you use spec-driven development, say the source of truth lives here> |
| `.claude/` | rules, agents, skills, hooks, settings |

## Commands

```
make bootstrap      # tools check, dependencies, hooks installed
make dev            # <ports, from a single source>
make test           # <all tests>
```

## Conventions that must hold

- <The two or three rules that a change is judged against.>
- <Who owns what: which directory a human edits, and which is generated or reconciled.>
- <Where secrets may and may not appear.>
- Verify every claim by running the command and showing the output.

## Names (use exactly)

<Services, images, namespaces, hosts. Ambiguity here costs more than anywhere else in this file:
if Claude has to guess a name, it will guess consistently and wrongly.>

<!--
Keep this file under ~150 lines. It is in context for every request of every session, so a line here
is the most expensive line in the repository. Three tests before adding one:
  1. Does EVERY session need it? If only sessions touching Python need it, it is a rule.
  2. Is it a fact, or a procedure? A procedure is a skill.
  3. Is it enforcement? Then it belongs in settings.json or a hook — prose is a request, not a rule.
-->
