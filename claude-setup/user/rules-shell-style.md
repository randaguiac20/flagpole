---
paths:
  - "**/*.sh"
---

# My shell style (user rule example: ~/.claude/rules/shell-style.md)

- `#!/usr/bin/env bash` + `set -euo pipefail`; quote every variable; run shellcheck before claiming a script works.
