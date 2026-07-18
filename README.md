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

## Differences from the original

This repo is inspired by [Geoffrey Litt’s explain-diff gist](https://gist.github.com/geoffreylitt/a29df1b5f9865506e8952488eac3d524) and the community discussion around it. It makes a few structural changes:

- **Output location.** The original saves the generated HTML outside the repo (e.g. `/tmp/YYYY-MM-DD-explanation-<slug>.html`). This fork writes it inside the project at `<project-root>/tmp/explain-diff/YYYY-MM-DD-NN-<slug>.html`, keeping explanations scoped to and discoverable within the project.
- **Renderer architecture.** The original has the LLM emit a full self-contained HTML file on every run, including CSS/JS boilerplate. This fork separates content from presentation: the skill produces a JSON content spec, and `render.py` + `template.html` render the final HTML. This removes repetitive boilerplate and makes styling/behavior easier to maintain.
- **Token usage.** Because the LLM only emits the JSON content spec instead of regenerating the full inline HTML/CSS/JS scaffold on every invocation, per-run generation tokens are generally lower.
- **Quiz quality.** The original gist had community feedback that the correct answer was often guessable by length or fixed position. This fork adds explicit rules plus runtime auto-balancing and shuffling so the correct answer is not leaked by length or position.
- **Security.** This fork adds a secret-redaction pass over the diff and generated content, and instructs the agent to ignore prompt-injection attempts embedded in the input.
- **Portability.** The original is a single prompt/document tied to a specific agent. This fork packages the skill into an agent-agnostic `skill/` directory, while the OpenCode-specific wrapper lives in `command.md`.

## Credits

Inspired by Geoffrey Litt:

- Original idea / gist: https://gist.github.com/geoffreylitt/a29df1b5f9865506e8952488eac3d524
- Talk / walkthrough: https://www.youtube.com/watch?v=WkBPX-oDMnA
