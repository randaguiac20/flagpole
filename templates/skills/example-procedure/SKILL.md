---
name: <procedure-name>
description: <What it does and when to use it. If disable-model-invocation is false, this text is in context every request — keep it short and specific.>
disable-model-invocation: true
argument-hint: "[<arg>]"
allowed-tools: Bash(make *), Read
---

<One line: what the user gets when this finishes.>

Current state (do not skip):

!`<a command whose output the procedure needs — it runs when the skill loads and is injected here>`

Steps, in order, showing the command and its last lines each time:

1. `<command>` — <what it does>. Stop on failure.
2. <step>
3. <The step that says what NOT to do, and why. This is usually the most valuable line in a skill.>
4. Finish with <the evidence that it worked: a URL, a revision, a table>.

<!--
Reach for a skill when you have pasted the same playbook three times, or when Claude needs reference
material only sometimes. `disable-model-invocation: true` for anything with side effects — it stays
invisible until a person types it.

Arguments are free text: `$0` and `$1` split on whitespace, so use `$ARGUMENTS` unless the
argument-hint really is positional. Invoke it for real before believing it works.
-->
