# nix-microsoft-skills

[![built with garnix](https://img.shields.io/endpoint.svg?url=https%3A%2F%2Fgarnix.io%2Fapi%2Fbadges%2Fnhooey%2Fnix-microsoft-skills)](https://garnix.io/repo/nhooey/nix-microsoft-skills)

Ten community [Claude Code agent skills][skills] targeting the
Microsoft / .NET stack, packaged as a Nix flake. Built on
[`nhooey/flake-skills`][flake-skills]; intended for inclusion in
[`nhooey/skillspkgs`][skillspkgs].

This collection is **consumer-agnostic** — it exposes packages.
Downstreams decide how to install them.

[skills]: https://www.anthropic.com/engineering/agent-skills
[flake-skills]: https://github.com/nhooey/flake-skills
[skillspkgs]: https://github.com/nhooey/skillspkgs

## The 10 skills

| Output name | Upstream |
|---|---|
| `csharp-concurrency-patterns` | `wshaddix/dotnet-skills` |
| `dotnet-csharp-async-patterns` | `wshaddix/dotnet-skills` |
| `dotnet-csharp-modern-patterns` | `wshaddix/dotnet-skills` |
| `dotnet-csproj-reading` | `wshaddix/dotnet-skills` |
| `dotnet-editorconfig` | `wshaddix/dotnet-skills` |
| `dotnet-solution-navigation` | `wshaddix/dotnet-skills` |
| `dotnet-xunit` | `wshaddix/dotnet-skills` |
| `managedcode-convert-to-cpm` | `managedcode/dotnet-skills` |
| `avalonia-dev-review` | `peterblazejewicz/claude-plugins` |
| `frontend-ui-engineering-avalonia` | `peterblazejewicz/claude-plugins` |

All pins live in [`skills/default.nix`](skills/default.nix) — one
attrset, one source of truth.

## Consuming

```nix
# downstream flake.nix
{
  inputs.nix-microsoft-skills.url = "github:nhooey/nix-microsoft-skills";
  # ...
}
```

Exposed outputs (per system):

```text
packages.${system}.<skill-name>     # one derivation per skill (10 total)
packages.${system}.all              # all 10 together (symlinkJoin)
packages.${system}.default          = all
checks.${system}.treefmt
checks.${system}.skills-valid
devShells.${system}.default
apps.${system}.bump
```

Each skill derivation contains `share/claude-skills/<name>/SKILL.md`
(plus optional `references/` and `scripts/`). Install behavior — symlinks
into `~/.claude/skills/`, activation hooks, `home-manager` modules — is
**not** included here. That is `skillspkgs`'s job.

## Bumping

```sh
nix run .#bump            # dry run — prints per-repo status
nix run .#bump -- --apply # bumps every behind repo, one commit each
```

`bump` groups by upstream repo so all eight `wshaddix/dotnet-skills`
skills refresh together on one commit, not eight.

## License

Each skill carries its upstream license; see the upstream repos linked
above. Repository scaffolding is Apache-2.0.
