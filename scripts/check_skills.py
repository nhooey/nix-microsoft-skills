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
  - frontmatter that isn't valid YAML, isn't a mapping, or repeats a key
  - frontmatter missing `name:` or `description:`, or either not a string
  - frontmatter `name:` not matching the containing directory

yq-go (`yq`, on PATH) parses the frontmatter as YAML 1.2 and hands it over
as JSON, so the check reads each value as a YAML parser does.
"""

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping, Optional, Tuple, Union


FRONTMATTER_RE = re.compile(r"\A---[ \t]*\n(.*?)\n?^---[ \t]*$", re.DOTALL | re.MULTILINE)


@dataclass(frozen=True, slots=True)
class Parsed:
    fields: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class Invalid:
    problems: Tuple[str, ...]


Frontmatter = Union[Parsed, Invalid]


def frontmatter_block(text):
    """The YAML between a SKILL.md's opening and closing `---` lines, or None."""
    match = FRONTMATTER_RE.match(text)
    return match.group(1) + "\n" if match else None


def duplicate_keys(pairs):
    keys = tuple(key for key, _ in pairs)
    return tuple(dict.fromkeys(key for i, key in enumerate(keys) if key in keys[:i]))


def from_json(text):
    """Parsed fields from yq's JSON output, or Invalid when it isn't a mapping
    or repeats a top-level key (yq keeps every copy of a key in its JSON)."""
    value = json.loads(text, object_pairs_hook=tuple)
    if value is None:
        return Parsed(MappingProxyType({}))
    if not isinstance(value, tuple):
        return Invalid((f"not a mapping of keys to values: {value!r}",))
    duplicates = duplicate_keys(value)
    if duplicates:
        return Invalid(tuple(f"duplicate key `{key}`" for key in duplicates))
    return Parsed(MappingProxyType(dict(value)))


def field_errors(name, fields, key, check_value=None):
    value = fields.get(key)
    if key not in fields:
        return (f"{name}: frontmatter missing `{key}:`",)
    if not isinstance(value, str) or not value.strip():
        return (f"{name}: frontmatter `{key}:` is not a non-empty string ({value!r})",)
    return check_value(value) if check_value else ()


def skill_errors(name, frontmatter: Optional[Frontmatter]):
    """Problems with one skill directory, given its parsed frontmatter (None
    when SKILL.md is absent)."""
    match frontmatter:
        case None:
            return (f"{name}: SKILL.md missing",)
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
    """Every problem with the aggregate: `skills` maps directory name to its
    parsed frontmatter, or None when SKILL.md is missing."""
    return listing_errors(tuple(skills), expected, expected_count) + tuple(
        e for name in sorted(skills) for e in skill_errors(name, skills[name])
    )


def parse_expected(text):
    return tuple(sorted(line.strip() for line in text.splitlines() if line.strip()))


# --- shell: yq and the file system -------------------------------------------


def parse_frontmatter(text):
    """A SKILL.md's frontmatter parsed by yq-go, or Invalid with the reasons."""
    block = frontmatter_block(text)
    if block is None:
        return Invalid(("no frontmatter block between `---` lines",))
    result = subprocess.run(
        ["yq", "--input-format=yaml", "--output-format=json", "."],
        input=block,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return Invalid((f"not valid YAML: {result.stderr.strip()}",))
    return from_json(result.stdout)


def read_skill_md(share_dir, name):
    path = os.path.join(share_dir, name, "SKILL.md")
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def read_skills(share_dir):
    names = sorted(n for n in os.listdir(share_dir) if os.path.isdir(os.path.join(share_dir, n)))
    texts = {n: read_skill_md(share_dir, n) for n in names}
    return MappingProxyType(
        {n: None if text is None else parse_frontmatter(text) for n, text in texts.items()}
    )


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
