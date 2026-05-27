#!/usr/bin/env python3
"""
checks.skills-valid: assert the `all` aggregate is well-formed.

Args:
  $1  share/claude-skills directory inside the symlinkJoin output
  $2  expected skill count
  $3  file with one expected skill name per line (sorted)

Fails loudly on:
  - count mismatch
  - missing SKILL.md
  - frontmatter that doesn't parse as YAML
  - frontmatter missing `name:` or `description:`
  - frontmatter `name:` not matching the containing directory
"""

import os
import re
import sys


FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def parse_frontmatter(text):
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None
    body = m.group(1)
    fields = {}
    for line in body.splitlines():
        if not line or line[0] in " \t#":
            continue
        if ":" not in line:
            continue
        k, _, v = line.partition(":")
        fields[k.strip()] = v.strip().strip('"').strip("'")
    return fields


def main():
    share_dir, expected_count_s, expected_list_path = sys.argv[1:4]
    expected_count = int(expected_count_s)
    with open(expected_list_path) as fh:
        expected = sorted(line.strip() for line in fh if line.strip())

    actual = sorted(
        n for n in os.listdir(share_dir) if os.path.isdir(os.path.join(share_dir, n))
    )

    errors = []
    if len(actual) != expected_count:
        errors.append(
            f"directory count: expected {expected_count}, got {len(actual)} ({actual})"
        )
    if actual != expected:
        missing = sorted(set(expected) - set(actual))
        extra = sorted(set(actual) - set(expected))
        if missing:
            errors.append(f"missing skills: {missing}")
        if extra:
            errors.append(f"unexpected skills: {extra}")

    for name in actual:
        skill_md = os.path.join(share_dir, name, "SKILL.md")
        if not os.path.isfile(skill_md):
            errors.append(f"{name}: SKILL.md missing")
            continue
        with open(skill_md) as fh:
            text = fh.read()
        fm = parse_frontmatter(text)
        if fm is None:
            errors.append(f"{name}: SKILL.md has no YAML frontmatter")
            continue
        if "name" not in fm:
            errors.append(f"{name}: frontmatter missing `name:`")
        elif fm["name"] != name:
            errors.append(
                f"{name}: frontmatter name={fm['name']!r} != directory name"
            )
        if "description" not in fm:
            errors.append(f"{name}: frontmatter missing `description:`")

    if errors:
        for e in errors:
            print(f"FAIL: {e}", file=sys.stderr)
        sys.exit(1)
    print(f"OK: {len(actual)} skills validated")


if __name__ == "__main__":
    main()
