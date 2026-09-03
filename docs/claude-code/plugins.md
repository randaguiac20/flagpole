# Plugins: `plugins/<name>/` + `.claude-plugin/marketplace.json`

*New to this? [`docs/TUTORIAL.md`](../TUTORIAL.md) lesson 8 builds up to this page.*


Source: https://code.claude.com/docs/en/plugins-reference and https://code.claude.com/docs/en/plugin-marketplaces

## What / where

A plugin is a directory holding the same components a project can hold — `skills/`, `agents/`,
`commands/`, `hooks/hooks.json`, `.mcp.json` — plus an optional manifest at
`.claude-plugin/plugin.json`. Component directories live at the **plugin root**, never inside
`.claude-plugin/`. `${CLAUDE_PLUGIN_ROOT}` resolves to the install directory, so a plugin's hooks and
MCP servers can name their own scripts without knowing where they were installed.

A *marketplace* is how a plugin is found: `.claude-plugin/marketplace.json` listing plugins and their
`source`. A repository can serve its own — `"source": "./plugins/flagpole-tools"` — and declare it in
`.claude/settings.json` so anyone who trusts the folder gets it with no extra prompt:

```json
"extraKnownMarketplaces": { "flagpole-local": { "source": { "source": "directory", "path": "." } } },
"enabledPlugins":         { "flagpole-tools@flagpole-local": true }
```

## When / how far

Trigger: the same components are wanted in **more than one repository**, or you want them versioned
and installed rather than copied. Nothing else. A single repository has `.claude/`, which already
works, needs no manifest, no marketplace and no namespace.

This repository has exactly one plugin, and the honest trigger is the learning goal — that is stated
in `docs/decisions/plugin-flagpole-tools.md` rather than dressed up as a need.

## Our implementation

`plugins/flagpole-tools/` holds the three *procedures* for running Flagpole and the two agents they
delegate to:

```
plugins/flagpole-tools/
├── .claude-plugin/plugin.json
├── skills/{deploy-local,security-scan,e2e}/SKILL.md
└── agents/{deploy-verifier,security-auditor}.md
```

They were **moved, not copied**. Two components stayed in `.claude/` on purpose:
`/add-flag-field` and `api-conventions` are knowledge about *this* codebase, not procedures anyone
else could run.

Every hook stayed in `.claude/` too, and that is the sharpest line in this page. A plugin can be
disabled — `claude plugin disable` is one command — and a guard that can be switched off is not a
guard. The GitOps guard and the secret guard are enforcement, so they stay where enforcement belongs:
`.claude/settings.json`, alongside `permissions.deny`.

## What the namespace costs

Everything the plugin owns is addressed `plugin:component`:

| Before | After |
|---|---|
| `/deploy-local` | `/flagpole-tools:deploy-local` |
| `Agent(deploy-verifier)` | `Agent(flagpole-tools:deploy-verifier)` |

Every cross-reference had to move with it — the skills' `allowed-tools`, their prose, `CLAUDE.md`,
`docs/claude-code/skills.md` and `agents.md`. That is the real price of packaging, and it is the
reason this page says "more than one repository" rather than "for completeness".

## How to verify

```
$ claude plugin marketplace add ./          # `.` is rejected; the leading ./ is required
✔ Successfully added marketplace: flagpole-local (declared in user settings)

$ claude plugin install flagpole-tools@flagpole-local
✔ Successfully installed plugin: flagpole-tools@flagpole-local (scope: user)

$ claude plugin details flagpole-tools
Component inventory
  Skills (3)  deploy-local, e2e, security-scan
  Agents (2)  security-auditor, deploy-verifier
  Hooks (0)   MCP servers (0)   LSP servers (0)
Projected token cost
  Always-on:   ~510 tok   added to every session
```

`claude plugin details` prints a **token cost**, which is the number worth watching: those five
components add ~510 tokens to every session whether or not anyone invokes them. In a session, `/plugin`
lists what is loaded, and changes to anything but a skill's Markdown need `/reload-plugins` or a
restart.
