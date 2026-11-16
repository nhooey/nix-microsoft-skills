---
title: skills-valid check on the aggregate
state: implemented
kind: implementation
part-of: microsoft-skills-collection
implemented-by: ab42396
touches: [flake.nix, scripts/check_skills.py]
---

# `skills-valid` check on the aggregate

`checks.skills-valid` runs `scripts/check_skills.py` over
`agent-skills-nhooey-microsoft-all` and fails the build unless:

1. `share/claude-skills/` holds exactly one directory per pinned skill;
2. each has a top-level `SKILL.md`;
3. each `SKILL.md` has frontmatter with `name` and `description`;
4. the frontmatter `name:` matches the directory.

Silent corruption is worse than a noisy failure.

## Check

`nix flake check` runs it.
