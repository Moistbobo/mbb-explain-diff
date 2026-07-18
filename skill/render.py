#!/usr/bin/env python3
"""Render an explain-diff content spec into a self-contained HTML file."""

import argparse
import base64
import json
import os
import re
import statistics
import subprocess
import sys
import unicodedata
from datetime import datetime
from html import escape
from pathlib import Path

DEFAULT_BRANCHES = {"main", "master", "trunk", "testnet", "production", "release"}

CALLOUT_EMOJIS = {
    "⚠️": "warning",
    "🚨": "danger",
    "❗": "warning",
    "✅": "success",
    "✔️": "success",
    "💡": "callout",
    "📝": "callout",
    "ℹ️": "callout",
    "🎯": "callout",
    "⚠": "warning",
}

ALLOWED_TAGS = {
    "div", "span", "p", "br", "hr", "h1", "h2", "h3", "h4", "h5", "h6",
    "ul", "ol", "li", "dl", "dt", "dd", "strong", "em", "b", "i", "u",
    "s", "strike", "del", "ins", "code", "pre", "blockquote", "q",
    "table", "thead", "tbody", "tfoot", "tr", "th", "td", "caption",
    "colgroup", "col", "abbr", "cite", "dfn", "kbd", "mark", "samp",
    "small", "sub", "sup", "time", "var", "wbr",
}

ALLOWED_ATTRS = {"class", "id", "role", "aria-label", "aria-labelledby", "aria-hidden"}


def slugify(text, max_len=40):
    if not text:
        return "change"
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    text = text[:max_len]
    return text.rstrip("-") or "change"


def git_root(cwd=None):
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def git_branch(cwd=None):
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip() or None
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def git_short_sha(cwd=None):
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def compute_output_path(root, branch, topic=None):
    today = datetime.now().strftime("%Y-%m-%d")
    out_dir = Path(root) / "tmp" / "explain-diff"
    out_dir.mkdir(parents=True, exist_ok=True)

    if topic:
        slug = slugify(topic)
    elif branch:
        if branch in DEFAULT_BRANCHES:
            raise ValueError(
                f"Branch '{branch}' is a default branch. Provide --topic <slug>."
            )
        slug = slugify(branch)
    else:
        slug = f"detached-{git_short_sha(root)}"

    existing = sorted(out_dir.glob(f"{today}-*.html"))
    max_n = -1
    for f in existing:
        m = re.match(rf"^{re.escape(today)}-(\d{{2}})-", f.name)
        if m:
            max_n = max(max_n, int(m.group(1)))

    nn = f"{max_n + 1:02d}"
    candidate = out_dir / f"{today}-{nn}-{slug}.html"

    # Guard against collisions in rare race conditions.
    while candidate.exists():
        max_n += 1
        nn = f"{max_n + 1:02d}"
        candidate = out_dir / f"{today}-{nn}-{slug}.html"

    return candidate


def _is_callout(line):
    stripped = line.lstrip(">").strip()
    for emoji, cls in CALLOUT_EMOJIS.items():
        if stripped.startswith(emoji):
            return True, cls, stripped[len(emoji):].strip()
    return False, None, None


def _parse_inline(text):
    # Escape HTML first, then selectively reintroduce formatting.
    text = escape(text)

    # Protect inline code spans before applying emphasis/strikethrough,
    # so underscores/asterisks inside backticks are preserved literally.
    code_spans = []

    def code_repl(m):
        code_spans.append(m.group(1))
        return f"\x00code{len(code_spans) - 1}\x00"

    text = re.sub(r"`([^`]+)`", code_repl, text)

    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"__(.+?)__", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*(.+?)\*(?!\*)", r"<em>\1</em>", text)
    text = re.sub(r"(?<!_)_(.+?)_(?!_)", r"<em>\1</em>", text)
    text = re.sub(r"~~(.+?)~~", r"<s>\1</s>", text)

    # Restore protected code spans.
    def code_restore(m):
        idx = int(m.group(1))
        return f"<code>{code_spans[idx]}</code>"

    text = re.sub(r"\x00code(\d+)\x00", code_restore, text)

    # Links: only allow internal anchors.
    def link_repl(m):
        label = m.group(1)
        url = m.group(2)
        if url.startswith("#"):
            return f'<a href="{escape(url)}">{escape(label)}</a>'
        return f'<a href="#">{escape(label)}</a>'
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link_repl, text)
    return text


def _render_table(lines):
    rows = []
    for line in lines:
        cells = [c.strip() for c in line.strip("|").split("|")]
        rows.append(cells)
    if len(rows) < 2:
        return ""
    header = rows[0]
    out = ['<table>\n<thead>\n<tr>']
    for h in header:
        out.append(f"<th>{_parse_inline(h)}</th>")
    out.append("</tr>\n</thead>\n<tbody>")
    for row in rows[2:]:
        out.append("<tr>")
        for i, cell in enumerate(row):
            tag = "th" if i == 0 and len(row) == len(header) else "td"
            out.append(f"<{tag}>{_parse_inline(cell)}</{tag}>")
        out.append("</tr>")
    out.append("</tbody>\n</table>")
    return "".join(out)


def _render_list(lines, ordered=False):
    tag = "ol" if ordered else "ul"
    items = []
    current = ""
    for line in lines:
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        marker_re = r"^\d+\.\s+" if ordered else r"^[-*+]\s+"
        content = re.sub(marker_re, "", stripped)
        if indent >= 2 and current:
            # Continuation / nested handling is simplified; treat as continuation.
            current += " " + content
        else:
            if current:
                items.append(current)
            current = content
    if current:
        items.append(current)

    out = [f"<{tag}>"]
    for item in items:
        out.append(f"<li>{_parse_inline(item)}</li>")
    out.append(f"</{tag}>")
    return "\n".join(out)


def _normalize_markdown_escapes(md):
    """Convert literal \\n, \\t, \\r escape sequences into real whitespace.

    Some LLMs emit Markdown as a JSON string with literal escape characters
    rather than actual newlines. This normalization fixes that without altering
    real line breaks if they already exist.
    """
    if "\n" not in md and "\\n" in md:
        md = md.replace("\\n", "\n").replace("\\t", "\t").replace("\\r", "\r")
    return md


def render_code_block(code, language=""):
    code = redact_secrets(code)
    code = escape(code)
    if not code.endswith("\n"):
        code += "\n"
    lang_attr = f' class="language-{escape(language)}"' if language else ""
    return f'<pre><code{lang_attr}>{code}</code></pre>'


def render_code_section(code_spec):
    """Render the Code section from either a Markdown string or structured object."""
    if isinstance(code_spec, str):
        return redact_secrets(markdown_to_html(code_spec))

    if not isinstance(code_spec, dict):
        return ""

    parts = []

    intro = code_spec.get("intro", "")
    if intro:
        parts.append(redact_secrets(markdown_to_html(intro)))

    files = code_spec.get("files", [])
    if files:
        rows = []
        for f in files:
            path = escape(f.get("path", ""))
            line_range = escape(f.get("line_range", ""))
            description = redact_secrets(escape(f.get("description", "")))
            path_with_lines = f"{path}:{line_range}" if line_range else path
            rows.append(
                f"<tr><td><code>{path_with_lines}</code></td>"
                f"<td>{description}</td></tr>"
            )
        parts.append(
            '<table class="files-table">\n'
            '<thead><tr><th>File</th><th>What changed</th></tr></thead>\n'
            '<tbody>\n' + "\n".join(rows) + "\n</tbody>\n</table>"
        )

    for group in code_spec.get("groups", []):
        heading = group.get("heading", "")
        text = group.get("text", "")
        blocks = group.get("code_blocks", [])

        if heading:
            parts.append(f"<h3>{escape(heading)}</h3>")
        if text:
            parts.append(redact_secrets(markdown_to_html(text)))
        for block in blocks:
            parts.append(render_code_block(block.get("code", ""), block.get("language", "")))

    return "\n\n".join(parts)


def markdown_to_html(md):
    if not md or not md.strip():
        return ""

    md = _normalize_markdown_escapes(md)

    # Allow a small whitelist of inline HTML to pass through for diagrams,
    # then run the markdown parser over the rest.
    md = _sanitize_inline_html(md)

    lines = md.splitlines()
    out = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        # Horizontal rule
        if re.match(r"^(\*\*\*|---|___)\s*$", stripped):
            out.append("<hr>")
            i += 1
            continue

        # Code block
        fence = re.match(r"^```(\w*)", stripped)
        if fence:
            lang = fence.group(1)
            code_lines = []
            i += 1
            while i < len(lines) and not re.match(r"^```\s*$", lines[i]):
                code_lines.append(lines[i])
                i += 1
            i += 1  # skip closing fence
            code = "\n".join(code_lines)
            code = escape(code)
            if not code.endswith("\n"):
                code += "\n"
            lang_attr = f' class="language-{escape(lang)}"' if lang else ""
            out.append(f'<pre><code{lang_attr}>{code}</code></pre>')
            continue

        # Header
        header = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if header:
            level = len(header.group(1))
            text = header.group(2)
            out.append(f"<h{level}>{_parse_inline(text)}</h{level}>")
            i += 1
            continue

        # Table
        if "|" in stripped:
            table_lines = []
            while i < len(lines) and "|" in lines[i]:
                table_lines.append(lines[i])
                i += 1
            out.append(_render_table(table_lines))
            continue

        # Callout / blockquote
        if stripped.startswith(">"):
            is_callout, cls, content = _is_callout(stripped)
            quote_lines = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                quote_lines.append(lines[i].lstrip(">").strip())
                i += 1
            body = " ".join(_parse_inline(l) for l in quote_lines)
            if is_callout:
                title = cls.capitalize()
                out.append(
                    f'<div class="callout {cls}">'
                    f'<div class="callout-title">{title}</div>'
                    f'{body}</div>'
                )
            else:
                out.append(f"<blockquote>{body}</blockquote>")
            continue

        # Lists
        if re.match(r"^[-*+]\s+", stripped):
            list_lines = []
            while i < len(lines) and (lines[i].strip() == "" or re.match(r"^[-*+]\s+", lines[i].strip())):
                if lines[i].strip():
                    list_lines.append(lines[i])
                i += 1
            out.append(_render_list(list_lines, ordered=False))
            continue

        if re.match(r"^\d+\.\s+", stripped):
            list_lines = []
            while i < len(lines) and (lines[i].strip() == "" or re.match(r"^\d+\.\s+", lines[i].strip())):
                if lines[i].strip():
                    list_lines.append(lines[i])
                i += 1
            out.append(_render_list(list_lines, ordered=True))
            continue

        # Paragraph (allow line continuations)
        para_lines = []
        while i < len(lines) and lines[i].strip():
            para_lines.append(lines[i])
            i += 1
        para = " ".join(para_lines)
        out.append(f"<p>{_parse_inline(para)}</p>")
        continue

    return "\n\n".join(out)


def _sanitize_inline_html(text):
    """Pass through allowed HTML tags with allowed attributes; escape others."""
    tag_re = re.compile(
        r"(<(/?)([a-zA-Z][a-zA-Z0-9]*)"
        r"((?:\s+[a-zA-Z_:][-a-zA-Z0-9_:.]*(?:\s*=\s*(?:\"[^\"]*\"|'[^']*'|[^\s>\"']+))?)*)"
        r"\s*(/?)>)",
        re.S,
    )

    def repl(m):
        full = m.group(1)
        closing = m.group(2)
        tag = m.group(3).lower()
        attrs = m.group(4)
        self_closing = m.group(5)

        if tag not in ALLOWED_TAGS:
            return escape(full)

        cleaned_attrs = []
        for attr_m in re.finditer(
            r"([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*(?:=\s*(?:\"([^\"]*)\"|'([^']*)'|([^\s>\"']+)))?",
            attrs,
        ):
            name = attr_m.group(1).lower()
            val = attr_m.group(2) or attr_m.group(3) or attr_m.group(4) or ""
            if name not in ALLOWED_ATTRS:
                continue
            if name in ("href", "src", "action"):
                # Only internal anchors allowed.
                if not val.startswith("#"):
                    continue
            cleaned_attrs.append(f'{name}="{escape(val)}"')

        attr_str = " " + " ".join(cleaned_attrs) if cleaned_attrs else ""
        slash = "/" if self_closing else ""
        close_slash = "/" if closing else ""
        return f"<{close_slash}{tag}{attr_str}{slash}>"

    return tag_re.sub(repl, text)


def redact_secrets(text):
    """Best-effort redaction of obvious secret patterns."""
    # OpenAI-style API keys
    text = re.sub(r"\bsk-[a-zA-Z0-9]{32,}\b", "<REDACTED-API-KEY>", text)
    # Generic high-entropy hex/base64-ish tokens
    text = re.sub(r"\b[a-f0-9]{32,64}\b", "<REDACTED-TOKEN>", text)
    text = re.sub(r"\b[A-Za-z0-9+/]{40,}={0,2}\b", "<REDACTED-TOKEN>", text)
    # Password-looking assignments
    text = re.sub(r"(password|secret|token|api[_-]?key)\s*=\s*['\"][^'\"]{8,}['\"]", r"\1 = '<REDACTED>'", text, flags=re.IGNORECASE)
    return text


def validate_html(html):
    unsafe_patterns = [
        (r"<script\b[^>]*\bsrc\s*=", "external script source"),
        (r"<[^>]+\son\w+\s*=", "inline event handler"),
        (r"javascript:", "javascript: URL"),
        (r"\beval\s*\(", "eval() call"),
        (r"new\s+Function\s*\(", "new Function()"),
        (r"<iframe\b", "iframe tag"),
        (r"<object\b", "object tag"),
        (r"<embed\b", "embed tag"),
        (r"\bsetTimeout\s*\(\s*['\"]", "setTimeout with string"),
        (r"\bsetInterval\s*\(\s*['\"]", "setInterval with string"),
        (r"href\s*=\s*['\"]?https?://", "external http link"),
        (r"src\s*=\s*['\"]?https?://", "external http source"),
        (r"url\s*\(\s*['\"]?https?://", "external CSS url()"),
    ]
    for pattern, description in unsafe_patterns:
        if re.search(pattern, html, re.IGNORECASE):
            raise ValueError(f"Unsafe pattern detected: {description}")

    # Verify every pre block has white-space styling.
    for pre in re.finditer(r"<pre\b[^>]*>", html, re.IGNORECASE):
        tag = pre.group(0)
        # We rely on CSS rules rather than inline styles, so ensure global pre rule exists.
        # The template already defines white-space: pre for pre.
        pass

    if "white-space: pre" not in html and "white-space: pre-wrap" not in html:
        raise ValueError("Missing white-space rule for pre blocks")


def _trim_trailing_clause(text):
    """Remove trailing prepositional clauses that can be safely dropped."""
    clauses = [
        " in this scenario.",
        " in this case.",
        " for this change.",
        " for this component.",
        " within this context.",
        " in this context.",
        " in this situation.",
    ]
    for clause in clauses:
        if text.endswith(clause):
            return text[: -len(clause)] + "."
    return text


def _shorten_option(text):
    """Apply safe, meaning-preserving compression patterns to an option."""
    text = re.sub(r"\bused in order to\b", "to", text, flags=re.IGNORECASE)
    text = re.sub(r"\bin order to\b", "to", text, flags=re.IGNORECASE)
    text = re.sub(r"\bwhich is used to\b", "to", text, flags=re.IGNORECASE)
    text = re.sub(r"\bwhich means that\b", "so", text, flags=re.IGNORECASE)
    text = re.sub(r"\bthis means that\b", "so", text, flags=re.IGNORECASE)
    text = re.sub(r"\btherefore\b", "so", text, flags=re.IGNORECASE)
    text = re.sub(r"\bas a result\b", "so", text, flags=re.IGNORECASE)
    text = re.sub(r"\bIt is\b", "It's", text)
    text = re.sub(r"\bthat is\b", "that's", text, flags=re.IGNORECASE)
    text = re.sub(r"\bhas been\b", "is", text, flags=re.IGNORECASE)
    text = re.sub(r"\bwill be\b", "is", text, flags=re.IGNORECASE)
    text = re.sub(r"\bkeyboard-focusable\b", "focusable", text)
    return text


def _pad_option(text, phrase):
    """Append a neutral prepositional phrase, preserving terminal punctuation."""
    if text.endswith("."):
        return text[:-1] + phrase
    return text + phrase


def rebalance_quiz_options(quiz):
    """Auto-correct length bias in quiz options.

    The main defense is the skill prompt: the LLM should author balanced
    options so the correct answer is not the longest. This function is a
    deterministic last-resort safety net applied at render time. If the
    correct option is still the longest (including ties), it first tries
    safe compression, then pads the shortest distractors with neutral
    prepositional phrases until the correct option is no longer the longest.
    """
    pad_phrases = [
        " in this scenario.",
        " for this change.",
        " within this context.",
        " for this component.",
    ]
    changed_any = False

    for q in quiz:
        options = list(q["options"])
        ci = q["correct_index"]

        def correct_is_longest():
            lens = [len(o) for o in options]
            return lens[ci] == max(lens)

        if not correct_is_longest():
            continue

        # First pass: try safe shortening of the correct option.
        shortened = _shorten_option(_trim_trailing_clause(options[ci]))
        if len(shortened) < len(options[ci]):
            options[ci] = shortened
            changed_any = True

        # Second pass: pad shortest distractors until the correct option is
        # no longer the longest. Cap iterations to avoid runaway expansion.
        attempts = 0
        while correct_is_longest() and attempts < 20:
            lens = [len(o) for o in options]
            others = [i for i in range(4) if i != ci]
            shortest = min(others, key=lambda i: lens[i])
            phrase = pad_phrases[attempts % len(pad_phrases)]
            options[shortest] = _pad_option(options[shortest], phrase)
            attempts += 1
            changed_any = True

        q["options"] = options

    return quiz, changed_any


def embed_quiz_data(quiz):
    """Encode quiz data so it can be safely embedded inside a script tag."""
    raw = json.dumps(quiz or [], ensure_ascii=False, separators=(",", ":"))
    # Guard against </script> and other tag-closing sequences.
    raw = raw.replace("</script>", "<\\/script>")
    return raw


def main():
    parser = argparse.ArgumentParser(description="Render explain-diff content spec to HTML")
    parser.add_argument("--spec", "-s", required=True, help="Path to JSON content spec")
    parser.add_argument("--topic", "-t", help="Topic slug for default branches")
    parser.add_argument("--cwd", help="Working directory for git resolution")
    parser.add_argument("--output", "-o", help="Override output path")
    args = parser.parse_args()

    spec_path = Path(args.spec).expanduser().resolve()
    with open(spec_path, "r", encoding="utf-8") as f:
        spec = json.load(f)

    # Validate required fields.
    for key in ("title", "summary", "background", "intuition", "code"):
        if key not in spec:
            raise ValueError(f"Missing required field in spec: {key}")

    quiz = spec.get("quiz") or []
    for idx, q in enumerate(quiz):
        opts = q.get("options", [])
        if len(opts) != 4:
            raise ValueError(f"Question {idx}: must have exactly 4 options")
        ci = q.get("correct_index", -1)
        if not (0 <= ci < 4):
            raise ValueError(f"Question {idx}: correct_index out of range")
        exps = q.get("explanations", [])
        if len(exps) != 4:
            raise ValueError(f"Question {idx}: must have exactly 4 explanations")

    quiz, rebalanced = rebalance_quiz_options(quiz)
    if rebalanced:
        print(
            "Note: quiz option lengths were auto-balanced to avoid giving away the correct answer by length.",
            file=sys.stderr,
        )

    root = git_root(args.cwd) or args.cwd or os.getcwd()
    branch = git_branch(args.cwd)

    if branch in DEFAULT_BRANCHES and not args.topic:
        print(
            f"Error: current branch '{branch}' is a default branch. "
            "Provide --topic <slug>.",
            file=sys.stderr,
        )
        sys.exit(1)

    output_path = args.output
    if not output_path:
        output_path = compute_output_path(root, branch, args.topic)
    output_path = Path(output_path).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert markdown sections to HTML and redact secrets.
    background_html = redact_secrets(markdown_to_html(spec["background"]))
    intuition_html = redact_secrets(markdown_to_html(spec["intuition"]))
    code_html = render_code_section(spec["code"])
    trade_offs_html = redact_secrets(markdown_to_html(spec.get("trade_offs")))

    if trade_offs_html.strip():
        trade_offs_sidebar = '        <li><a href="#trade-offs">Trade-offs</a></li>\n'
        trade_offs_section = (
            '    <section id="trade-offs" aria-labelledby="trade-offs-heading">\n'
            '      <h2 id="trade-offs-heading">Trade-offs</h2>\n'
            f"      {trade_offs_html}\n"
            "    </section>\n"
        )
    else:
        trade_offs_sidebar = ""
        trade_offs_section = ""

    skill_dir = Path(__file__).parent
    template_path = skill_dir / "template.html"
    with open(template_path, "r", encoding="utf-8") as f:
        template = f.read()

    html = (
        template
        .replace("{{TITLE}}", escape(spec["title"]))
        .replace("{{SUMMARY}}", escape(spec["summary"]))
        .replace("{{BACKGROUND}}", background_html)
        .replace("{{INTUITION}}", intuition_html)
        .replace("{{CODE}}", code_html)
        .replace("{{TRADE_OFFS_SIDEBAR}}", trade_offs_sidebar)
        .replace("{{TRADE_OFFS_SECTION}}", trade_offs_section)
        .replace("{{QUIZ_DATA}}", embed_quiz_data(quiz))
    )

    validate_html(html)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(output_path)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
