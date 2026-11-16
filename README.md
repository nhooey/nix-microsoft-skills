# nix-microsoft-skills

Ten community [Claude Code agent skills][skills] targeting the Microsoft / .NET stack, packaged as a Nix flake.
Built on [`nhooey/agent-skill-flake`][agent-skill-flake]; intended for inclusion in [`nhooey/skillspkgs`][skillspkgs].

This collection is **consumer-agnostic** — it exposes packages.
Downstreams decide how to install them.

[skills]: https://www.anthropic.com/engineering/agent-skills
[agent-skill-flake]: https://github.com/nhooey/agent-skill-flake
[skillspkgs]: https://github.com/nhooey/skillspkgs

## The 10 skills

| Skill | Upstream |
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

Each skill's package is `agent-skill-nhooey-microsoft-<skill>`.
All pins live in [`skills/default.nix`](skills/default.nix) — one attrset, one source of truth.

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
packages.${system}.agent-skill-nhooey-microsoft-<skill>   # one per skill (10 total)
packages.${system}.agent-skills-nhooey-microsoft-all     # all 10 together (symlinkJoin)
packages.${system}.default                               = agent-skills-nhooey-microsoft-all
checks.${system}.skill-agent-skill-nhooey-microsoft-<skill>  # each skill builds
checks.${system}.skills-valid
checks.${system}.scripts-tests                           # unit tests of scripts/
checks.${system}.treefmt
formatter.${system}                                      # treefmt (nixfmt + shfmt)
devShells.${system}.default
apps.${system}.bump
```

Each skill derivation contains `share/claude-skills/<name>/SKILL.md` (plus optional `references/` and `scripts/`).
Install behavior — symlinks into `~/.claude/skills/`, activation hooks, `home-manager` modules — is **not** included here.
That is `skillspkgs`'s job.

## Bumping

In the dev shell, `skills-dev bump` prints each upstream repo's status against GitHub, and `skills-dev bump --apply` bumps every behind repo, one commit each.
Outside it, `nix run .#bump` does the same.

`bump` groups by upstream repo so all seven `wshaddix/dotnet-skills` skills refresh together on one commit, not seven.

## Development

`nix develop` enters the dev shell; `menu` lists its commands.
`check` runs `nix flake check`, `fmt` formats the tree, and `skills-dev` builds skills (`build`), runs the scripts' unit tests (`test`) and bumps the pins (`bump`).
`skills-dev --help` lists its commands and options.

## License

Each skill carries its upstream license; see the upstream repos linked above.
Repository scaffolding is Apache-2.0.
