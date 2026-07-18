# mbb-explain-diff

A self-contained, offline-capable HTML explainer for code changes. It works as a portable skill for agent harnesses that support skill directories with a `SKILL.md` entrypoint.

## What it does

`explain-diff` turns a diff, branch comparison, commit range, or PR diff into a single HTML file with:

- **Background** — the system context needed to understand the change
- **Intuition** — the core idea before implementation details
- **Code** — a walkthrough grouped by concept, with precise file and line references
- **Trade-offs** — when there are notable design decisions (optional)
- **Quiz** — up to five randomized, interactive questions

The rendered HTML has no external dependencies: all CSS, JavaScript, and assets are inline, so it works from `file://` and without an internet connection.

## Demo

You can preview a generated example here:

- **Gist:** https://gist.github.com/Moistbobo/e0be30c4792eae13100434c5149d02cb
- **Preview:** https://www.hyouji.moe/?gist= (paste the gist URL or ID)

> When using [hyouji](https://www.hyouji.moe/) to preview, you must allow scripts for the quiz interactions to work.

## Supported harnesses

The skill itself (`skill/` in this repo) uses the common `SKILL.md` + supporting files layout, which is recognized by multiple agent tools. Where applicable, the slash command is also provided.

### OpenCode

Symlink the command file and the skill directory:

```bash
ln -s "$(pwd)/mbb-explain-diff/command.md" ~/.config/opencode/commands/explain-diff.md
ln -s "$(pwd)/mbb-explain-diff/skill" ~/.agents/skills/explain-diff
```

Then run:

```
/explain-diff
```

### Claude Code

Symlink the skill directory:

```bash
ln -s "$(pwd)/mbb-explain-diff/skill" ~/.claude/skills/explain-diff
```

Then run:

```
/explain-diff
```

### Codex

Symlink the skill directory into `~/.agents/skills/` (or a repo-level `.codex/skills/`):

```bash
ln -s "$(pwd)/mbb-explain-diff/skill" ~/.agents/skills/explain-diff
```

Codex will load the skill by name/description and use it when the task matches.

### Pi

Pi has no public skill/instruction harness, so this skill cannot be used with Pi directly.

## Usage

Once installed in your agent harness:

```
/explain-diff                    # Explain working-tree diff against HEAD
/explain-diff <branch>           # Explain diff between current branch and <branch>
/explain-diff <commit-range>     # Explain the given commit range
/explain-diff --pr <url>         # Fetch and explain a PR diff
```

The rendered file is saved to:

```
<project-root>/tmp/explain-diff/YYYY-MM-DD-NN-<slug>.html
```

## Repo layout

```
mbb-explain-diff/
├── README.md
├── command.md          # OpenCode slash command definition
└── skill/
    ├── SKILL.md        # Portable skill instructions
    ├── render.py       # HTML renderer
    └── template.html   # Inline HTML template
```

`command.md` is only needed for OpenCode. The `skill/` directory is the agent-agnostic part.

## Credits

Inspired by Geoffrey Litt:

- Original idea / gist: https://gist.github.com/geoffreylitt/a29df1b5f9865506e8952488eac3d524
- Talk / walkthrough: https://www.youtube.com/watch?v=WkBPX-oDMnA
