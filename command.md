---
description: Explain a code change as a self-contained HTML page with background, intuition,
  code walkthrough, optional trade-offs, and a randomized quiz. Usage /explain-diff [branch|range]
  or /explain-diff --pr <url>.
---

# /explain-diff

Run the explain-diff skill. Produce a rich, interactive, offline-capable HTML explanation of the specified code change.

## What to do

1. Identify the change from the user's argument:
   - `/explain-diff` → explain the working-tree diff against `HEAD`.
   - `/explain-diff <branch>` → explain the diff between the current branch and `<branch>`.
   - `/explain-diff <commit-range>` → explain that commit range.
   - `/explain-diff --pr <url>` → fetch and explain the PR diff.
2. Load the explain-diff skill instructions from `~/.agents/skills/explain-diff/SKILL.md`.
3. Follow the skill workflow: explore the surrounding code, build a narrative, produce a JSON content spec, redact secrets, render with `~/.agents/skills/explain-diff/render.py`, validate, and return the absolute file path.

## Output

A single HTML file saved to:

```
<project-root>/tmp/explain-diff/YYYY-MM-DD-NN-<slug>.html
```

Return the absolute path as a clickable `file://` link, plus a one-sentence summary of what was inspected and any assumptions made.
