# Decision: managed and user memory examples (`claude-setup/`)

- **Problem / trigger**: the lesson requires seeing every scope. Nothing in *this repo* needs org policy, so the managed example is deliberately generic and installed only on request.
- **Alternative rejected**: putting policy into the project CLAUDE.md (it would be excludable and project-bound; real policy needs the managed location, and *enforcement* needs `managed-settings.json`).
- **Limits**: one short CLAUDE.md + one `managed-settings.json` + one user CLAUDE.md + one user rule. `install-managed.sh` prints sudo commands and never runs them; `install-user.sh` never overwrites.
- **Not done**: no MDM/console delivery, no `claudeMd` key demo (documented in `docs/claude-code/memory.md`). Signal: more than one machine to manage.
- **Verification**: after install, `/context` shows the Managed and User entries; `/doctor` reports no conflicts. Pending: user-run (needs sudo).
