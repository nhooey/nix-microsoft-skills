# `nix-microsoft-skills` — implementation plan

Package ten community Claude Code skills targeting the Microsoft / .NET stack as a Nix flake, built on top of [`nhooey/flake-skills`](https://github.com/nhooey/flake-skills) and intended for inclusion in [`nhooey/skillspkgs`](https://github.com/nhooey/skillspkgs).

This collection is consumer-agnostic — it exposes packages; downstreams decide how to install them.

## The 10 skills

Each row: `output name | upstream repo | path inside repo | default branch`. Paths point to the **skill directory** (one level above `SKILL.md`); copy the whole directory so any sibling `references/`, `assets/`, `scripts/` come along.

| Output name | Repo | Path in repo | Branch |
|---|---|---|---|
| `csharp-concurrency-patterns` | `wshaddix/dotnet-skills` | `skills/csharp-concurrency-patterns` | `main` |
| `dotnet-csharp-async-patterns` | `wshaddix/dotnet-skills` | `skills/dotnet-csharp-async-patterns` | `main` |
| `dotnet-csharp-modern-patterns` | `wshaddix/dotnet-skills` | `skills/dotnet-csharp-modern-patterns` | `main` |
| `dotnet-csproj-reading` | `wshaddix/dotnet-skills` | `skills/dotnet-csproj-reading` | `main` |
| `dotnet-editorconfig` | `wshaddix/dotnet-skills` | `skills/dotnet-editorconfig` | `main` |
| `dotnet-solution-navigation` | `wshaddix/dotnet-skills` | `skills/dotnet-solution-navigation` | `main` |
| `dotnet-xunit` | `wshaddix/dotnet-skills` | `skills/dotnet-xunit` | `main` |
| `managedcode-convert-to-cpm` | `managedcode/dotnet-skills` | `catalog/Tools/Official-DotNet-NuGet/skills` | `main` |
| `avalonia-dev-review` | `peterblazejewicz/claude-plugins` | `plugins/avalonia-dev` | `main` |
| `frontend-ui-engineering-avalonia` | `peterblazejewicz/claude-plugins` | `plugins/dotnet-skills/skills/frontend-ui-engineering-avalonia` | `main` |

Notes:
- For `avalonia-dev-review`, copy the **whole plugin directory** (`commands/`, `skills/review/`, `.claude-plugin/`) so the `/avalonia-review` slash command stays wired.
- For `managedcode-convert-to-cpm`, verify the exact path against `gh api repos/managedcode/dotnet-skills/contents/catalog/Tools/Official-DotNet-NuGet/skills` before locking — managedcode reshuffles their catalog occasionally.
- All eight `wshaddix/*` outputs come from one repo. Fetch it **once** per `rev` and let each output copy a different subtree, so a `nix build .#all` doesn't redownload the tarball eight times.

## Library + collection architecture

```
flake-skills (library)
   │  exposes a builder (e.g. `mkSkill`) + likely some
   │  conventions for declaring upstream sources
   ▼
nix-microsoft-skills (this collection)   ← what this plan builds
   │  10 packages, plus an `all` aggregate
   ▼
skillspkgs (umbrella)
   │  imports many collections like this one
   ▼
end users
```

The implementing agent's **first step** is to read `flake-skills`'s `README.md` / `flake.nix` / `lib/` to discover its actual public API. Adapt the templates in this plan to whatever `flake-skills` exposes. Do not invent your own builder if `flake-skills` already ships one — that's the whole reason it exists.

If `flake-skills`'s API differs from what this plan assumes, the plan loses; the library wins. Flag the divergence in the first commit message so it's visible.

## Conventions

These are sourced from currently loaded skills. The implementing agent should re-read each skill rather than rely on the summary here.

**From `nix-flakes`** (applied throughout):
- Input order: `nixpkgs` → `flake-parts` → `systems` → alphabetical for the rest. Use the `@inputs` head convention in `outputs`.
- Use `flake-parts` and `nix-systems/default` for system iteration. Don't hand-roll `forAllSystems`.
- Prefer `inherit` over `with` in attrsets when both work.
- Use `git ls-files` (not `find`) when enumerating repo files inside Nix.
- Wire every check into `nix flake check`.
- Format with `treefmt-nix` (enable `nixfmt` + `shfmt`).

**From `nix-flake-recursive-bump-input-versions`** (applied to the bump workflow, see below):
- Compare each pinned upstream `rev` to GitHub HEAD via `gh api`.
- Classify as direct vs transitive — here every upstream is a leaf, so all behinds are direct, no cascade needed.
- Bumps land as one PR per skill (or one PR per upstream repo, since `wshaddix/dotnet-skills` contributes eight outputs that share a rev).

**From `git-hygiene-commit-message-format`** (applied to every commit the agent makes):
- Subject ≤ 72 chars, blank line, body wrapped at 72 cols, explain WHY not what.
- Cap body at ~4 paragraphs.

**From `git-hygiene-no-history-in-code`** (applied to any in-repo comments):
- No diachronic notes ("added in v2", "TODO remove after Q3"). That belongs in the commit message.

**From `git-hygiene-gitignore`** (applied to `.gitignore`):
- Anchor patterns with `/` when they apply at one path only. Editor/personal junk belongs in `~/.gitignore_global`, not here.

**From `github-policy-protect-default-branch`** (applied once the repo exists):
- Apply a Rulesets-API ruleset to the default branch: require PR, required status checks, block force-push, block deletion, apply to admins.

**From `nix-garnix-ci`** (applied for CI):
- Wire Garnix to build `packages.*` and run `checks.*` per push. `garnix.yaml` scope covers `x86_64-linux` and `aarch64-darwin` at minimum; add others only if `flake-skills` already does.

Skills inspected but **not used** because they don't apply here: `nix-java`, `nix-clojure` (no JVM / Clojure content); `github-pull-request-stacked` (no dependent-PR chain in v1); `github-policy-codeowners` (single-maintainer for now — wire later if collaborators land).

## Required flake outputs

```text
packages.${system}.<skill-name>     # one derivation per skill (10 total)
packages.${system}.all              # all 10 together, exposed as a single tree
packages.${system}.default          = all
checks.${system}.treefmt            # via treefmt-nix
checks.${system}.skills-valid       # every output has a top-level SKILL.md with parseable YAML frontmatter
devShells.${system}.default         # gh + jq + nixfmt + treefmt + a `bump` command
apps.${system}.bump                 # see "Bump workflow" below
```

Deliberately **not** exposed: install scripts, activation hooks, `~/.claude/skills/` symlinking. Those are `skillspkgs`'s job. If a downstream wants per-machine install ergonomics they consume this collection from `skillspkgs`, which handles it uniformly across all collections.

## Per-skill derivation shape

Each skill is a derivation built (preferably) by `flake-skills.lib.mkSkill` or whatever the library calls its builder. The expected inputs and outputs:

**Inputs** (per skill):
- `owner`, `repo`, `rev` (40-char SHA — never a branch), `hash`
- `srcSubdir` — path inside the repo to copy
- `outDir` — name under `share/claude-skills/` (matches the table above)
- `description` — extracted from upstream `SKILL.md` frontmatter, or hardcoded with a TODO to revisit

**Outputs**:
- `$out/share/claude-skills/<outDir>/...` containing the skill subtree verbatim
- `meta.description`, `meta.homepage` (GitHub tree URL at the pinned rev), `meta.license` (inherit upstream's license — verify each)
- `passthru.upstream` = `{ inherit owner repo rev srcSubdir; }` so the `bump` tool can iterate without re-parsing the flake

If `flake-skills` doesn't already ship `mkSkill`, contribute it there in a separate PR before continuing this collection. Don't fork the builder locally.

## Single source of truth

All upstream pins live in **one file** — `skills/default.nix` (or whatever path `flake-skills` recommends). Shape:

```nix
{
  csharp-concurrency-patterns = {
    owner = "wshaddix"; repo = "dotnet-skills"; rev = "<sha>"; hash = "<sri>";
    srcSubdir = "skills/csharp-concurrency-patterns";
    description = "…";
  };
  # … 9 more
}
```

`flake.nix` reads this attrset and maps `mkSkill` over it. Adding an 11th skill is one new attribute. Never let pin data leak into `flake.nix` itself.

## `all` aggregate

Use `pkgs.symlinkJoin` over the 10 derivations so `$out/share/claude-skills/` contains exactly 10 directories. The `checks.skills-valid` check should assert:

1. 10 directories present.
2. Each has a top-level `SKILL.md`.
3. Each `SKILL.md`'s YAML frontmatter parses and has at least `name` + `description`.
4. The `name:` in frontmatter matches the directory name.

Fail the build on any violation. Silent corruption is worse than a noisy failure.

## Bump workflow

`apps.${system}.bump` is a small bash script (formatted by `shfmt`) that, per the `nix-flake-recursive-bump-input-versions` skill:

1. Reads each pinned rev from `skills/default.nix`.
2. Calls `gh api repos/<owner>/<repo>/commits/<branch>` for each unique upstream repo (not per skill — group by repo so `wshaddix/dotnet-skills` is one API call, not eight).
3. Prints `owner/repo: <old-short> → <new-short> (<N skills>)` for each behind upstream. No-op if already current.
4. With `--apply`, rewrites the pinned rev + hash. Use `nix-prefetch-github` (or the equivalent `nix store prefetch-file`/`nurl` pattern that `flake-skills` documents) to recompute hashes.
5. Each `--apply` invocation produces **one commit per upstream repo** with the subject `chore(deps): bump <owner>/<repo> to <new-short>` and a body listing the skills affected.

Keep the script ≤120 lines. If it grows, factor to a writer in Nix.

## Repository layout

```
nix-microsoft-skills/
├── flake.nix
├── flake.lock
├── PLAN.md                      # this file
├── README.md                    # short: what + how downstreams consume it + how to bump
├── .gitignore                   # anchored, narrow, no editor cruft
├── garnix.yaml                  # CI config per nix-garnix-ci
├── skills/
│   └── default.nix              # single source of truth — attrset of 10 pins
└── scripts/
    └── bump.sh                  # invoked by apps.bump
```

## Acceptance checks (run before declaring done)

1. `nix flake check` passes cleanly.
2. `nix build .#all` produces exactly 10 directories under `result/share/claude-skills/`, each with a `SKILL.md` whose frontmatter `name:` matches the directory.
3. Each of the 10 individual `packages.<name>` builds standalone.
4. `treefmt` reports no drift.
5. `nix run .#bump` (read-only) runs to completion against all unique upstream repos and prints either `up to date` or a delta per repo, without modifying any file.
6. `nix run .#bump -- --apply` on a deliberately-stale pin produces exactly one commit per upstream repo, with a Conventional-Commits-style subject and a body that explains the bump.
7. Garnix CI is green on the first push.
8. The default branch ruleset (per `github-policy-protect-default-branch`) is in place before opening the repo to PRs.

Stop at the first failed check, fix the root cause, re-run from #1.

## Out of scope

- Install scripts, activation, symlinking into `~/.claude/skills/`, or any per-user state. That lives downstream of this collection.
- Home-manager / nix-darwin modules. Same reason.
- Vendoring skill contents into this repo — always fetch upstream so `bump` can refresh.
- Auto-bumping on every build. Bumping is explicit (`--apply`) so consumers own when upstream changes land.
- Forking the builder if `flake-skills` already ships one.

## First moves for the implementing agent

1. Clone or visit `nhooey/flake-skills`. Identify the public API for declaring a skill package. Anchor every later step to whatever it provides.
2. Set up the empty repo skeleton: `flake.nix` (inputs only — `nixpkgs`, `flake-parts`, `systems`, `flake-skills`, `treefmt-nix`, alphabetical after the first three), `.gitignore`, `garnix.yaml`, `treefmt` config. Confirm `nix flake check` is green on the empty shell.
3. Pin upstream HEADs into `skills/default.nix` by running `gh api repos/<owner>/<repo>/commits/main` for the three unique upstream repos (one call covers all eight `wshaddix` skills).
4. Build a single skill end-to-end first — `dotnet-xunit` is a good probe (small, top-level, no surprise paths). Get `nix build .#dotnet-xunit` green before expanding to the others.
5. Add the remaining nine. Add `all`. Add `checks.skills-valid`. Add `apps.bump` (read-only mode first; `--apply` second).
6. Wire Garnix. Apply the default-branch ruleset. Open the repo for PRs.
7. Submit the collection to `skillspkgs` per whatever inclusion process that repo documents.

Do not skip the single-skill probe in step 4. Getting `mkSkill` (or the equivalent) right once saves debugging it ten times.
