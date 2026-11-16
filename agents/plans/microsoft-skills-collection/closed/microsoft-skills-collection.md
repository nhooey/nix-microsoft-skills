---
title: Ten Microsoft / .NET skills packaged as a Nix flake
state: implemented
kind: end-state
implemented-by: ab42396
---

# Ten Microsoft / .NET skills packaged as a Nix flake

This repository packages ten community Claude Code skills for the
Microsoft / .NET stack, built with `nhooey/agent-skill-flake` and included
in `nhooey/skillspkgs`. It exposes packages only: installing them
(symlinks into `~/.claude/skills/`, activation hooks, home-manager or
nix-darwin modules) is the consumer's job, and no skill content is vendored,
so `bump` can always refresh from upstream.

## Check

1. `nix flake check` passes.
2. `nix build .#agent-skills-nhooey-microsoft-all` gives one directory per
   pinned skill under `share/claude-skills/`, each with a `SKILL.md` whose
   frontmatter `name:` matches the directory.
3. Each `agent-skill-nhooey-microsoft-<skill>` package builds on its own.
4. `nix fmt` changes nothing.
