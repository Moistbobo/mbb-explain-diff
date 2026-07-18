# mbb-explain-diff

A self-contained, offline-capable HTML explainer for code changes, designed for use as an [OpenCode](https://opencode.ai/) slash command.

## What it does

`/explain-diff` turns a diff, branch comparison, commit range, or PR diff into a single HTML file with:

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

## Install

1. Clone this repo somewhere on your machine:
   ```bash
   git clone https://github.com/Moistbobo/mbb-explain-diff.git
   ```

2. Symlink the command file into OpenCode:
   ```bash
   ln -s "$(pwd)/mbb-explain-diff/command.md" ~/.config/opencode/commands/explain-diff.md
   ```

3. Symlink the skill directory into `~/.agents/skills/`:
   ```bash
   ln -s "$(pwd)/mbb-explain-diff/skill" ~/.agents/skills/explain-diff
   ```

4. In OpenCode, run:
   ```
   /explain-diff
   ```

## Usage

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

## Credits

Inspired by Geoffrey Litt:

- Original idea / gist: https://gist.github.com/geoffreylitt/a29df1b5f9865506e8952488eac3d524
- Talk / walkthrough: https://www.youtube.com/watch?v=WkBPX-oDMnA
