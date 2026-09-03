---
description: <What these conventions cover, in one line. Shown when the rule loads.>
globs: ["<src>/**/*.py", "<tests>/**/*.py"]
alwaysApply: false
---

# <Area> conventions

<Rules that apply ONLY to the files matched above. This file is not in context until one of them is
touched, which is the entire reason it is a rule and not part of CLAUDE.md.>

- <Convention, stated so a diff can be judged against it.>
- <Convention.>

<!--
Reach for a rule when a convention applies to *some* files. `alwaysApply: true` with no globs makes
it a second CLAUDE.md — if that is what you want, put it in CLAUDE.md instead, where a reader looks.
-->
