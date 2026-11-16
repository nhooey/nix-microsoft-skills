#!/usr/bin/env python3
"""
checks.skills-valid: assert the `all` aggregate is well-formed.

Usage:
  check_skills.py SHARE_DIR EXPECTED_COUNT EXPECTED_LIST

  SHARE_DIR       share/claude-skills directory inside the symlinkJoin output
  EXPECTED_COUNT  expected skill count
  EXPECTED_LIST   file with one expected skill name per line

Fails loudly on:
  - count mismatch, or a missing or unexpected skill directory
  - missing SKILL.md
  - frontmatter that isn't a block of top-level `key: value` entries
  - frontmatter missing `name:` or `description:`, or either not a string
  - frontmatter `name:` not matching the containing directory

The frontmatter parser reads the YAML subset skill files use: plain,
single-quoted and double-quoted scalars (on one line or folded over
several), literal and folded block scalars, and nested blocks or flow
collections (kept as non-string values). Anchors, aliases, tags, reserved
indicators, duplicate keys and a plain scalar holding `: ` are errors,
as they would be (or would change the value) under a full YAML parser.
"""

import itertools
import json
import os
import re
import sys
from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping, Tuple, Union


FRONTMATTER_RE = re.compile(r"\A---[ \t]*\n(.*?)\n?^---[ \t]*$", re.DOTALL | re.MULTILINE)
KEY_RE = re.compile(r"\A([A-Za-z0-9_][A-Za-z0-9_.-]*):(?:[ \t]+(.*))?\Z")
BLOCK_RE = re.compile(r"\A([|>])([+-]?)[1-9]?([+-]?)[ \t]*(?:#.*)?\Z")
# A quoted scalar, then optionally a comment, which needs a space before `#`.
DOUBLE_QUOTED_RE = re.compile(r'\A"((?:[^"\\]|\\.)*)"(?:[ \t]+#.*)?[ \t]*\Z', re.DOTALL)
SINGLE_QUOTED_RE = re.compile(r"\A'((?:[^']|'')*)'(?:[ \t]+#.*)?[ \t]*\Z", re.DOTALL)


class NonScalar:
    """A nested mapping, sequence or flow collection: present, not a string."""

    def __repr__(self):
        return "<non-scalar>"


NON_SCALAR = NonScalar()

Value = Union[str, None, NonScalar]


@dataclass(frozen=True, slots=True)
class Parsed:
    fields: Mapping[str, Value]


@dataclass(frozen=True, slots=True)
class Invalid:
    problems: Tuple[str, ...]


def is_top_level(line):
    return bool(line) and line[0] not in " \t#"


def is_blank(line):
    return not line.strip() or line.lstrip().startswith("#")


def dedent(lines):
    content = tuple(ln for ln in lines if ln.strip())
    indent = min((len(ln) - len(ln.lstrip(" \t")) for ln in content), default=0)
    return tuple(ln[indent:] for ln in lines)


def fold(lines):
    """Join lines as YAML folding does: one newline per blank line, else a space."""
    paragraphs = (
        " ".join(group)
        for blank, group in itertools.groupby(lines, key=lambda ln: not ln.strip())
        if not blank
    )
    return "\n".join(paragraphs)


def block_scalar(style, chomp, lines):
    body = dedent(lines)
    trailing = len(body) - len(tuple(itertools.dropwhile(lambda ln: not ln.strip(), reversed(body))))
    content = body[: len(body) - trailing]
    text = "\n".join(content) if style == "|" else fold(content)
    if not text:
        return ""
    if chomp == "-":
        return text
    if chomp == "+":
        return text + "\n" * (trailing + 1)
    return text + "\n"


def double_quoted(lineno, raw):
    match = DOUBLE_QUOTED_RE.match(raw)
    try:
        if match:
            return json.loads(f'"{match.group(1)}"')
    except ValueError:
        pass
    return Invalid((f"line {lineno}: double-quoted scalar doesn't parse: {raw!r}",))


def single_quoted(lineno, raw):
    match = SINGLE_QUOTED_RE.match(raw)
    if not match:
        return Invalid((f"line {lineno}: single-quoted scalar doesn't parse: {raw!r}",))
    return match.group(1).replace("''", "'")


def plain(lineno, raw):
    text = re.sub(r"[ \t]+#.*\Z", "", raw)
    if text[0] in "@`":
        return Invalid((f"line {lineno}: {text[0]!r} is reserved at the start of a scalar",))
    if text[0] in "&*!":
        return Invalid((f"line {lineno}: anchors, aliases and tags aren't supported",))
    if text[0] in "[{":
        return NON_SCALAR
    if ": " in text or text.endswith(":"):
        return Invalid((f"line {lineno}: plain scalar contains ': ' (quote it): {text!r}",))
    return text


def entry_value(lineno, rest, continuation):
    """Value of one top-level entry: its text after `key:` and its indented lines."""
    block = BLOCK_RE.match(rest)
    folded = " ".join((rest, *(ln.strip() for ln in continuation if ln.strip()))).strip()
    if not rest:
        return NON_SCALAR if any(not is_blank(ln) for ln in continuation) else None
    if block:
        return block_scalar(block.group(1), block.group(2) or block.group(3), continuation)
    if rest.startswith('"'):
        return double_quoted(lineno, folded)
    if rest.startswith("'"):
        return single_quoted(lineno, folded)
    return plain(lineno, folded)


def parse_entry(entry):
    """(lineno, key, value) for one entry, or an Invalid naming its first line."""
    (lineno, head), *rest = entry
    match = KEY_RE.match(head.rstrip())
    if not match:
        return Invalid((f"line {lineno}: not a `key: value` line: {head!r}",))
    text = (match.group(2) or "").strip()
    # A `#` straight after `key: ` opens a comment, leaving the value empty.
    value = entry_value(lineno, "" if text.startswith("#") else text, tuple(ln for _, ln in rest))
    return value if isinstance(value, Invalid) else (lineno, match.group(1), value)


def parse_frontmatter(text):
    """Parsed fields of a SKILL.md's frontmatter, or Invalid with the reasons."""
    match = FRONTMATTER_RE.match(text.replace("\r\n", "\n"))
    if not match:
        return Invalid(("no frontmatter block between `---` lines",))
    # A `#` in the first column is a comment line wherever it falls, even
    # between a key and its indented continuation.
    numbered = tuple(
        (n, ln)
        for n, ln in enumerate(match.group(1).split("\n"), start=2)
        if not ln.startswith("#")
    )
    leading = tuple(itertools.takewhile(lambda p: not is_top_level(p[1]), numbered))
    stray = tuple(f"line {n}: indented line before any key" for n, ln in leading if not is_blank(ln))
    body = numbered[len(leading) :]
    groups = itertools.accumulate((int(is_top_level(ln)) for _, ln in body))
    entries = tuple(
        tuple(pair for _, pair in group)
        for _, group in itertools.groupby(zip(groups, body), key=lambda g: g[0])
    )
    parsed = tuple(parse_entry(e) for e in entries)
    invalid = tuple(p for result in parsed if isinstance(result, Invalid) for p in result.problems)
    good = tuple(result for result in parsed if not isinstance(result, Invalid))
    keys = tuple(key for _, key, _ in good)
    duplicates = tuple(
        f"line {n}: duplicate key `{key}`" for i, (n, key, _) in enumerate(good) if key in keys[:i]
    )
    problems = stray + invalid + duplicates
    if problems:
        return Invalid(problems)
    return Parsed(MappingProxyType({key: value for _, key, value in good}))


def field_errors(name, fields, key, check_value=None):
    value = fields.get(key)
    if key not in fields:
        return (f"{name}: frontmatter missing `{key}:`",)
    if not isinstance(value, str) or not value.strip():
        return (f"{name}: frontmatter `{key}:` is not a non-empty string ({value!r})",)
    return check_value(value) if check_value else ()


def skill_errors(name, skill_md):
    """Problems with one skill directory, given its SKILL.md text (None if absent)."""
    if skill_md is None:
        return (f"{name}: SKILL.md missing",)
    match parse_frontmatter(skill_md):
        case Invalid(problems):
            return tuple(f"{name}: frontmatter: {p}" for p in problems)
        case Parsed(fields):
            name_matches = lambda v: () if v == name else (
                f"{name}: frontmatter name={v!r} != directory name",
            )
            return field_errors(name, fields, "name", name_matches) + field_errors(
                name, fields, "description"
            )


def listing_errors(actual, expected, expected_count):
    """Problems with the set of skill directory names against the pins."""
    count = (
        ()
        if len(actual) == expected_count
        else (f"directory count: expected {expected_count}, got {len(actual)} ({sorted(actual)})",)
    )
    missing = sorted(set(expected) - set(actual))
    extra = sorted(set(actual) - set(expected))
    return (
        count
        + ((f"missing skills: {missing}",) if missing else ())
        + ((f"unexpected skills: {extra}",) if extra else ())
    )


def validate(skills, expected, expected_count):
    """Every problem with the aggregate: `skills` maps directory name to SKILL.md text or None."""
    return listing_errors(tuple(skills), expected, expected_count) + tuple(
        e for name in sorted(skills) for e in skill_errors(name, skills[name])
    )


def parse_expected(text):
    return tuple(sorted(line.strip() for line in text.splitlines() if line.strip()))


def read_skill_md(share_dir, name):
    path = os.path.join(share_dir, name, "SKILL.md")
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def read_skills(share_dir):
    names = sorted(n for n in os.listdir(share_dir) if os.path.isdir(os.path.join(share_dir, n)))
    return MappingProxyType({n: read_skill_md(share_dir, n) for n in names})


def main(argv):
    if len(argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    share_dir, expected_count, expected_list = argv
    with open(expected_list, encoding="utf-8") as fh:
        expected = parse_expected(fh.read())
    skills = read_skills(share_dir)
    errors = validate(skills, expected, int(expected_count))
    if errors:
        print("\n".join(f"FAIL: {e}" for e in errors), file=sys.stderr)
        return 1
    print(f"OK: {len(skills)} skills validated")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
