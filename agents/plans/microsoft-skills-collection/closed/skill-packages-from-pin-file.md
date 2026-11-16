---
title: One package per skill, built from a single pin file
state: implemented
kind: implementation
part-of: microsoft-skills-collection
implemented-by: ab42396
touches: [flake.nix, skills/default.nix]
---

# One package per skill, built from a single pin file

`skills/default.nix` holds every upstream pin: `repos.<key>` gives
`owner`, `repo`, a 40-character `rev`, `hash` and `defaultBranch`, and
`skills.<name>` gives the `repo` key, `srcSubdir` and `description`.
Adding a skill is one new attribute; no pin data sits in `flake.nix`.

`flake.nix` fetches each repository once per rev, so the seven
`wshaddix/dotnet-skills` skills share one tarball, and builds each skill
with `agent-skill-flake.lib.mkSkillFlake` rather than a local builder.
`namespaceFn` names every package `agent-skill-nhooey-microsoft-<skill>`.
Each package carries `meta.homepage` (the GitHub tree at the pinned rev)
and `passthru.upstream` (`owner`, `repo`, `rev`, `srcSubdir`).
`agent-skills-nhooey-microsoft-all`, also `default`, is a `symlinkJoin`
of all of them.

The skill directories, copied whole so sibling `references/`, `scripts/`
come along:

| Skill | Upstream | Path in repo |
|---|---|---|
| `csharp-concurrency-patterns` | `wshaddix/dotnet-skills` | `skills/csharp-concurrency-patterns` |
| `dotnet-csharp-async-patterns` | `wshaddix/dotnet-skills` | `skills/dotnet-csharp-async-patterns` |
| `dotnet-csharp-modern-patterns` | `wshaddix/dotnet-skills` | `skills/dotnet-csharp-modern-patterns` |
| `dotnet-csproj-reading` | `wshaddix/dotnet-skills` | `skills/dotnet-csproj-reading` |
| `dotnet-editorconfig` | `wshaddix/dotnet-skills` | `skills/dotnet-editorconfig` |
| `dotnet-solution-navigation` | `wshaddix/dotnet-skills` | `skills/dotnet-solution-navigation` |
| `dotnet-xunit` | `wshaddix/dotnet-skills` | `skills/dotnet-xunit` |
| `managedcode-convert-to-cpm` | `managedcode/dotnet-skills` | `catalog/Tools/Official-DotNet-NuGet/skills/convert-to-cpm` |
| `avalonia-dev-review` | `peterblazejewicz/claude-plugins` | `plugins/avalonia-dev/skills/review` |
| `frontend-ui-engineering-avalonia` | `peterblazejewicz/claude-plugins` | `plugins/dotnet-skills/skills/frontend-ui-engineering-avalonia` |

## Check

`checks.skill-agent-skill-nhooey-microsoft-<skill>` builds each package.
