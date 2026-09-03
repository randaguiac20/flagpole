# plugin template

Copy `.claude-plugin/plugin.json` to `plugins/<plugin-name>/.claude-plugin/plugin.json`, and
`marketplace.json` to `.claude-plugin/marketplace.json` at the **repository root** — the marketplace
describes where plugins are; the manifest describes one plugin.

Component directories go at the plugin root, never inside `.claude-plugin/`:

```
plugins/<plugin-name>/
├── .claude-plugin/plugin.json
├── skills/<name>/SKILL.md
├── agents/<name>.md
└── hooks/hooks.json          # see the warning below
```

Declare it in the project's `.claude/settings.json` so anyone who trusts the folder gets it:

```json
"extraKnownMarketplaces": { "<marketplace-name>": { "source": { "source": "directory", "path": "." } } },
"enabledPlugins":         { "<plugin-name>@<marketplace-name>": true }
```

## Before you build one

A plugin exists to get components into **more than one repository**. With one repository, `.claude/`
already works and costs nothing. Packaging namespaces everything — `/plugin-name:skill`,
`Agent(plugin-name:agent)` — so every cross-reference has to move with it, and
`claude plugin details <name>` will tell you the token cost added to every session.

**Do not put enforcement in a plugin.** A plugin can be disabled with one command. Guards belong in
the repository's own `settings.json`, next to `permissions.deny`.
